from cn_option_vix.validate.ivix_compare import compare_to_ivix

def test_50etf_vix_matches_official_ivix(rq_online):
    res = compare_to_ivix()
    assert res["n"] >= 50
    assert res["corr"] >= 0.90
    assert res["rmse"] < 3.0
