"""Seed the dashboard database from existing 30m history and recent 5m RQData."""
from __future__ import annotations

import argparse
from pathlib import Path

from cn_option_vix.pipeline.build_recent_5m import build_recent_5m
from cn_option_vix.web.storage import (
    DEFAULT_DB_PATH,
    database_summary,
    import_halfday_history,
    initialise,
)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _default_history_path() -> Path:
    candidates = [
        PACKAGE_ROOT / "outputs" / "vix_30m_2y.parquet",
        PACKAGE_ROOT / "outputs" / "vix_30m_2y.csv",
        PACKAGE_ROOT / "outputs" / "vix_30m_latest5.parquet",
        PACKAGE_ROOT / "outputs" / "vix_30m_latest5.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[1]


def bootstrap(
    *,
    history_30m: str | Path | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    five_minute_days: int = 5,
    asof=None,
    force_5m: bool = False,
    skip_5m: bool = False,
) -> dict:
    initialise(db_path)
    history_path = Path(history_30m) if history_30m else _default_history_path()
    if history_path.exists():
        count = import_halfday_history(history_path, db_path=db_path)
        print(f"imported/upserted {count} half-day points from {history_path}")
    else:
        print(f"warning: 30m history not found: {history_path}")

    if not skip_5m:
        build_recent_5m(
            n_days=five_minute_days,
            asof=asof,
            force=force_5m,
            db_path=db_path,
        )
    summary = database_summary(db_path)
    print(summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-30m", default=None)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--asof", default=None)
    parser.add_argument("--force-5m", action="store_true")
    parser.add_argument(
        "--skip-5m",
        action="store_true",
        help="seed only the two-month half-day history; do not call RQData",
    )
    args = parser.parse_args()
    bootstrap(
        history_30m=args.history_30m,
        db_path=args.db,
        five_minute_days=args.days,
        asof=args.asof,
        force_5m=args.force_5m,
        skip_5m=args.skip_5m,
    )


if __name__ == "__main__":
    main()
