from cn_option_vix.aggregate.composite import aggregate_variances

def test_oi_weighted_variance_aggregation():
    per_inst = [
        {"symbol":"A","group":"blue_chip","var30":0.04,"oi":300,"ok":True},
        {"symbol":"B","group":"blue_chip","var30":0.09,"oi":100,"ok":True},
    ]
    out = aggregate_variances(per_inst)
    exp_var = (0.04*300 + 0.09*100) / 400
    assert abs(out["groups"]["blue_chip"]["var"] - exp_var) < 1e-12
    assert abs(out["groups"]["blue_chip"]["vix"] - 100*exp_var**0.5) < 1e-9
    assert abs(out["overall"]["var"] - exp_var) < 1e-12

def test_dead_instruments_excluded_and_weights_renormalize():
    per_inst = [
        {"symbol":"A","group":"mid_small","var30":0.04,"oi":300,"ok":True},
        {"symbol":"B","group":"mid_small","var30":0.09,"oi":0,"ok":True},
        {"symbol":"C","group":"mid_small","var30":0.16,"oi":100,"ok":False},
    ]
    out = aggregate_variances(per_inst)
    assert abs(out["groups"]["mid_small"]["var"] - 0.04) < 1e-12
