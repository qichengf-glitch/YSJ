from pathlib import Path

import pandas as pd

from cn_option_vix.web.storage import (
    import_halfday_history,
    latest_by_resolution,
    query_series,
    upsert_points,
)


def _row(ts, overall=20.0, hard=26.0):
    return {
        "timestamp": ts,
        "overall": overall,
        "index_vix": 21.0,
        "blue_chip": 19.0,
        "sz_growth": 23.0,
        "mid_small": 24.0,
        "hard_tech": hard,
        "n_instruments": 12,
        "expected_instruments": 12,
    }


def test_upsert_computes_all_group_spreads(tmp_path: Path):
    db = tmp_path / "live.sqlite"
    upsert_points([_row("2026-07-14 10:00")], resolution="5m", source="test", db_path=db)
    point = latest_by_resolution("5m", db)
    assert point["spread_index_vix_overall"] == 1.0
    assert point["spread_blue_chip_overall"] == -1.0
    assert point["spread_sz_growth_overall"] == 3.0
    assert point["spread_mid_small_overall"] == 4.0
    assert point["spread_hard_tech_overall"] == 6.0


def test_query_5m_keeps_latest_five_trading_dates(tmp_path: Path):
    db = tmp_path / "live.sqlite"
    rows = []
    for day in pd.bdate_range("2026-07-01", periods=7):
        rows.append(_row(f"{day.date()} 10:00"))
    upsert_points(rows, resolution="5m", source="test", db_path=db)
    result = query_series("5m", db_path=db, trading_days=5)
    assert len(result) == 5
    assert result[0]["timestamp"].startswith("2026-07-03")
    assert result[-1]["timestamp"].startswith("2026-07-09")


def test_import_halfday_uses_only_1130_and_1500(tmp_path: Path):
    history = tmp_path / "history.csv"
    pd.DataFrame(
        [
            _row("2026-07-13 11:00"),
            _row("2026-07-13 11:30"),
            _row("2026-07-13 15:00"),
        ]
    ).to_csv(history, index=False)
    db = tmp_path / "live.sqlite"
    assert import_halfday_history(history, db_path=db) == 2
    result = query_series("halfday", db_path=db, months=2)
    assert [row["session"] for row in result] == ["AM", "PM"]


def test_halfday_explicit_start_and_moving_averages(tmp_path: Path):
    from cn_option_vix.web.storage import moving_average_snapshot

    db = tmp_path / "live.sqlite"
    rows = []
    for i, day in enumerate(pd.bdate_range("2025-12-29", periods=65)):
        rows.append(_row(f"{day.date()} 11:30", overall=20.0 + i, hard=26.0 + i))
        rows.append(_row(f"{day.date()} 15:00", overall=21.0 + i, hard=27.0 + i))
    upsert_points(rows, resolution="halfday", source="test", db_path=db)

    ytd = query_series("halfday", db_path=db, start_date="2026-01-01")
    assert ytd
    assert ytd[0]["timestamp"] >= "2026-01-01 00:00:00"

    summary = moving_average_snapshot(db_path=db)
    assert summary["available_trading_days"] == 65
    overall = next(row for row in summary["rows"] if row["key"] == "overall")
    assert overall["count_30"] == 30
    assert overall["count_60"] == 60
    # One daily observation is used: the 15:00 point, not both half-days.
    assert overall["avg_30"] == pd.Series([21.0 + i for i in range(35, 65)]).mean()
    assert overall["avg_60"] == pd.Series([21.0 + i for i in range(5, 65)]).mean()


def test_partial_point_is_never_published(tmp_path: Path):
    db = tmp_path / "live.sqlite"
    full = _row("2026-07-14 10:00")
    partial = _row("2026-07-14 10:05")
    partial["n_instruments"] = 3
    upsert_points([full, partial], resolution="5m", source="test", db_path=db)

    assert latest_by_resolution("5m", db, published_only=False)["timestamp"].startswith(
        "2026-07-14 10:05"
    )
    assert latest_by_resolution("5m", db)["timestamp"].startswith("2026-07-14 10:00")
    assert [row["timestamp"] for row in query_series("5m", db_path=db)] == [
        "2026-07-14 10:00:00"
    ]
