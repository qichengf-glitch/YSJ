"""Repair missing five-minute dashboard observations through a trading date.

This is the restart-safe bridge between historical RQData bars and the live
collector. It inspects SQLite first, downloads only trading dates whose
completed five-minute slots are incomplete, and then verifies the database.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from cn_option_vix.config import LIVE_DASHBOARD_PARAMS
from cn_option_vix.data.five_min_chains import expected_5m_timestamps
from cn_option_vix.data.intraday_chains import latest_trading_dates, trading_dates_between
from cn_option_vix.data.rq_process_lock import rqdata_locked
from cn_option_vix.pipeline.build_recent_5m import build_recent_5m
from cn_option_vix.web.storage import (
    DEFAULT_DB_PATH,
    PUBLISHED_POINT_SQL,
    initialise,
    log_event,
)

TZ = ZoneInfo("Asia/Shanghai")


def _now_shanghai(value=None) -> datetime:
    if value is None:
        return datetime.now(TZ)
    dt = pd.Timestamp(value).to_pydatetime()
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)


def completed_slot_count(date, *, now=None, settle_seconds: int = 30) -> int:
    """Number of five-minute bars that should already exist for ``date``."""
    day = pd.Timestamp(date).normalize()
    current = _now_shanghai(now)
    current_day = pd.Timestamp(current.date())
    slots = expected_5m_timestamps(day)
    if day < current_day:
        return len(slots)
    if day > current_day:
        return 0
    cutoff = pd.Timestamp(current.replace(tzinfo=None)) - pd.Timedelta(
        seconds=max(0, int(settle_seconds))
    )
    return sum(ts <= cutoff for ts in slots)


def _published_counts(db_path: str | Path) -> dict[pd.Timestamp, int]:
    initialise(db_path)
    sql = f"""
        SELECT substr(timestamp, 1, 10) AS trading_date, count(*) AS n
        FROM vix_points
        WHERE resolution='5m' AND {PUBLISHED_POINT_SQL}
        GROUP BY substr(timestamp, 1, 10)
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(sql).fetchall()
    return {pd.Timestamp(day).normalize(): int(n) for day, n in rows}


def _latest_db_date(db_path: str | Path) -> pd.Timestamp | None:
    initialise(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT max(substr(timestamp,1,10)) FROM vix_points WHERE resolution='5m'"
        ).fetchone()
    return pd.Timestamp(row[0]).normalize() if row and row[0] else None


def dates_requiring_sync(
    trading_dates: list[pd.Timestamp],
    counts: dict[pd.Timestamp, int],
    *,
    now=None,
    settle_seconds: int = 30,
) -> list[dict]:
    missing = []
    for date in trading_dates:
        date = pd.Timestamp(date).normalize()
        expected = completed_slot_count(
            date, now=now, settle_seconds=settle_seconds
        )
        actual = int(counts.get(date, 0))
        if expected > actual:
            missing.append(
                {
                    "date": date,
                    "expected_points": expected,
                    "actual_points": actual,
                    "missing_points": expected - actual,
                }
            )
    return missing


@rqdata_locked
def sync_missing_5m(
    *,
    through=None,
    from_date=None,
    db_path: str | Path = DEFAULT_DB_PATH,
    reserve_mib: float = 64.0,
    lookback_trading_days: int = 10,
    settle_seconds: int = 30,
    dry_run: bool = False,
    best_effort: bool = False,
    now=None,
) -> dict:
    """Backfill every incomplete trading date and return a verification report."""
    db_path = Path(db_path)
    current = _now_shanghai(now)
    end = (
        pd.Timestamp(through).normalize()
        if through is not None
        else latest_trading_dates(1)[-1]
    )
    latest_db = _latest_db_date(db_path)
    if from_date is not None:
        start = pd.Timestamp(from_date).normalize()
    else:
        lookback_start = latest_trading_dates(
            max(
                int(LIVE_DASHBOARD_PARAMS["history_trading_days"]),
                int(lookback_trading_days),
            ),
            asof=end,
        )[0]
        start = min(latest_db, lookback_start) if latest_db is not None else lookback_start

    trading_dates = trading_dates_between(start, end)
    before_counts = _published_counts(db_path)
    required = dates_requiring_sync(
        trading_dates,
        before_counts,
        now=current,
        settle_seconds=settle_seconds,
    )
    report = {
        "started_at": current.isoformat(),
        "database": str(db_path),
        "from_date": str(start.date()),
        "through": str(end.date()),
        "required": [
            {**item, "date": str(item["date"].date())} for item in required
        ],
        "completed": [],
        "errors": [],
        "dry_run": bool(dry_run),
    }
    log_event(
        "INFO",
        "catchup_started",
        json.dumps(
            {
                "from": report["from_date"],
                "through": report["through"],
                "dates": len(required),
            },
            ensure_ascii=False,
        ),
        db_path=db_path,
    )

    for item in required:
        date = item["date"]
        if dry_run:
            continue
        try:
            print(
                f"[catchup] {date.date()} actual={item['actual_points']} "
                f"expected={item['expected_points']}",
                flush=True,
            )
            build_recent_5m(
                n_days=1,
                asof=str(date.date()),
                force=True,
                db_path=db_path,
                out_stem=f"vix_5m_{date.strftime('%Y%m%d')}",
                reserve_mib=reserve_mib,
            )
            report["completed"].append(str(date.date()))
        except Exception as exc:
            error = {
                "date": str(date.date()),
                "error": f"{type(exc).__name__}: {exc}",
            }
            report["errors"].append(error)
            log_event(
                "ERROR",
                "catchup_date_error",
                json.dumps(error, ensure_ascii=False),
                db_path=db_path,
            )
            print(f"[catchup] ERROR {error}", flush=True)
            if not best_effort:
                raise

    after_counts = _published_counts(db_path)
    remaining = dates_requiring_sync(
        trading_dates,
        after_counts,
        now=current,
        settle_seconds=settle_seconds,
    )
    report["remaining"] = [
        {**item, "date": str(item["date"].date())} for item in remaining
    ]
    report["finished_at"] = datetime.now(TZ).isoformat()
    level = "INFO" if not remaining and not report["errors"] else "WARNING"
    log_event(
        level,
        "catchup_finished",
        json.dumps(
            {
                "completed": report["completed"],
                "errors": report["errors"],
                "remaining": report["remaining"],
            },
            ensure_ascii=False,
        ),
        db_path=db_path,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if remaining and not best_effort and not dry_run:
        raise RuntimeError(f"catch-up incomplete: {remaining}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through", default=None, help="inclusive YYYY-MM-DD")
    parser.add_argument("--from-date", default=None, help="inclusive YYYY-MM-DD")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reserve-mib", type=float, default=64.0)
    parser.add_argument("--lookback-trading-days", type=int, default=10)
    parser.add_argument("--settle-seconds", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--best-effort", action="store_true")
    args = parser.parse_args()
    sync_missing_5m(
        through=args.through,
        from_date=args.from_date,
        db_path=args.db,
        reserve_mib=args.reserve_mib,
        lookback_trading_days=args.lookback_trading_days,
        settle_seconds=args.settle_seconds,
        dry_run=args.dry_run,
        best_effort=args.best_effort,
    )


if __name__ == "__main__":
    main()
