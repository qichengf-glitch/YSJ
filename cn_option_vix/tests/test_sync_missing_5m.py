from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from cn_option_vix.pipeline.monitor_repair import _next_run
from cn_option_vix.pipeline.sync_missing_5m import (
    completed_slot_count,
    dates_requiring_sync,
)

TZ = ZoneInfo("Asia/Shanghai")


def test_completed_slot_count_past_and_current_session():
    now = datetime(2026, 7, 23, 13, 17, tzinfo=TZ)
    assert completed_slot_count("2026-07-22", now=now) == 48
    # 24 morning bars through 11:30 and three afternoon bars through 13:15.
    assert completed_slot_count("2026-07-23", now=now) == 27
    assert completed_slot_count("2026-07-24", now=now) == 0


def test_dates_requiring_sync_only_returns_incomplete_dates():
    dates = [pd.Timestamp("2026-07-21"), pd.Timestamp("2026-07-22")]
    counts = {
        pd.Timestamp("2026-07-21"): 48,
        pd.Timestamp("2026-07-22"): 17,
    }
    missing = dates_requiring_sync(
        dates,
        counts,
        now=datetime(2026, 7, 23, 9, 0, tzinfo=TZ),
    )
    assert len(missing) == 1
    assert missing[0]["date"] == pd.Timestamp("2026-07-22")
    assert missing[0]["missing_points"] == 31


def test_repair_scheduler_uses_next_configured_slot():
    now = datetime(2026, 7, 23, 14, 0, tzinfo=TZ)
    assert _next_run(now, ["08:50", "15:20"]) == datetime(
        2026, 7, 23, 15, 20, tzinfo=TZ
    )
    after_close = datetime(2026, 7, 23, 16, 0, tzinfo=TZ)
    assert _next_run(after_close, ["08:50", "15:20"]) == datetime(
        2026, 7, 24, 8, 50, tzinfo=TZ
    )
