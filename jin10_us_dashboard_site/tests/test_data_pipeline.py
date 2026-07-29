import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.database import get_conn, init_db, record_log
from app import prediction_market_service as pm
from app import whale_service as whales
from app import services


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class DataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = settings.database_path
        object.__setattr__(settings, "database_path", str(Path(self.tmp.name) / "test.db"))
        init_db()

    def tearDown(self):
        object.__setattr__(settings, "database_path", self.old_db)
        self.tmp.cleanup()

    @staticmethod
    def sample_event():
        return {
            "id": "evt-1",
            "title": "Federal Reserve rate cut in 2026?",
            "active": True,
            "closed": False,
            "volume": 1_000_000,
            "liquidity": 120_000,
            "tags": [{"slug": "fed-rates"}],
            "markets": [{
                "conditionId": "cond-1",
                "question": "Will the Fed cut rates in 2026?",
                "active": True,
                "closed": False,
                "outcomes": '["No", "Yes"]',
                "outcomePrices": '["0.65", "0.35"]',
                "clobTokenIds": '["no-token", "yes-token"]',
                "volume24hr": 22_000,
                "volume1wk": 70_000,
                "volume": 1_000_000,
                "liquidity": 120_000,
                "oneWeekPriceChange": 0.04,
                "oneDayPriceChange": 0.01,
                "bestBid": 0.34,
                "bestAsk": 0.36,
            }],
        }

    def test_jin10_log_accepts_data_id_from_nested_payload(self):
        ok = record_log("us", "data", {
            "log_id": 123, "action": "update", "modify_time": "2026-07-17 10:00:00",
            "data": {"id": 456, "actual": "1.2"},
        })
        self.assertTrue(ok)
        with get_conn() as conn:
            row = conn.execute("SELECT data_id FROM raw_jin10_logs WHERE log_id=123").fetchone()
        self.assertEqual(row["data_id"], 456)

    def test_regular_events_endpoint_uses_offset_pagination(self):
        calls = []

        class FakeHTTP:
            def get(self, url, params=None, timeout=None):
                calls.append(dict(params or {}))
                offset = int(params["offset"])
                if offset == 0:
                    return FakeResponse([{"id": "a"}, {"id": "b"}])
                if offset == 2:
                    return FakeResponse([{"id": "c"}])
                return FakeResponse([])

        with patch.object(pm, "_HTTP", FakeHTTP()), patch.object(pm.time, "sleep", lambda *_: None):
            rows, complete, pages = pm._fetch_poly_events(page_size=2, max_pages=5)

        self.assertEqual([r["id"] for r in rows], ["a", "b", "c"])
        self.assertTrue(complete)
        self.assertEqual(pages, 2)
        self.assertEqual([c["offset"] for c in calls], [0, 2])
        self.assertTrue(all("next_cursor" not in c and "after_cursor" not in c for c in calls))
        self.assertTrue(all(c["order"] == "volume_24hr" for c in calls))

    def test_events_422_falls_back_to_minimal_query_and_local_sort(self):
        calls = []

        class Response:
            def __init__(self, status_code, payload=None, text=""):
                self.status_code = status_code
                self.payload = payload
                self.text = text

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise pm.requests.HTTPError(f"HTTP {self.status_code}")

            def json(self):
                return self.payload

        class FakeHTTP:
            def get(self, url, params=None, timeout=None):
                params = dict(params or {})
                calls.append(params)
                if "order" in params:
                    return Response(422, text='{"detail":"invalid order"}')
                if int(params["offset"]) == 0:
                    return Response(200, [
                        {"id": "low", "volume24hr": 10},
                        {"id": "high", "volume24hr": 50},
                    ])
                return Response(200, [])

        with patch.object(pm, "_HTTP", FakeHTTP()), patch.object(pm.time, "sleep", lambda *_: None):
            rows, complete, pages = pm._fetch_poly_events(page_size=2, max_pages=3)

        self.assertEqual([r["id"] for r in rows], ["high", "low"])
        self.assertTrue(complete)
        self.assertEqual(pages, 2)
        self.assertEqual(calls[0]["order"], "volume_24hr")
        self.assertEqual(calls[1]["order"], "volume24hr")
        self.assertNotIn("order", calls[2])
        self.assertEqual(pm._LAST_GAMMA_QUERY_MODE, "minimal_local_sort")
        self.assertEqual(len(pm._LAST_GAMMA_VALIDATION_FALLBACKS), 2)

    def test_events_parser_accepts_enveloped_response(self):
        class FakeHTTP:
            def get(self, url, params=None, timeout=None):
                return FakeResponse({"events": [{"id": "a"}], "has_more": "false"})
        with patch.object(pm, "_HTTP", FakeHTTP()):
            rows, complete, pages = pm._fetch_poly_events(page_size=100, max_pages=2)
        self.assertEqual([r["id"] for r in rows], ["a"])
        self.assertTrue(complete)
        self.assertEqual(pages, 1)

    def test_page_cap_is_reported_as_incomplete(self):
        class FakeHTTP:
            def get(self, url, params=None, timeout=None):
                offset = int(params["offset"])
                return FakeResponse([{"id": f"evt-{offset}"}, {"id": f"evt-{offset+1}"}])
        with patch.object(pm, "_HTTP", FakeHTTP()), patch.object(pm.time, "sleep", lambda *_: None):
            rows, complete, pages = pm._fetch_poly_events(page_size=2, max_pages=2)
        self.assertEqual(len(rows), 4)
        self.assertFalse(complete)
        self.assertEqual(pages, 2)

    def test_quote_sync_maps_yes_and_uses_real_weekly_volume(self):
        with patch.object(pm, "_fetch_poly_events", return_value=([self.sample_event()], True, 1)):
            result = pm.sync_prediction_markets(min_prob=0.1, min_volume=10_000, fetch_history=False)

        self.assertEqual(result["saved_markets"], 1)
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM pm_markets WHERE condition_id='cond-1'").fetchone()
        self.assertAlmostEqual(row["price_now"], 0.35)
        self.assertEqual(row["token_id"], "yes-token")
        self.assertAlmostEqual(row["volume_7d"], 70_000)
        self.assertAlmostEqual(row["volume_total"], 1_000_000)
        self.assertAlmostEqual(row["volume_24h"], 22_000)
        # With no prior daily snapshots, the documented 7-day total is the fallback baseline.
        self.assertAlmostEqual(row["volume_10d_avg"], 10_000)
        self.assertAlmostEqual(row["volume_spike_ratio"], 2.2)

    def test_prediction_volume_snapshot_uses_dashboard_local_date(self):
        event = self.sample_event()
        event["active"] = "true"
        event["closed"] = "false"
        event["markets"][0]["active"] = "true"
        event["markets"][0]["closed"] = "false"
        with patch.object(pm, "_fetch_poly_events", return_value=([event], True, 1)), \
             patch.object(pm, "dashboard_today", return_value=date(2026, 7, 18)):
            result = pm.sync_prediction_markets(fetch_history=False)
        self.assertEqual(result["saved_markets"], 1)
        with get_conn() as conn:
            row = conn.execute(
                "SELECT date FROM pm_volume_history WHERE condition_id='cond-1'"
            ).fetchone()
        self.assertEqual(row["date"], "2026-07-18")

    def test_market_without_explicit_yes_outcome_is_rejected(self):
        event = self.sample_event()
        event["markets"][0]["outcomes"] = '["Up", "Down"]'
        with patch.object(pm, "_fetch_poly_events", return_value=([event], True, 1)):
            with self.assertRaises(RuntimeError):
                pm.sync_prediction_markets(fetch_history=False)
        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM pm_markets").fetchone()[0]
        self.assertEqual(count, 0)

    def test_empty_upstream_response_preserves_last_snapshot(self):
        with patch.object(pm, "_fetch_poly_events", return_value=([self.sample_event()], True, 1)):
            pm.sync_prediction_markets(fetch_history=False)
        with patch.object(pm, "_fetch_poly_events", return_value=([], True, 1)):
            with self.assertRaises(RuntimeError):
                pm.sync_prediction_markets(fetch_history=False)
        with get_conn() as conn:
            row = conn.execute("SELECT active, price_now FROM pm_markets WHERE condition_id='cond-1'").fetchone()
        self.assertEqual(row["active"], 1)
        self.assertAlmostEqual(row["price_now"], 0.35)

    def test_jin10_missing_data_id_does_not_pin_cursor(self):
        class FakeJin10Client:
            def fetch_log(self, source_type, category, last_log_id=None):
                if (last_log_id or 0) < 7:
                    return [{
                        "log_id": 7, "action": "update",
                        "modify_time": "2026-07-17 10:00:00", "data": {},
                    }]
                return []

        with patch.object(services, "Jin10Client", return_value=FakeJin10Client()):
            result = services.process_logs_for("data")
        self.assertEqual(result["last_log_id"], 7)
        self.assertEqual(result["skipped_missing_data_id"], 1)
        with get_conn() as conn:
            row = conn.execute(
                "SELECT data_id FROM raw_jin10_logs WHERE log_id=7"
            ).fetchone()
        self.assertEqual(row["data_id"], 0)

    def test_trades_request_uses_server_side_time_window(self):
        calls = []

        def fake_get_json(url, params=None):
            calls.append((url, dict(params or {})))
            return []

        with patch.object(whales, "_get_json", side_effect=fake_get_json):
            rows = whales.fetch_trades_for_wallet_markets("0xabc", ["cond-1"], days=3)
        self.assertEqual(rows, [])
        params = calls[0][1]
        self.assertIn("start", params)
        self.assertIn("end", params)
        self.assertLess(params["start"], params["end"])
        self.assertEqual(params["market"], "cond-1")


    def test_failed_partial_whale_run_does_not_override_legacy_snapshot(self):
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO pm_whale_sync_runs(fetched_at,status,wallet_count,wallets_failed,positions_saved) VALUES ('2026-07-16T01:00:00Z',NULL,1,0,1)"
            )
            conn.execute(
                "INSERT INTO pm_whale_sync_runs(fetched_at,status,wallet_count,wallets_failed,positions_saved) VALUES ('2026-07-17T01:00:00Z','partial',2,1,1)"
            )
            for ts in ('2026-07-16T01:00:00Z','2026-07-17T01:00:00Z'):
                conn.execute(
                    """INSERT INTO pm_whale_positions(condition_id,address,name,outcome,asset,size,value,win_rate,wins,losses,fetched_at,raw_json)
                       VALUES ('cond-1','0xabc','A','Yes','asset',1,10,0,0,0,?, '{}')""",
                    (ts,),
                )
        with get_conn() as conn:
            self.assertEqual(whales._latest_snapshot_time(conn), '2026-07-16T01:00:00Z')


    def test_failed_wallet_is_carried_while_other_wallet_updates(self):
        wallets_cfg = [
            {"address": "0xaaa", "name": "Alice"},
            {"address": "0xbbb", "name": "Bob"},
        ]
        markets = {"cond-1": {"condition_id": "cond-1"}}

        def first_positions(address):
            value = 10.0 if address == "0xaaa" else 12.0
            return [{
                "conditionId": "cond-1", "outcome": "Yes",
                "asset": f"asset-{address}", "currentValue": value,
                "size": 1.0, "cashPnl": 1.0,
            }]

        with patch.object(whales, "qualifying_markets", return_value=markets), \
             patch.object(whales, "load_wallets", return_value=wallets_cfg), \
             patch.object(whales, "fetch_positions", side_effect=first_positions), \
             patch.object(whales, "fetch_trades_for_wallet_markets", return_value=[]), \
             patch.object(whales, "utc_now", return_value="2026-07-17T01:00:00Z"), \
             patch.object(whales.time, "sleep", lambda *_: None):
            first = whales.sync_tracked_whales()
        self.assertEqual(first["status"], "success")

        def second_positions(address):
            if address == "0xbbb":
                raise RuntimeError("temporary upstream failure")
            return [{
                "conditionId": "cond-1", "outcome": "Yes",
                "asset": "asset-0xaaa", "currentValue": 20.0,
                "size": 2.0, "cashPnl": 2.0,
            }]

        with patch.object(whales, "qualifying_markets", return_value=markets), \
             patch.object(whales, "load_wallets", return_value=wallets_cfg), \
             patch.object(whales, "fetch_positions", side_effect=second_positions), \
             patch.object(whales, "fetch_trades_for_wallet_markets", return_value=[]), \
             patch.object(whales, "utc_now", return_value="2026-07-17T02:00:00Z"), \
             patch.object(whales.time, "sleep", lambda *_: None):
            second = whales.sync_tracked_whales()

        self.assertEqual(second["status"], "partial_carried")
        self.assertEqual(second["wallets_carried"], 1)
        self.assertEqual(second["positions_carried"], 1)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT address, value, raw_json FROM pm_whale_positions "
                "WHERE fetched_at='2026-07-17T02:00:00Z' ORDER BY address"
            ).fetchall()
            run = conn.execute(
                "SELECT wallet_set_hash, wallets_carried, status FROM pm_whale_sync_runs "
                "WHERE fetched_at='2026-07-17T02:00:00Z'"
            ).fetchone()
        self.assertEqual([(r["address"], r["value"]) for r in rows], [("0xaaa", 20.0), ("0xbbb", 12.0)])
        self.assertIn("_carried_forward_from", rows[1]["raw_json"])
        self.assertTrue(run["wallet_set_hash"])
        self.assertEqual(run["wallets_carried"], 1)
        self.assertEqual(run["status"], "partial_carried")

    def test_whale_daily_boundary_uses_dashboard_timezone(self):
        end = whales._day_end_utc('2026-07-17')
        # Asia/Shanghai local 23:59:59 is 15:59:59 UTC.
        self.assertEqual(end.isoformat(), '2026-07-17T15:59:59+00:00')

    def test_safe_partial_whale_run_can_remain_current(self):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO pm_whale_sync_runs(
                    fetched_at, status, wallet_count, wallets_failed,
                    positions_saved, trades_saved, finished_at
                ) VALUES ('2026-07-17T01:00:00Z','partial',1,0,1,0,'2026-07-17T01:01:00Z')
                """
            )
        with get_conn() as conn:
            self.assertEqual(whales._latest_snapshot_time(conn), "2026-07-17T01:00:00Z")


if __name__ == "__main__":
    unittest.main()
