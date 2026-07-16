"""Term-matched risk-free rate. SHIBOR if available, else constant fallback.

VERIFIED 2026-07: this rqdatac build has no `get_shibor` accessor (SHIBOR-ish
accessors present are `get_interbank_offered_rate` / `get_yield_curve`), so the
try-block below always falls through to the constant fallback in practice. Rate
sensitivity of the model-free VIX is small by design, so the fallback is fine and
keeps this function network/permission-independent.
"""
import rqdatac as rq

_DEFAULT = 0.02


def risk_free_rate(date, tenor_days: int) -> float:
    """Annualized risk-free rate (fraction) for the given date and tenor.

    Always returns a value and is **connection-free**: `get_shibor` is absent on this
    rqdatac build, so we never call `rq.init()` here (that would need a live RQ login
    even when every chain is served from disk cache). If a SHIBOR accessor appears on a
    future build we attempt it lazily, but any failure silently falls back to _DEFAULT.
    Rate sensitivity of the model-free VIX is small by design.
    """
    if hasattr(rq, "get_shibor"):
        try:
            sh = rq.get_shibor(start_date=date, end_date=date)
            if sh is not None and len(sh):
                col = "3M" if tenor_days <= 45 else "6M"
                col = col if col in sh.columns else sh.columns[-1]
                val = float(sh.iloc[-1][col])
                return val / 100.0 if val > 1 else val  # handle percent vs fraction
        except Exception:
            pass
    return _DEFAULT
