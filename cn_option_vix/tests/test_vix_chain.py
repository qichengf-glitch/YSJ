import math
import pytest
from cn_option_vix.core.vix_chain import interpolate_to_target, select_near_next

def test_interpolation_between_equal_variances():
    # equal variances on both terms => VIX == sqrt(var)*100 regardless of days
    var = 0.25**2
    vix = interpolate_to_target(t1_days=23, var1=var, t2_days=37, var2=var, target_days=30)
    assert abs(vix - 25.0) < 1e-6

def test_select_near_next_rolls_when_too_close():
    # expiries 3, 31, 59 days; min_near_days=7 => near=31, next=59
    near, nxt = select_near_next([3, 31, 59], min_near_days=7)
    assert (near, nxt) == (31, 59)

def test_interpolation_equal_day_counts_raises():
    with pytest.raises(ValueError):
        interpolate_to_target(t1_days=30, var1=0.04, t2_days=30, var2=0.09, target_days=30)

def test_interpolation_flat_extrapolates_when_not_bracketed_low():
    # target 30d < near 33d: TRUE flat extrapolation holds the near-term annualized
    # vol constant => 100*sqrt(0.04) = 20.0 exactly (no N1/NT reannualization), with a warning.
    with pytest.warns(UserWarning):
        vix = interpolate_to_target(t1_days=33, var1=0.04, t2_days=60, var2=0.09,
                                    target_days=30)
    assert abs(vix - 20.0) < 1e-9

def test_interpolation_negative_variance_returns_nan():
    with pytest.warns(UserWarning):
        vix = interpolate_to_target(t1_days=23, var1=-1.0, t2_days=37, var2=-1.0,
                                    target_days=30)
    assert math.isnan(vix)
