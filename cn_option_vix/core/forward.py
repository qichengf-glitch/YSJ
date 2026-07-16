"""Forward level and K0 from put-call parity (CBOE VIX step 1)."""
import math

def compute_forward(calls: dict, puts: dict, r: float, T: float):
    """calls/puts: {strike: price}. Returns (F, K0, kstar).

    F   = forward index level implied by put-call parity at the strike with
          the smallest |C-P|.
    K0  = first strike at or below F.
    """
    strikes = sorted(set(calls) & set(puts))
    if not strikes:
        raise ValueError("no common call/put strikes")
    kstar = min(strikes, key=lambda k: abs(calls[k] - puts[k]))
    F = kstar + math.exp(r * T) * (calls[kstar] - puts[kstar])
    below = [k for k in strikes if k <= F]
    if not below:
        raise ValueError(f"no strike at or below forward F={F}")
    K0 = max(below)
    return F, K0, kstar
