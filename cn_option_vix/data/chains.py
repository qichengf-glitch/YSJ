"""Option chain snapshot: near+next expiry, settlement price (close fallback), OI."""
import os
import pandas as pd
import rqdatac as rq
from cn_option_vix.config import VIX_PARAMS, require_rqdata_uri
from cn_option_vix.core.vix_chain import select_near_next

_CACHE = os.path.join(os.path.dirname(__file__), "cache")
_inited = False


def _ensure():
    global _inited
    if not _inited:
        rq.init(uri=require_rqdata_uri())
        _inited = True


_UNIVERSE = None
_UNIVERSE_FILE = os.path.join(_CACHE, "_universe_options.parquet")


def _universe():
    """The full option-instrument universe. Cached in-process AND on disk, because
    `all_instruments('Option')` is a heavy ~220k-row pull that otherwise repeats every
    process and burns RQ traffic quota. Delete `_universe_options.parquet` to refresh."""
    global _UNIVERSE
    if _UNIVERSE is not None:
        return _UNIVERSE
    if os.path.exists(_UNIVERSE_FILE):
        _UNIVERSE = pd.read_parquet(_UNIVERSE_FILE)
        return _UNIVERSE
    _ensure()
    df = rq.all_instruments(type="Option").copy()
    for c in ("listed_date", "de_listed_date", "maturity_date"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    try:
        os.makedirs(_CACHE, exist_ok=True)
        df.to_parquet(_UNIVERSE_FILE)
    except Exception:
        pass
    _UNIVERSE = df
    return _UNIVERSE


def get_chain_snapshot(symbol, date, min_near_days=None):
    """Return {underlying, date, expiries:[near_days, next_days],
    by_expiry:{days: DataFrame[strike,cp,price,oi]}, n_close_fallback} or None."""
    date = pd.Timestamp(date)
    if min_near_days is None:
        min_near_days = VIX_PARAMS["min_near_days"]

    # Cache-first: never re-hit the RQ API for a (symbol, date) we've already pulled.
    # The per-date cache is immutable (settlement is final once the day closes).
    key = symbol.replace(".", "_") + "_" + str(date.date())
    cache_path = os.path.join(_CACHE, key + ".parquet")
    if min_near_days == VIX_PARAMS["min_near_days"] and os.path.exists(cache_path):
        try:
            cached = pd.read_parquet(cache_path)
            days = sorted(int(d) for d in cached["days"].unique())
            if len(days) >= 2:
                by_expiry = {d: cached[cached["days"] == d].drop(columns=["days"]).reset_index(drop=True)
                             for d in days}
                return {"underlying": symbol, "date": date, "expiries": [days[0], days[1]],
                        "by_expiry": by_expiry, "n_close_fallback": 0, "from_cache": True}
        except Exception:
            pass  # fall through to a fresh pull on any cache read error

    u = _universe()
    live = u[(u["underlying_symbol"] == symbol) &
             (u["listed_date"] <= date) & (u["de_listed_date"] >= date)]
    if live.empty:
        return None
    exp_days = {}
    for m in sorted(pd.Series(live["maturity_date"].dropna().unique())):
        exp_days[int((pd.Timestamp(m) - date).days)] = pd.Timestamp(m)
    try:
        near_d, next_d = select_near_next(sorted(exp_days), min_near_days)
    except ValueError:
        return None
    result = {"underlying": symbol, "date": date, "expiries": [near_d, next_d],
              "by_expiry": {}, "n_close_fallback": 0}
    for dd in (near_d, next_d):
        contracts = live[live["maturity_date"] == exp_days[dd]]
        ids = contracts["order_book_id"].tolist()
        px = rq.get_price(ids, start_date=date, end_date=date, frequency="1d",
                          fields=["settlement", "close", "open_interest"])
        if px is None or len(px) == 0:
            return None
        px = px.reset_index()
        pxmap = {row["order_book_id"]: row for _, row in px.iterrows()}
        rows = []
        for _, c in contracts.iterrows():
            row = pxmap.get(c["order_book_id"])
            if row is None:
                continue
            settle = float(row["settlement"]) if pd.notna(row["settlement"]) else 0.0
            close = float(row["close"]) if pd.notna(row["close"]) else 0.0
            price = settle if settle > 0 else close
            if price <= 0:
                continue
            if settle <= 0:
                result["n_close_fallback"] += 1
            oi = float(row["open_interest"]) if pd.notna(row["open_interest"]) else 0.0
            rows.append({"strike": float(c["strike_price"]),
                         "cp": str(c["option_type"]).lower(),
                         "price": price, "oi": oi})
        result["by_expiry"][dd] = pd.DataFrame(rows)
    # cache (best-effort; immutable per date)
    try:
        os.makedirs(_CACHE, exist_ok=True)
        key = symbol.replace(".", "_") + "_" + str(date.date())
        frames = []
        for dd, df in result["by_expiry"].items():
            t = df.copy()
            t["days"] = dd
            frames.append(t)
        if frames:
            pd.concat(frames).to_parquet(os.path.join(_CACHE, key + ".parquet"))
    except Exception:
        pass
    return result
