"""Live half-hour VIX monitor using RQData current level-1 snapshots.

Historical 30-minute data use bar ``close``. At a live observation point the
matching quantity is the snapshot ``last`` price. Bid/ask midpoints are not used,
so the historical and live series share one price convention.
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

from cn_option_vix.config import INTRADAY_PARAMS, ROSTER
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

TZ = ZoneInfo("Asia/Shanghai")
_OUT = Path(__file__).resolve().parent.parent / "outputs"
_LIVE_PARQUET = _OUT / "vix_30m_live.parquet"
_LIVE_CSV = _OUT / "vix_30m_live.csv"
_LIVE_AUDIT = _OUT / "vix_30m_live_audit.csv"


def _tick_frame(ids: list[str]) -> pd.DataFrame:
    frames = []
    for batch in _chunks(ids):
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


def _live_snapshot(symbol: str, date, timestamp, plan: pd.DataFrame):
    ticks = _tick_frame(plan["order_book_id"].astype(str).tolist())
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
    point["timestamp"] = pd.Timestamp(timestamp)
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
    if any(df.empty for df in by_expiry.values()):
        return None, point, "missing_snapshot_for_expiry"
    return (
        {
            "underlying": symbol,
            "date": pd.Timestamp(date).normalize(),
            "timestamp": pd.Timestamp(timestamp),
            "expiries": [near_d, next_d],
            "by_expiry": by_expiry,
            "price_source": "current_snapshot.last",
        },
        point,
        "chain_ready",
    )


def _append_row(path: Path, row: dict, index: str) -> pd.DataFrame:
    new = pd.DataFrame([row]).set_index(index)
    if path.exists():
        old = pd.read_parquet(path)
        combined = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    else:
        combined = new.sort_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(path)
    return combined


def run_once(timestamp=None, refresh_plans: bool = True) -> dict:
    """Pull one live chain snapshot and append one half-hour VIX row."""
    ensure_rq()
    now = datetime.now(TZ) if timestamp is None else pd.Timestamp(timestamp).to_pydatetime()
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    else:
        now = now.astimezone(TZ)
    date = pd.Timestamp(now.date())
    sample_ts = pd.Timestamp(now.replace(second=0, microsecond=0, tzinfo=None))

    latest = latest_trading_dates(1, asof=date)[-1]
    if latest != date:
        raise RuntimeError(f"{date.date()} is not a Chinese trading date")

    hhmm = sample_ts.strftime("%H:%M")
    if hhmm not in INTRADAY_PARAMS["sample_times"]:
        raise RuntimeError(
            f"{hhmm} is not a configured completed half-hour point: "
            f"{INTRADAY_PARAMS['sample_times']}"
        )

    quota_before = quota_snapshot()
    per_inst = []
    audits = []
    for item in ROSTER:
        symbol = item["symbol"]
        plan = load_contract_plan(symbol, date, force=refresh_plans)
        snap, point, status = _live_snapshot(symbol, date, sample_ts, plan)
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
        }
        if result is None:
            if status == "chain_ready":
                audit["status"] = "vix_calculation_failed"
        else:
            result = dict(result)
            result["group"] = item["group"]
            per_inst.append(result)
            audit["status"] = "ok" if result.get("ok") else "invalid_vix"
            audit["vix"] = result.get("vix")
        audits.append(audit)

    row = assemble_vix_row(sample_ts, per_inst)
    row["timestamp"] = pd.Timestamp(row.pop("date"))
    for item in ROSTER:
        row.setdefault("iv_" + item["symbol"], None)
    row["expected_instruments"] = len(ROSTER)
    row["missing_instruments"] = len(ROSTER) - int(row["n_instruments"])

    _OUT.mkdir(parents=True, exist_ok=True)
    live = _append_row(_LIVE_PARQUET, row, "timestamp")
    live.to_csv(_LIVE_CSV)

    audit_df = pd.DataFrame(audits)
    if _LIVE_AUDIT.exists():
        old_audit = pd.read_csv(_LIVE_AUDIT, parse_dates=["timestamp"])
        old_audit = old_audit[
            ~(
                (old_audit["timestamp"] == sample_ts)
                & old_audit["symbol"].isin(audit_df["symbol"])
            )
        ]
        audit_df = pd.concat([old_audit, audit_df], ignore_index=True)
    audit_df.sort_values(["timestamp", "symbol"]).to_csv(_LIVE_AUDIT, index=False)

    quota_after = quota_snapshot()
    before = quota_before.get("bytes_used")
    after = quota_after.get("bytes_used")
    row["quota_bytes_used"] = int(after - before) if before is not None and after is not None else None
    print(json.dumps(row, default=str, ensure_ascii=False, indent=2))
    return row


def _next_slot(now: datetime) -> datetime:
    candidates = []
    for hhmm in INTRADAY_PARAMS["sample_times"]:
        hh, mm = map(int, hhmm.split(":"))
        candidate = now.replace(hour=hh, minute=mm, second=5, microsecond=0)
        if candidate > now:
            candidates.append(candidate)
    if candidates:
        return min(candidates)
    tomorrow = now.date() + timedelta(days=1)
    hh, mm = map(int, INTRADAY_PARAMS["sample_times"][0].split(":"))
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, hh, mm, 5, tzinfo=TZ)


def monitor_forever() -> None:
    """Run at fixed Shanghai-market slots without cumulative sleep drift."""
    last_plan_date = None
    while True:
        now = datetime.now(TZ)
        target = _next_slot(now)
        time.sleep(max(0.0, (target - now).total_seconds()))
        try:
            refresh = last_plan_date != target.date()
            run_once(target, refresh_plans=refresh)
            last_plan_date = target.date()
        except Exception as exc:
            print(f"monitor error at {target}: {type(exc).__name__}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Shanghai time, e.g. '2026-07-13 14:30'; only with --once",
    )
    parser.add_argument("--no-refresh-plans", action="store_true")
    args = parser.parse_args()
    if args.once:
        run_once(args.timestamp, refresh_plans=not args.no_refresh_plans)
    else:
        monitor_forever()


if __name__ == "__main__":
    main()
