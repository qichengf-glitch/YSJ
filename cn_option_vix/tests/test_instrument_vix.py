import math
from cn_option_vix.core.instrument_vix import instrument_vix


def test_instrument_vix_reasonable():
    res = instrument_vix("510300.XSHG", "2024-06-03")
    assert res is not None
    assert res["ok"] is True
    assert 5.0 < res["vix"] < 80.0
    assert res["oi"] > 0
    assert res["n_strikes_near"] >= 5
