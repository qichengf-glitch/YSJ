import math
import pytest
from cn_option_vix.core.variance import build_otm_series, single_expiry_variance

def _black76(F, K, r, T, sigma, cp):
    from math import log, sqrt, exp
    from statistics import NormalDist
    N = NormalDist().cdf
    d1 = (log(F/K) + 0.5*sigma*sigma*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    if cp == "c":
        return exp(-r*T) * (F*N(d1) - K*N(d2))
    return exp(-r*T) * (K*N(-d2) - F*N(-d1))

def test_recovers_flat_vol_variance():
    F, r, T, sigma = 100.0, 0.02, 30/365, 0.25
    strikes = [F*(1+0.01*i) for i in range(-40, 41)]  # dense +/-40% grid, 1% steps
    calls = {round(K,4): _black76(F, K, r, T, sigma, "c") for K in strikes}
    puts  = {round(K,4): _black76(F, K, r, T, sigma, "p") for K in strikes}
    K0 = max(k for k in calls if k <= F)
    otm = build_otm_series(calls, puts, K0)
    var = single_expiry_variance(otm, F, K0, r, T)
    assert abs(math.sqrt(var) - sigma) < 0.01   # recover 25% within 1 vol pt

def test_single_expiry_variance_nonpositive_T_raises():
    with pytest.raises(ValueError):
        single_expiry_variance([(100, 3.0)], 100, 100, 0.02, 0)

def test_build_otm_series_k0_not_in_strikes_raises():
    calls = {90: 1.0, 100: 3.0, 110: 0.5}
    puts  = {90: 0.5, 100: 3.0, 110: 1.0}
    with pytest.raises(ValueError):
        build_otm_series(calls, puts, K0=95)   # 95 is not a common strike
