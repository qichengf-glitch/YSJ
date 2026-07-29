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
    assert overall["count_20"] == 20
    assert overall["count_60"] == 60
    # One daily observation is used: the 15:00 point, not both half-days.
    assert overall["avg_20"] == pd.Series([21.0 + i for i in range(45, 65)]).mean()
    assert overall["variance_20"] == pd.Series([21.0 + i for i in range(45, 65)]).var(ddof=1)
    assert overall["avg_60"] == pd.Series([21.0 + i for i in range(5, 65)]).mean()
    assert overall["variance_60"] == pd.Series([21.0 + i for i in range(5, 65)]).var(ddof=1)


def test_partial_point_is_never_published(tmp_path: Path):
    db = tmp_path / "live.sqlite"
    full = _row("2026-07-16 13:15")
    partial = _row("2026-07-16 13:20")
    partial["n_instruments"] = 3
    partial["index_vix"] = None
    partial["blue_chip"] = None
    partial["sz_growth"] = None
    upsert_points([full, partial], resolution="5m", source="test", db_path=db)

    assert latest_by_resolution("5m", db, published_only=False)["timestamp"].endswith("13:20:00")
    assert latest_by_resolution("5m", db)["timestamp"].endswith("13:15:00")
    points = query_series("5m", db_path=db, trading_days=1)
    assert [point["timestamp"] for point in points] == ["2026-07-16 13:15:00"]


def test_moving_average_snapshot_computes_relative_spread_after_subtraction(tmp_path: Path):
    from cn_option_vix.web.storage import moving_average_snapshot

    db = tmp_path / "live.sqlite"
    rows = []
    overall_values = [20.0, 21.0, 22.0, 23.0]
    hard_values = [21.0, 23.0, 25.0, 27.0]  # spreads: 1, 2, 3, 4
    for day, overall, hard in zip(
        pd.bdate_range("2026-07-01", periods=4),
        overall_values,
        hard_values,
    ):
        rows.append(_row(f"{day.date()} 15:00", overall=overall, hard=hard))
    upsert_points(rows, resolution="halfday", source="test", db_path=db)

    # The latest panel values must come from one complete, matched 5-minute row.
    live = _row("2026-07-08 13:20", overall=30.0, hard=35.5)
    upsert_points([live], resolution="5m", source="test", db_path=db)

    summary = moving_average_snapshot(db_path=db, windows=(4,))
    hard = next(row for row in summary["rows"] if row["key"] == "hard_tech")
    expected = pd.Series([1.0, 2.0, 3.0, 4.0])

    assert hard["latest"] == 35.5
    assert hard["latest_spread"] == 5.5
    assert hard["spread_mean_4"] == expected.mean()
    assert hard["spread_std_4"] == expected.std(ddof=1)
    assert hard["spread_variance_4"] == expected.var(ddof=1)
    assert hard["spread_count_4"] == 4

    overall = next(row for row in summary["rows"] if row["key"] == "overall")
    assert overall["latest_spread"] is None
    assert overall["spread_std_4"] is None
    assert overall["spread_variance_4"] is None
    assert overall["spread_count_4"] == 0
