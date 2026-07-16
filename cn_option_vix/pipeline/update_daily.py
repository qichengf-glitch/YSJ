"""Idempotent daily update: append one day's VIX row to the parquet history."""
import os
import pandas as pd
import rqdatac as rq
from cn_option_vix.config import GROUPS, require_rqdata_uri
from cn_option_vix.pipeline.one_day import compute_day

_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
_PUBLISHED = ["overall"] + list(GROUPS.keys())

def update_daily(out_path=None, asof=None):
    """Compute `asof` (default: latest trading date) and append to the parquet history.
    Idempotent: re-running a date overwrites that row. Returns the full DataFrame.

    Only connects to RQ when `asof` is None (to resolve the latest trading date); with
    an explicit `asof` and disk-cached chains this runs fully offline."""
    if asof is None:
        rq.init(uri=require_rqdata_uri())
        asof = str(pd.Timestamp(rq.get_latest_trading_date()).date())
    path = out_path or os.path.join(_OUT_DIR, "vix_series.parquet")
    if os.path.exists(path):
        hist = pd.read_parquet(path)
    else:
        hist = pd.DataFrame()
    row = compute_day(asof)
    row = dict(row)
    row["date"] = pd.Timestamp(asof)
    new = pd.DataFrame([row]).set_index("date")
    combined = pd.concat([hist[~hist.index.isin(new.index)], new]).sort_index()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    combined.to_parquet(path)
    csv_cols = [c for c in _PUBLISHED if c in combined.columns]
    if csv_cols:
        combined[csv_cols].to_csv(os.path.join(_OUT_DIR, "vix_series.csv"))
    return combined
