"""Scheduled reconciliation for missed CN VIX five-minute observations."""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from cn_option_vix.pipeline.sync_missing_5m import sync_missing_5m
from cn_option_vix.web.storage import DEFAULT_DB_PATH, log_event

TZ = ZoneInfo("Asia/Shanghai")


def _repair_times() -> list[str]:
    raw = os.environ.get("CN_VIX_REPAIR_TIMES", "08:50,15:20")
    times = sorted({part.strip() for part in raw.split(",") if part.strip()})
    if not times:
        raise ValueError("CN_VIX_REPAIR_TIMES must contain at least one HH:MM")
    for value in times:
        datetime.strptime(value, "%H:%M")
    return times


def _next_run(now: datetime, repair_times: list[str]) -> datetime:
    for offset in range(0, 8):
        day = now.date() + timedelta(days=offset)
        for hhmm in repair_times:
            hh, mm = map(int, hhmm.split(":"))
            candidate = datetime(day.year, day.month, day.day, hh, mm, tzinfo=TZ)
            if candidate > now:
                return candidate
    raise AssertionError("unreachable")


def _run_repair(db_path: str | Path, reserve_mib: float, lookback_days: int) -> None:
    try:
        sync_missing_5m(
            db_path=db_path,
            reserve_mib=reserve_mib,
            lookback_trading_days=lookback_days,
            best_effort=True,
        )
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        print(f"scheduled catch-up error: {message}", flush=True)
        log_event("ERROR", "scheduled_catchup_error", message, db_path=db_path)


def monitor_forever(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    reserve_mib: float = 64.0,
    run_at_start: bool = True,
    lookback_days: int = 10,
) -> None:
    times = _repair_times()
    if run_at_start:
        _run_repair(db_path, reserve_mib, lookback_days)
    while True:
        now = datetime.now(TZ)
        target = _next_run(now, times)
        print(f"next scheduled catch-up: {target.isoformat()}", flush=True)
        time.sleep(max(0.0, (target - now).total_seconds()))
        _run_repair(db_path, reserve_mib, lookback_days)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reserve-mib", type=float, default=64.0)
    parser.add_argument("--lookback-trading-days", type=int, default=10)
    parser.add_argument("--no-startup", action="store_true")
    args = parser.parse_args()
    monitor_forever(
        db_path=args.db,
        reserve_mib=args.reserve_mib,
        run_at_start=not args.no_startup,
        lookback_days=args.lookback_trading_days,
    )


if __name__ == "__main__":
    main()
