from cn_option_vix.config import ROSTER, GROUPS, VIX_PARAMS

def test_roster_has_12_instruments():
    assert len(ROSTER) == 12

def test_group_membership_counts():
    assert GROUPS["index_vix"]["underlyings"] == ["HS300", "SH50", "ZZ1000"]
    assert set(GROUPS["blue_chip"]["underlyings"]) == {"SH50", "HS300"}
    assert set(GROUPS["sz_growth"]["underlyings"]) == {"SZ100", "CYB"}
    assert GROUPS["mid_small"]["underlyings"] == ["ZZ500"]
    assert GROUPS["hard_tech"]["underlyings"] == ["KC50"]

def test_every_instrument_maps_to_a_group():
    for r in ROSTER:
        assert r["group"] in GROUPS

def test_vix_params_defaults():
    assert VIX_PARAMS["target_days"] == 30
    assert VIX_PARAMS["min_near_days"] == 7
    assert VIX_PARAMS["weight_mode"] == "oi"
