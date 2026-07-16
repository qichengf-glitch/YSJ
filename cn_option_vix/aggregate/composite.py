"""OI-weighted aggregation of per-instrument variances into group & overall VIX."""
import math

def _weighted_var(members):
    """members: list of (var30, oi) with oi>0. Returns OI-weighted mean variance."""
    tot = sum(oi for _, oi in members)
    if tot <= 0:
        return None
    return sum(var * oi for var, oi in members) / tot

def aggregate_variances(per_inst):
    """per_inst: list of dicts with keys group, var30, oi, ok.
    Returns {groups: {gid: {var, vix, members, weight_sum}}, overall: {var, vix}}."""
    usable = [d for d in per_inst if d.get("ok") and d.get("oi", 0) > 0
              and d.get("var30") == d.get("var30")]  # var30 not nan
    groups = {}
    by_group = {}
    for d in usable:
        by_group.setdefault(d["group"], []).append((d["var30"], d["oi"]))
    for gid, members in by_group.items():
        var = _weighted_var(members)
        if var is None or var < 0:
            continue
        groups[gid] = {"var": var, "vix": 100.0 * math.sqrt(var),
                       "members": len(members), "weight_sum": sum(oi for _, oi in members)}
    all_members = [(d["var30"], d["oi"]) for d in usable]
    overall = {}
    ov = _weighted_var(all_members) if all_members else None
    if ov is not None and ov >= 0:
        overall = {"var": ov, "vix": 100.0 * math.sqrt(ov)}
    return {"groups": groups, "overall": overall}
