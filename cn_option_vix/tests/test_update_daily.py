import pandas as pd
from cn_option_vix.pipeline.update_daily import update_daily

def test_update_appends_latest(tmp_path):
    p = tmp_path / "vix.parquet"
    seed = pd.DataFrame({"overall": [20.0]}, index=pd.to_datetime(["2024-06-03"]))
    seed.index.name = "date"
    seed.to_parquet(p)
    df = update_daily(out_path=str(p), asof="2024-06-04")
    assert pd.Timestamp("2024-06-04") in df.index
    assert pd.Timestamp("2024-06-03") in df.index
