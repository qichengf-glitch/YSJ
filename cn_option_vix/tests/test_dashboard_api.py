from fastapi.testclient import TestClient

from cn_option_vix.web import app as web_app
from cn_option_vix.web.storage import upsert_points


def test_dashboard_api_serves_both_resolutions(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    row = {
        "timestamp": "2026-07-14 14:35",
        "overall": 20.0,
        "index_vix": 21.0,
        "blue_chip": 19.0,
        "sz_growth": 23.0,
        "mid_small": 24.0,
        "hard_tech": 26.0,
        "n_instruments": 12,
        "expected_instruments": 12,
    }
    upsert_points([row], resolution="5m", source="test", db_path=db)
    half = dict(row, timestamp="2026-07-14 11:30", session="AM")
    upsert_points([half], resolution="halfday", source="test", db_path=db)

    client = TestClient(web_app.app)
    latest = client.get("/api/latest")
    assert latest.status_code == 200
    assert len(latest.json()["cards"]) == 6
    assert latest.json()["cards"][-1]["spread"] == 6.0

    five = client.get("/api/series", params={"resolution": "5m"})
    halfday = client.get("/api/series", params={"resolution": "halfday"})
    assert five.json()["count"] == 1
    assert halfday.json()["count"] == 1


def test_dashboard_api_exposes_averages_and_ytd(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    rows = []
    for i, day in enumerate(__import__('pandas').bdate_range("2026-01-02", periods=60)):
        rows.append({
            "timestamp": f"{day.date()} 15:00",
            "overall": 20.0 + i / 10,
            "index_vix": 21.0 + i / 10,
            "blue_chip": 19.0 + i / 10,
            "sz_growth": 23.0 + i / 10,
            "mid_small": 24.0 + i / 10,
            "hard_tech": 26.0 + i / 10,
            "n_instruments": 12,
            "expected_instruments": 12,
            "session": "PM",
        })
    upsert_points(rows, resolution="halfday", source="test", db_path=db)
    live = dict(rows[-1], timestamp="2026-07-14 14:35")
    upsert_points([live], resolution="5m", source="test", db_path=db)

    client = TestClient(web_app.app)
    averages = client.get("/api/averages")
    assert averages.status_code == 200
    payload = averages.json()
    assert len(payload["rows"]) == 6
    assert payload["rows"][0]["count_20"] == 20
    assert payload["rows"][0]["variance_20"] is not None
    assert payload["rows"][0]["count_60"] == 60
    hard = next(row for row in payload["rows"] if row["key"] == "hard_tech")
    assert hard["latest_spread"] == 6.0
    assert hard["spread_count_20"] == 20
    assert hard["spread_std_20"] == 0.0
    assert hard["spread_variance_20"] == 0.0

    halfday = client.get("/api/series", params={"resolution": "halfday"})
    assert halfday.status_code == 200
    assert halfday.json()["points"][0]["timestamp"].startswith("2026-")


def test_static_assets_are_cache_busted_and_no_store(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    client = TestClient(web_app.app)
    page = client.get("/")
    assert page.status_code == 200
    assert "app.js?v=20260723-auto-catchup-v5" in page.text
    assert "styles.css?v=20260723-auto-catchup-v5" in page.text
    assert page.headers["cache-control"].startswith("no-store")
    assert "Indexed 100" not in page.text
    assert 'id="relativeRows"' in page.text
    assert 'id="levelGrid"' in page.text
    assert "20D relative spread" in page.text
    assert "20D / 60D VIX Level Context" in page.text


def test_api_hides_partial_latest_point(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    full = {
        "timestamp": "2026-07-16 13:15",
        "overall": 30.0,
        "index_vix": 28.0,
        "blue_chip": 26.0,
        "sz_growth": 32.0,
        "mid_small": 34.0,
        "hard_tech": 40.0,
        "n_instruments": 12,
        "expected_instruments": 12,
    }
    partial = dict(full, timestamp="2026-07-16 13:20", n_instruments=3)
    partial.update(index_vix=None, blue_chip=None, sz_growth=None)
    upsert_points([full, partial], resolution="5m", source="test", db_path=db)

    client = TestClient(web_app.app)
    latest = client.get("/api/latest").json()
    assert latest["timestamp"] == "2026-07-16 13:15:00"
    assert all(card["value"] is not None for card in latest["cards"])
    series = client.get("/api/series", params={"resolution": "5m"}).json()
    assert series["count"] == 1


def test_status_marks_old_weekday_data_stale_after_close(tmp_path, monkeypatch):
    from datetime import datetime as real_datetime
    from zoneinfo import ZoneInfo

    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    row = {
        "timestamp": "2026-07-17 15:00",
        "overall": 20.0,
        "index_vix": 21.0,
        "blue_chip": 19.0,
        "sz_growth": 23.0,
        "mid_small": 24.0,
        "hard_tech": 26.0,
        "n_instruments": 12,
        "expected_instruments": 12,
    }
    upsert_points([row], resolution="5m", source="test", db_path=db)

    class FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = cls(2026, 7, 23, 17, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
            return fixed if tz is None else fixed.astimezone(tz)

    monkeypatch.setattr(web_app, "datetime", FixedDateTime)
    payload = TestClient(web_app.app).get("/api/status").json()
    assert payload["state"] == "STALE"
    assert payload["quality"] == "STALE"
