"""Single-day VIX snapshot: 6 published series + per-instrument diagnostics."""
from cn_option_vix.config import ROSTER, GROUPS
from cn_option_vix.core.instrument_vix import instrument_vix
from cn_option_vix.aggregate.composite import aggregate_variances


def assemble_vix_row(label, per_inst):
    """Aggregate already-computed instruments using the original OI-weighted path.

    ``label`` is stored in the legacy ``date`` field. The half-hour pipeline
    renames it to ``timestamp`` after calling this function.
    """
    ivs = {}
    for d in per_inst:
        ivs["iv_" + d["symbol"]] = d["vix"] if d.get("ok") else None

    agg = aggregate_variances(per_inst)
    row = {"date": label}
    row["overall"] = agg["overall"].get("vix") if agg["overall"] else None
    for gid in GROUPS:
        row[gid] = agg["groups"].get(gid, {}).get("vix")
    row.update(ivs)

    def _sp(a, b):
        va, vb = row.get(a), row.get(b)
        return (va - vb) if (va is not None and vb is not None) else None

    # Dashboard spreads: each published group versus the common Overall benchmark.
    # These are presentation fields only; all six VIX values still come from the
    # unchanged OI-weighted variance aggregation above.
    for gid in GROUPS:
        row[f"spread_{gid}_overall"] = _sp(gid, "overall")

    # Legacy pairwise spreads kept for backward compatibility.
    row["spread_index_bluechip"] = _sp("index_vix", "blue_chip")
    row["spread_bluechip_szgrowth"] = _sp("blue_chip", "sz_growth")
    row["n_instruments"] = sum(1 for d in per_inst if d.get("ok"))
    row["dq_flags"] = sum(1 for d in per_inst if not d.get("ok"))
    return row


def compute_day(date):
    """Return a flat dict row for one daily observation."""
    per_inst = []
    for r in ROSTER:
        res = instrument_vix(r["symbol"], date)
        if res is None:
            continue
        res = dict(res)
        res["group"] = r["group"]
        per_inst.append(res)
    return assemble_vix_row(date, per_inst)
