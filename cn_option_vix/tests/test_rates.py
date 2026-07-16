from cn_option_vix.data.rates import risk_free_rate


def test_rate_is_reasonable():
    r = risk_free_rate("2024-06-03", tenor_days=30)
    assert 0.0 <= r <= 0.10
