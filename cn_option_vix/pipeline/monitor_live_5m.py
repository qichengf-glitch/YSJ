"""Five-minute live collector for the two-scale VIX dashboard.

One unioned RQData snapshot is reused across all 12 instruments so Overall,
all five published groups, and every group-minus-Overall spread share the same
observation point. At 11:30 and 15:00 the exact same computed row is also
written to the half-day series; no second data request is made.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import rqdatac as rq

from cn_option_vix.config import LIVE_DASHBOARD_PARAMS, ROSTER
from cn_option_vix.core.instrument_vix import instrument_vix_from_snapshot
from cn_option_vix.data.intraday_chains import (
    _chunks,
    _retry,
    ensure_rq,
    latest_trading_dates,
    load_contract_plan,
    quota_snapshot,
)
from cn_option_vix.pipeline.one_day import assemble_vix_row
from cn_option_vix.data.rq_process_lock import rqdata_locked
from cn_option_vix.web.storage import (
    DEFAULT_DB_PATH,
    is_publishable_point,
    log_event,
    query_series,
    upsert_points,
)

TZ = ZoneInfo("Asia/Shanghai")
_OUT = Path(__file__).resolve().parent.parent / "outputs"
_AUDIT_PATH = _OUT / "vix_5m_live_audit.csv"


def _safe_quota_snapshot(db_path: str | Path) -> dict:
    """Read quota diagnostics without blocking a market-data observation.

    RQData quota inspection is operational metadata, not an input to the VIX
    calculation. A transient account/session error must therefore not discard
    an otherwise collectable five-minute point.
    """
    try:
        return quota_snapshot()
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        print(f"quota diagnostic warning: {message}", flush=True)
        log_event("WARNING", "quota_snapshot_error", message, db_path=db_path)
        return {}


def _tick_frame(ids: list[str]) -> pd.DataFrame:
    """Fetch one logical market snapshot for the union of required contracts."""
    frames = []
    batch_size = int(LIVE_DASHBOARD_PARAMS["request_batch_size"])
    for batch in _chunks(ids, batch_size):
        ticks = _retry(
            f"current_snapshot ({len(batch)} contracts)",
            lambda batch=batch: rq.current_snapshot(batch),
        )
        if ticks is None:
            continue
        if not isinstance(ticks, (list, tuple)):
            ticks = [ticks]
        rows = []
        for tick in ticks:
            if tick is None:
                continue
            rows.append(
                {
                    "order_book_id": str(getattr(tick, "order_book_id", "")),
                    "tick_datetime": pd.to_datetime(
                        getattr(tick, "datetime", None), errors="coerce"
                    ),
                    "last": pd.to_numeric(getattr(tick, "last", None), errors="coerce"),
                    "open_interest": pd.to_numeric(
                        getattr(tick, "open_interest", None), errors="coerce"
                    ),
                    "volume": pd.to_numeric(
                        getattr(tick, "volume", None), errors="coerce"
                    ),
                }
            )
        if rows:
            frames.append(pd.DataFrame(rows))
    if not frames:
        return pd.DataFrame(
            columns=["order_book_id", "tick_datetime", "last", "open_interest", "volume"]
        )
    df = pd.concat(frames, ignore_index=True)
    df = df[df["order_book_id"].ne("")].copy()
    return df.drop_duplicates("order_book_id", keep="last")


def _snapshot_from_ticks(
    symbol: str,
    date: pd.Timestamp,
    timestamp: pd.Timestamp,
    plan: pd.DataFrame,
    ticks: pd.DataFrame,
):
    point = ticks.merge(
        plan[["order_book_id", "days", "term", "cp", "strike", "maturity_date"]],
        on="order_book_id",
        how="inner",
        validate="one_to_one",
    )
    point["price"] = pd.to_numeric(point["last"], errors="coerce")
    point["oi"] = pd.to_numeric(point["open_interest"], errors="coerce").fillna(0.0)
    point = point[point["price"].gt(0)].copy()
    point["symbol"] = symbol
    point["timestamp"] = timestamp
    point["price_source"] = "current_snapshot.last"

    days = sorted(int(x) for x in plan["days"].unique())
    if len(days) < 2:
        return None, point, "missing_expiry_plan"
    near_d, next_d = days[:2]
    by_expiry = {
        dd: point[point["days"] == dd][["strike", "cp", "price", "oi"]]
        .sort_values(["strike", "cp"])
        .reset_index(drop=True)
        for dd in (near_d, next_d)
    }
    if any(frame.empty for frame in by_expiry.values()):
        return None, point, "missing_snapshot_for_expiry"
    return (
        {
            "underlying": symbol,
            "date": date,
            "timestamp": timestamp,
            "expiries": [near_d, next_d],
            "by_expiry": by_expiry,
            "price_source": "current_snapshot.last",
        },
        point,
        "chain_ready",
    )


def _save_audits(audits: list[dict]) -> None:
    if not audits:
        return
    _OUT.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(audits)
    if _AUDIT_PATH.exists():
        old = pd.read_csv(_AUDIT_PATH)
        old["timestamp"] = pd.to_datetime(old["timestamp"], errors="coerce")
        new["timestamp"] = pd.to_datetime(new["timestamp"], errors="coerce")
        keys = set(zip(new["timestamp"].astype(str), new["symbol"].astype(str)))
        keep = [
            (str(ts), str(symbol)) not in keys
            for ts, symbol in zip(old["timestamp"], old["symbol"])
        ]
        new = pd.concat([old.loc[keep], new], ignore_index=True)
    new = new.sort_values(["timestamp", "symbol"])
    tmp = _AUDIT_PATH.with_suffix(".tmp.csv")
    new.to_csv(tmp, index=False)
    tmp.replace(_AUDIT_PATH)


def _export_dashboard_csv(db_path: str | Path) -> None:
    for resolution, kwargs, filename in (
        ("5m", {"trading_days": 5}, "vix_dashboard_5d_5m.csv"),
        ("halfday", {"start_date": LIVE_DASHBOARD_PARAMS["halfday_history_start"]}, "vix_dashboard_2026_ytd_halfday.csv"),
    ):
        rows = query_series(resolution, db_path=db_path, **kwargs)
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("timestamp")
        path = _OUT / filename
        tmp = path.with_suffix(".tmp.csv")
        df.to_csv(tmp, index=False)
        tmp.replace(path)


def _as_shanghai_datetime(value=None) -> datetime:
    if value is None:
        return datetime.now(TZ)
    dt = pd.Timestamp(value).to_pydatetime()
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)


@rqdata_locked(timeout_seconds=45)
def run_once(
    timestamp=None,
    *,
    refresh_plans: bool = True,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict:
    requested_now = _as_shanghai_datetime(timestamp)
    actual_now = datetime.now(TZ)
    if timestamp is not None:
        delay_seconds = (actual_now - requested_now).total_seconds()
        if requested_now.date() == actual_now.date() and delay_seconds > 90:
            raise RuntimeError(
                f"refusing stale live slot {requested_now.isoformat()} after "
                f"{delay_seconds:.0f}s lock/start delay; historical catch-up will repair it"
            )
    ensure_rq()
    now = requested_now
    date = pd.Timestamp(now.date())
    sample_ts = pd.Timestamp(now.replace(second=0, microsecond=0, tzinfo=None))
    hhmm = sample_ts.strftime("%H:%M")
    if hhmm not in LIVE_DASHBOARD_PARAMS["sample_times"]:
        raise RuntimeError(f"{hhmm} is not a configured completed five-minute point")

    latest = latest_trading_dates(1, asof=date)[-1]
    if latest != date:
        raise RuntimeError(f"{date.date()} is not a Chinese trading date")

    quota_before = _safe_quota_snapshot(db_path)
    plans: dict[str, pd.DataFrame] = {}
    for item in ROSTER:
        symbol = item["symbol"]
        plans[symbol] = load_contract_plan(symbol, date, force=refresh_plans)

    union_ids = sorted(
        {
            str(order_book_id)
            for plan in plans.values()
            for order_book_id in plan["order_book_id"]
        }
    )
    ticks = _tick_frame(union_ids)
    provider_ts = ticks["tick_datetime"].dropna().max() if not ticks.empty else None

    per_inst = []
    audits = []
    valid_contracts = 0
    missing_quotes = 0
    for item in ROSTER:
        symbol = item["symbol"]
        plan = plans[symbol]
        snap, point, status = _snapshot_from_ticks(
            symbol, date, sample_ts, plan, ticks
        )
        result = instrument_vix_from_snapshot(symbol, date, snap)
        audit = {
            "timestamp": sample_ts,
            "symbol": symbol,
            "status": status,
            "expected_contracts": int(len(plan)),
            "valid_prices": int(len(point)),
            "near_days": int(plan["days"].min()),
            "next_days": int(plan["days"].max()),
            "price_source": "current_snapshot.last",
            "provider_timestamp": provider_ts,
        }
        valid_contracts += int(len(point))
        missing_quotes += max(0, int(len(plan)) - int(len(point)))
        if result is None:
            if status == "chain_ready":
                audit["status"] = "vix_calculation_failed"
        else:
            result = dict(result)
            result["group"] = item["group"]
            per_inst.append(result)
            audit["status"] = "ok" if result.get("ok") else "invalid_vix"
            audit["vix"] = result.get("vix")
            audit["oi"] = result.get("oi")
        audits.append(audit)

    row = assemble_vix_row(sample_ts, per_inst)
    row["timestamp"] = pd.Timestamp(row.pop("date"))
    row["expected_instruments"] = len(ROSTER)
    row["missing_instruments"] = len(ROSTER) - int(row["n_instruments"])
    row["valid_contracts"] = valid_contracts
    row["missing_quotes"] = missing_quotes
    row["provider_timestamp"] = provider_ts
    row["calculated_at"] = datetime.now(TZ).replace(tzinfo=None)

    quota_after = _safe_quota_snapshot(db_path)
    before = quota_before.get("bytes_used")
    after = quota_after.get("bytes_used")
    row["quota_bytes_used"] = (
        int(after - before) if before is not None and after is not None else None
    )

    if not is_publishable_point(row):
        _save_audits(audits)
        message = json.dumps(
            {
                "timestamp": str(sample_ts),
                "valid_instruments": row["n_instruments"],
                "expected_instruments": len(ROSTER),
                "action": "skipped_not_published",
            },
            ensure_ascii=False,
        )
        log_event(
            "WARNING",
            "collector_partial_point_skipped",
            message,
            db_path=db_path,
        )
        print(f"partial point skipped; dashboard unchanged: {message}", flush=True)
        return row

    upsert_points(
        [row],
        resolution="5m",
        source="live_current_snapshot_last",
        db_path=db_path,
    )
    if hhmm in LIVE_DASHBOARD_PARAMS["halfday_times"]:
        session = "AM" if hhmm == "11:30" else "PM"
        halfday_row = dict(row)
        halfday_row["session"] = session
        upsert_points(
            [halfday_row],
            resolution="halfday",
            source="live_current_snapshot_last",
            db_path=db_path,
        )

    _save_audits(audits)
    _export_dashboard_csv(db_path)
    log_event(
        "INFO",
        "collector_point",
        json.dumps(
            {
                "timestamp": str(sample_ts),
                "valid_instruments": row["n_instruments"],
                "valid_contracts": valid_contracts,
                "quota_bytes_used": row["quota_bytes_used"],
            },
            ensure_ascii=False,
        ),
        db_path=db_path,
    )
    print(json.dumps(row, default=str, ensure_ascii=False, indent=2), flush=True)
    return row


def _next_slot(now: datetime, skip_date=None) -> datetime:
    dates = [now.date(), now.date() + timedelta(days=1)]
    for day in dates:
        if skip_date is not None and day == skip_date:
            continue
        for hhmm in LIVE_DASHBOARD_PARAMS["sample_times"]:
            hh, mm = map(int, hhmm.split(":"))
            candidate = datetime(day.year, day.month, day.day, hh, mm, 8, tzinfo=TZ)
            if candidate > now:
                return candidate
    day = now.date() + timedelta(days=2)
    hh, mm = map(int, LIVE_DASHBOARD_PARAMS["sample_times"][0].split(":"))
    return datetime(day.year, day.month, day.day, hh, mm, 8, tzinfo=TZ)


def monitor_forever(*, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    last_plan_date = None
    skipped_date = None
    while True:
        now = datetime.now(TZ)
        target = _next_slot(now, skip_date=skipped_date)
        time.sleep(max(0.0, (target - now).total_seconds()))
        woke_at = datetime.now(TZ)
        delay_seconds = (woke_at - target).total_seconds()
        if delay_seconds > 90:
            message = (
                f"skipped stale slot {target.isoformat()} after "
                f"{delay_seconds:.0f}s suspension; historical backfill required"
            )
            print(message, flush=True)
            log_event("WARNING", "collector_missed_slot", message, db_path=db_path)
            continue
        try:
            refresh = last_plan_date != target.date()
            run_once(target, refresh_plans=refresh, db_path=db_path)
            last_plan_date = target.date()
            skipped_date = None
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            print(f"monitor error at {target}: {message}", flush=True)
            log_event("ERROR", "collector_error", message, db_path=db_path)
            if "not a Chinese trading date" in message:
                skipped_date = target.date()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--no-refresh-plans", action="store_true")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    try:
        if args.once:
            run_once(
                args.timestamp,
                refresh_plans=not args.no_refresh_plans,
                db_path=args.db,
            )
        else:
            monitor_forever(db_path=args.db)
    except KeyboardInterrupt:
        print("collector stopped; all completed points are already committed")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
