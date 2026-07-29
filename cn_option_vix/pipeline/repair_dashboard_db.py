"""Back up the dashboard SQLite DB and remove partial/non-publishable points."""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from cn_option_vix.web.storage import (
    DEFAULT_DB_PATH,
    delete_unpublishable_points,
    latest_by_resolution,
)


def repair(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db.with_name(f"{db.name}.backup_before_pure_vix_{stamp}")
    shutil.copy2(db, backup)
    removed = delete_unpublishable_points(db_path=db)
    latest_5m = latest_by_resolution("5m", db)
    latest_half = latest_by_resolution("halfday", db)
    print(f"backup: {backup}")
    print(f"removed partial/non-publishable points: {removed}")
    print(f"latest published 5m: {latest_5m['timestamp'] if latest_5m else None}")
    print(f"latest published halfday: {latest_half['timestamp'] if latest_half else None}")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    repair(args.db)


if __name__ == "__main__":
    main()
