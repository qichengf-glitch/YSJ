"""Per-instrument 30-day model-free VIX.

The numerical path lives in :func:`instrument_vix_from_snapshot`. Both the
original daily pipeline and the new half-hour pipeline call this same function,
so the VIX formula, expiry interpolation and OI aggregation inputs cannot drift.
"""
import pandas as pd
from cn_option_vix.config import VIX_PARAMS
from cn_option_vix.data.chains import get_chain_snapshot
from cn_option_vix.data.rates import risk_free_rate
from cn_option_vix.core.forward import compute_forward
from cn_option_vix.core.variance import build_otm_series, single_expiry_variance
from cn_option_vix.core.vix_chain import interpolate_to_target


def _expiry_variance(df, r, T):
    calls = {r_.strike: r_.price for r_ in df.itertuples() if r_.cp == "c"}
    puts = {r_.strike: r_.price for r_ in df.itertuples() if r_.cp == "p"}
    common = sorted(set(calls) & set(puts))
    if len(common) < 3:
        return None, 0
    F, K0, _ = compute_forward(calls, puts, r, T)
    otm = build_otm_series(calls, puts, K0)
    return single_expiry_variance(otm, F, K0, r, T), len(otm)


def instrument_vix_from_snapshot(symbol, date, snap):
    """Compute one instrument from an already assembled option-chain snapshot.

    ``snap`` must have the same schema returned by ``get_chain_snapshot``:
    ``expiries`` and ``by_expiry[days]`` frames with ``strike/cp/price/oi``.
    This function is intentionally the single numerical implementation used by
    daily, historical 30-minute and live 30-minute data paths.
    """
    if snap is None or len(snap["expiries"]) < 2:
        return None
    ann = VIX_PARAMS["annual_days"]
    near_d, next_d = snap["expiries"]
    variances, nstr, total_oi = {}, {}, 0.0
    for dd in (near_d, next_d):
        df = snap["by_expiry"].get(dd)
        if df is None or df.empty:
            return None
        r = risk_free_rate(str(pd.Timestamp(date).date()), dd)
        try:
            var, ns = _expiry_variance(df, r, dd / ann)
        except Exception:
            return None
        if var is None:
            return None
        variances[dd], nstr[dd] = var, ns
        total_oi += float(df["oi"].sum())
    vix = interpolate_to_target(
        near_d,
        variances[near_d],
        next_d,
        variances[next_d],
        target_days=VIX_PARAMS["target_days"],
        annual_days=ann,
    )
    ok = (vix == vix) and vix > 0  # not nan
    return {
        "symbol": symbol,
        "date": date,
        "vix": vix,
        "var30": (vix / 100.0) ** 2 if ok else float("nan"),
        "oi": total_oi,
        "near_days": near_d,
        "next_days": next_d,
        "n_strikes_near": nstr[near_d],
        "ok": bool(ok),
    }


def instrument_vix(symbol, date):
    # TODO: optional ATM-IV cross-check (rq.options.get_greeks iv is unreliable; diagnostic only)
    return instrument_vix_from_snapshot(symbol, date, get_chain_snapshot(symbol, date))
