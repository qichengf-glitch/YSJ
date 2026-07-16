"""Near/next selection + constant-30-day interpolation (CBOE final step)."""
import math
import warnings

def select_near_next(days_list, min_near_days: int):
    """days_list: sorted calendar-days-to-expiry. Near = first expiry with
    >= min_near_days; Next = the following expiry."""
    eligible = [d for d in sorted(days_list) if d >= min_near_days]
    if len(eligible) < 2:
        raise ValueError(f"need >=2 expiries with >= {min_near_days} days, got {eligible}")
    return eligible[0], eligible[1]

def interpolate_to_target(t1_days, var1, t2_days, var2, target_days=30, annual_days=365):
    """CBOE 30-day interpolation of total variance, annualized. Returns VIX (%).

    All day counts must be CALENDAR days under the same convention. If the target
    is not bracketed by [t1_days, t2_days], falls back to true FLAT extrapolation:
    the annualized vol of the nearer term is held constant (with a warning), rather
    than producing wrong-signed weights or reannualizing the near variance to 30d.
    Returns float('nan') if the (interpolated) variance is negative (bad chain).
    """
    N1, N2, NT = t1_days, t2_days, target_days
    if N1 == N2:
        raise ValueError(f"near and next terms share a day count: {N1}")
    if N1 > N2:
        N1, N2, var1, var2 = N2, N1, var2, var1  # normalize order

    def _annualized_vix(var):
        # var is already an annualized variance rate; hold it flat.
        if var < 0:
            warnings.warn(f"negative variance {var:.6g}; returning nan")
            return float("nan")
        return 100.0 * math.sqrt(var)

    if NT <= N1:
        warnings.warn(f"target {NT}d <= near {N1}d; flat-extrapolating near term")
        return _annualized_vix(var1)
    if NT >= N2:
        warnings.warn(f"target {NT}d >= next {N2}d; flat-extrapolating next term")
        return _annualized_vix(var2)

    # Bracketed: standard CBOE linear interpolation of TOTAL variance, reannualized to 30d.
    T1, T2 = N1 / annual_days, N2 / annual_days
    w1 = (N2 - NT) / (N2 - N1)
    w2 = (NT - N1) / (N2 - N1)
    interp = (T1 * var1 * w1 + T2 * var2 * w2) * (annual_days / NT)
    if interp < 0:
        warnings.warn(f"negative interpolated variance {interp:.6g}; returning nan")
        return float("nan")
    return 100.0 * math.sqrt(interp)
