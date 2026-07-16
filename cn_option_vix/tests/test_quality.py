import pandas as pd
from cn_option_vix.pipeline.one_day import compute_day
from cn_option_vix.pipeline.quality import summarize_quality

def test_spreads_present():
    row = compute_day("2024-06-03")
    assert "spread_index_bluechip" in row
    assert "spread_bluechip_szgrowth" in row
    assert "dq_flags" in row
    # 沪深300 vol via Index VIX (IO) vs blue_chip ETF group => a real number on this date
    assert row["spread_index_bluechip"] is not None

def test_summarize_quality():
    df = pd.DataFrame([
        {"n_instruments": 12, "dq_flags": 0},
        {"n_instruments": 11, "dq_flags": 1},
    ])
    s = summarize_quality(df)
    assert s["n_days"] == 2
    assert s["days_with_flags"] == 1
    assert abs(s["mean_instruments"] - 11.5) < 1e-9
