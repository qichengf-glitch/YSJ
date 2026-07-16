"""Validate the reconstructed 50ETF VIX against the official 中国波指 iVIX (000188)."""
import os
import numpy as np
import pandas as pd
import rqdatac as rq
from cn_option_vix.config import RQDATAC_URI, IVIX_CODE, IVIX_WINDOW
from cn_option_vix.core.instrument_vix import instrument_vix

_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

def compare_to_ivix(symbol="510050.XSHG", window=IVIX_WINDOW):
    rq.init(uri=RQDATAC_URI)
    start, end = window
    dates = rq.get_trading_dates(start, end)
    ours = {}
    for d in dates:
        ds = str(pd.Timestamp(d).date())
        try:
            res = instrument_vix(symbol, ds)
        except Exception:
            res = None
        if res and res.get("ok"):
            ours[pd.Timestamp(ds)] = res["vix"]
    ours = pd.Series(ours, name="ours").sort_index()

    off = rq.get_price(IVIX_CODE, start_date=start, end_date=end, frequency="1d", fields="close")
    # off may be a Series or a 1-col DataFrame with a MultiIndex; normalize to a date-indexed Series
    off = off["close"] if hasattr(off, "columns") else off
    off.index = [pd.Timestamp(x[-1]) if isinstance(x, tuple) else pd.Timestamp(x) for x in off.index]
    off = pd.Series(off.values, index=off.index, name="ivix").sort_index()

    joined = pd.concat([ours, off], axis=1).dropna()
    corr = float(joined["ours"].corr(joined["ivix"]))
    rmse = float(np.sqrt(((joined["ours"] - joined["ivix"]) ** 2).mean()))
    bias = float((joined["ours"] - joined["ivix"]).mean())

    # overlay plot (best-effort)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        os.makedirs(os.path.join(_OUT_DIR, "plots"), exist_ok=True)
        ax = joined.plot(title=f"50ETF VIX vs 中国波指 iVIX  corr={corr:.3f} rmse={rmse:.2f}")
        ax.figure.savefig(os.path.join(_OUT_DIR, "plots", "ivix_validation.png"), dpi=110, bbox_inches="tight")
        plt.close(ax.figure)
    except Exception:
        pass

    return {"n": int(len(joined)), "corr": corr, "rmse": rmse, "bias": bias,
            "start": str(joined.index.min().date()) if len(joined) else None,
            "end": str(joined.index.max().date()) if len(joined) else None}
