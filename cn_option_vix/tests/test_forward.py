import math
import pytest
from cn_option_vix.core.forward import compute_forward

def test_forward_and_k0_basic():
    # Symmetric chain: C==P at K=100 => forward ~ 100
    strikes = [90, 95, 100, 105, 110]
    calls = {90: 11.0, 95: 6.5, 100: 3.0, 105: 1.2, 110: 0.4}
    puts  = {90: 0.4, 95: 1.1, 100: 3.0, 105: 6.3, 110: 10.5}
    r, T = 0.02, 30/365
    F, K0, kstar = compute_forward(calls, puts, r, T)
    assert kstar == 100                 # smallest |C-P|
    assert abs(F - 100.0) < 0.5         # C-P==0 at 100 => F≈K*
    assert K0 == 100                    # first strike <= F

def test_k0_is_strike_below_forward():
    strikes = [90, 95, 100, 105, 110]
    calls = {90: 12.5, 95: 8.2, 100: 4.6, 105: 2.1, 110: 0.8}
    puts  = {90: 0.3, 95: 1.0, 100: 2.3, 105: 4.7, 110: 8.3}
    F, K0, kstar = compute_forward(calls, puts, 0.02, 30/365)
    assert K0 <= F
    assert not any(K0 < k <= F for k in strikes)   # no strike sits in the (K0, F] gap

def test_no_strike_at_or_below_forward_raises():
    # puts >> calls everywhere pushes the implied F below the lowest strike,
    # so there is no strike at or below F -> data-quality error, not a fallback.
    calls = {100: 0.1, 105: 0.05, 110: 0.03, 115: 0.02, 120: 0.01}
    puts  = {100: 30.0, 105: 35.0, 110: 40.0, 115: 45.0, 120: 50.0}
    with pytest.raises(ValueError):
        compute_forward(calls, puts, 0.02, 30/365)
