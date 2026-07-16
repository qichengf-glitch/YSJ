"""Single-expiry model-free variance (CBOE VIX steps 2-3)."""
import math

def build_otm_series(calls: dict, puts: dict, K0: float):
    """Return sorted [(K, Q)] using OTM options: puts below K0, calls above,
    and the average of call & put at K0. Drops non-positive prices, and trims
    each tail after two consecutive dropped strikes (CBOE tail rule)."""
    strikes = sorted(set(calls) & set(puts))
    if K0 not in set(strikes):
        raise ValueError(f"K0={K0} not in the common call/put strikes")
    out = {}
    for K in strikes:
        if K < K0:
            q = puts[K]
        elif K > K0:
            q = calls[K]
        else:
            q = 0.5 * (calls[K] + puts[K])
        out[K] = q

    def trim(seq):
        kept, zeros = [], 0
        for K in seq:
            if out[K] <= 0:
                zeros += 1
                if zeros >= 2:
                    break
                continue
            zeros = 0
            kept.append(K)
        return kept

    below = trim([k for k in strikes if k < K0][::-1])   # walk down from K0
    above = trim([k for k in strikes if k > K0])          # walk up from K0
    kept = sorted(set(below) | set(above) | {K0})
    return [(K, out[K]) for K in kept]

def single_expiry_variance(otm, F: float, K0: float, r: float, T: float) -> float:
    """otm: sorted [(K, Q)]. Returns σ² for this expiry."""
    if T <= 0:
        raise ValueError("T must be positive")
    ks = [K for K, _ in otm]
    q  = {K: Q for K, Q in otm}
    n = len(ks)
    total = 0.0
    for i, K in enumerate(ks):
        if i == 0:
            dK = ks[1] - ks[0]
        elif i == n - 1:
            dK = ks[-1] - ks[-2]
        else:
            dK = (ks[i+1] - ks[i-1]) / 2.0
        total += (dK / (K * K)) * math.exp(r * T) * q[K]
    return (2.0 / T) * total - (1.0 / T) * (F / K0 - 1.0) ** 2
