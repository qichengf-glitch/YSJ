"""Smoke test: RiceQuant connects and returns the option universe."""
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cn_option_vix.config import require_rqdata_uri  # project license (not the exhausted primary)
import rqdatac as rq


def test_rq_connects_and_lists_options(rq_online):
    rq.init(uri=require_rqdata_uri())
    df = rq.all_instruments(type="Option")
    assert len(df) > 100000  # RQ carries ~220k option instruments all-time
