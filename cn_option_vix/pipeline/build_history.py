"""Backfill the VIX history over a date range -> parquet + csv."""
import os
import pandas as pd
import rqdatac as rq
from cn_option_vix.config import GROUPS, require_rqdata_uri
from cn_option_vix.pipeline.one_day import compute_day

_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
_PUBLISHED = ["overall"] + list(GROUPS.keys())  # overall + 5 groups

def build_history(start, end, out_path=None):
    rq.init(uri=require_rqdata_uri())
    dates = rq.get_trading_dates(start, end)
    rows = []
    for i, d in enumerate(dates):
        ds = str(pd.Timestamp(d).date())
        try:
            rows.append(compute_day(ds))
        except Exception as e:
            print(f"  skip {ds}: {e}")
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(dates)} days ...")
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("no rows computed")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    # write outputs
    os.makedirs(_OUT_DIR, exist_ok=True)
    parquet_path = out_path or os.path.join(_OUT_DIR, "vix_series.parquet")
    df.to_parquet(parquet_path)
    csv_cols = [c for c in _PUBLISHED if c in df.columns]
    df[csv_cols].to_csv(os.path.join(_OUT_DIR, "vix_series.csv"))
    # data-quality summary
    from cn_option_vix.pipeline.quality import summarize_quality
    import json
    q = summarize_quality(df)
    with open(os.path.join(_OUT_DIR, "quality_report.json"), "w") as f:
        json.dump(q, f, indent=2)
    return df
