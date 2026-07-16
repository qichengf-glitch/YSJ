"""Ensure the workspace root is importable so `cn_option_vix.*` and
`container.*` resolve no matter how pytest is invoked."""
import sys, os
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_RQ_ONLINE = None


def _rq_online():
    """True if a live RQ connection can be established (checked once per session).
    Tests that need fresh RQ calls (calendar, official iVIX, universe) skip when False,
    e.g. under the trial-license login-machine cap or a traffic-quota block. Cached-data
    tests do NOT use this — they run connection-free."""
    global _RQ_ONLINE
    if _RQ_ONLINE is None:
        try:
            import rqdatac as rq
            from cn_option_vix.config import require_rqdata_uri
            rq.init(uri=require_rqdata_uri())
            rq.get_trading_dates("2024-06-03", "2024-06-04")
            _RQ_ONLINE = True
        except Exception:
            _RQ_ONLINE = False
    return _RQ_ONLINE


@pytest.fixture
def rq_online():
    if not _rq_online():
        pytest.skip("live RQ connection unavailable (login/traffic quota) — skipping")
