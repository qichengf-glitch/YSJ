import sqlite3
from pathlib import Path

import pandas as pd

from cn_option_vix.pipeline.seed_packaged_history import seed_packaged_history
from cn_option_vix.web.storage import upsert_points


def _row(timestamp: str, overall: float) -> dict:
    return {
        "timestamp": timestamp,
        "overall": overall,
        "index_vix": overall + 1,
        "blue_chip": overall + 2,
        "sz_growth": overall + 3,
        "mid_small": overall + 4,
        "hard_tech": overall + 5,
        "n_instruments": 12,
        "expected_instruments": 12,
    }


def _trading_days(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT count(DISTINCT substr(timestamp,1,10)) "
            "FROM vix_points WHERE resolution='halfday'"
        ).fetchone()[0]


def test_seed_imports_full_package_and_preserves_consistent_backup(tmp_path: Path):
    database = tmp_path / "live.sqlite"
    backup = tmp_path / "before.sqlite"
    upsert_points(
        [_row("2026-07-01 15:00", 20.0)],
        resolution="halfday",
        source="existing",
        db_path=database,
    )

    history = tmp_path / "history.csv"
    rows = []
    for index, day in enumerate(pd.bdate_range("2026-06-29", periods=3)):
        rows.append(_row(f"{day.date()} 11:30", 10.0 + index))
        rows.append(_row(f"{day.date()} 15:00", 11.0 + index))
    pd.DataFrame(rows).to_csv(history, index=False)

    result = seed_packaged_history(
        history_path=history,
        db_path=database,
        backup_path=backup,
    )

    assert result["imported"] is True
    assert result["before_days"] == 1
    assert result["after_days"] == 3
    assert result["packaged_days"] == 3
    assert _trading_days(backup) == 1
    assert _trading_days(database) == 3

    second = seed_packaged_history(
        history_path=history,
        db_path=database,
        backup_path=backup,
    )
    assert second["imported"] is False
    assert second["after_days"] == 3
    assert _trading_days(backup) == 1
