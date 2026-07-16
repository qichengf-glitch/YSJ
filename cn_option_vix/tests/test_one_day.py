from cn_option_vix.pipeline.one_day import compute_day

def test_compute_day_row():
    row = compute_day("2024-06-03")
    for col in ["overall","index_vix","blue_chip","sz_growth","mid_small","hard_tech"]:
        assert col in row and row[col] > 0
    assert row["n_instruments"] >= 6
