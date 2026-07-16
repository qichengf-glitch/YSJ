from cn_option_vix.data.chains import get_chain_snapshot


def test_510300_chain_snapshot():
    snap = get_chain_snapshot("510300.XSHG", "2024-06-03")
    assert snap is not None
    assert len(snap["expiries"]) == 2
    near = snap["expiries"][0]
    df = snap["by_expiry"][near]
    assert set(df["cp"]) == {"c", "p"}
    assert (df["strike"] > 0).all()
    assert "price" in df.columns and "oi" in df.columns
    assert (df["price"] > 0).all()
