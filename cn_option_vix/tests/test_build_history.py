import os
from cn_option_vix.pipeline.build_history import build_history

def test_build_history_small_range(tmp_path, rq_online):
    out = tmp_path / "vix.parquet"
    df = build_history("2024-06-03", "2024-06-07", out_path=str(out))
    assert os.path.exists(out)
    assert len(df) >= 3
    assert df["overall"].notna().all()
    assert df.index.is_monotonic_increasing
