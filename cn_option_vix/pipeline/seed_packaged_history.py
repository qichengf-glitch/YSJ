"""Seed packaged half-day history into a persistent dashboard database."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from cn_option_vix.web.storage import import_halfday_history, initialise


def _history_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path).reset_index()
    return pd.read_csv(path)


def packaged_trading_dates(history_path: str | Path) -> set[str]:
    """Return trading dates represented by packaged 11:30/15:00 rows."""
    path = Path(history_path)
    if not path.exists():
        raise FileNotFoundError(path)
    frame = _history_frame(path)
    time_col = next(
        (name for name in ("timestamp", "datetime", "date", "index") if name in frame),
        None,
    )
    if time_col is None:
        raise ValueError(f"no timestamp column in {path}: {list(frame.columns)}")
    timestamps = pd.to_datetime(frame[time_col], errors="raise")
    eligible = timestamps[timestamps.dt.strftime("%H:%M").isin(("11:30", "15:00"))]
    return set(eligible.dt.strftime("%Y-%m-%d").unique())


def stored_halfday_trading_dates(db_path: str | Path) -> set[str]:
    initialise(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(timestamp,1,10) AS trading_date "
            "FROM vix_points WHERE resolution='halfday'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def _stored_point_count(db_path: str | Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT count(*) FROM vix_points").fetchone()[0])


def seed_packaged_history(
    *,
    history_path: str | Path,
    db_path: str | Path,
    backup_path: str | Path | None = None,
) -> dict:
    """Import packaged history when SQLite does not yet contain the full package."""
    history = Path(history_path)
    database = Path(db_path)
    packaged_dates = packaged_trading_dates(history)
    stored_dates = stored_halfday_trading_dates(database)
    missing_dates = packaged_dates - stored_dates

    result = {
        "imported": False,
        "before_days": len(stored_dates),
        "after_days": len(stored_dates),
        "packaged_days": len(packaged_dates),
        "missing_packaged_days": len(missing_dates),
        "backup_path": None,
    }
    if not missing_dates:
        return result

    backup = Path(backup_path) if backup_path else Path(
        f"{database}.backup-before-vix-history-import"
    )
    if _stored_point_count(database) > 0 and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        result["backup_path"] = str(backup)

    imported_points = import_halfday_history(history, db_path=database)
    result.update(
        imported=True,
        imported_points=imported_points,
        after_days=len(stored_halfday_trading_dates(database)),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-30m", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--backup", default=None)
    args = parser.parse_args()

    result = seed_packaged_history(
        history_path=args.history_30m,
        db_path=args.db,
        backup_path=args.backup,
    )
    if result["imported"]:
        print(
            "packaged half-day history: imported "
            f"{result['imported_points']} points; "
            f"trading days {result['before_days']} -> {result['after_days']}"
        )
        if result["backup_path"]:
            print(f"consistent SQLite backup: {result['backup_path']}")
    else:
        print(
            "packaged half-day history: already complete "
            f"({result['before_days']} trading days)"
        )


if __name__ == "__main__":
    main()
