"""Single source of truth for the CN option VIX roster & groups."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# RQ connection. Credentials must never be stored in source code.
# Export either RQDATA_URI (recommended) or RQDATAC_URI before running.
RQDATAC_URI = os.environ.get("RQDATA_URI") or os.environ.get("RQDATAC_URI")


def require_rqdata_uri():
    """Return the configured RQData URI or raise a clear configuration error."""
    uri = os.environ.get("RQDATA_URI") or os.environ.get("RQDATAC_URI") or RQDATAC_URI
    if not uri:
        raise RuntimeError(
            "RQData URI is not configured. Run: export RQDATA_URI='tcp://...'"
        )
    return uri

# --- The 12 financial-option instruments (option product code, exchange, underlying, group) ---
# underlying keys: SH50 上证50, HS300 沪深300, ZZ500 中证500, ZZ1000 中证1000,
#                  KC50 科创50, CYB 创业板, SZ100 深证100
ROSTER = [
    # CFFEX stock-index options -> Index VIX
    {"symbol": "IO", "kind": "index", "exchange": "CFFEX", "underlying": "HS300",  "group": "index_vix"},
    {"symbol": "HO", "kind": "index", "exchange": "CFFEX", "underlying": "SH50",   "group": "index_vix"},
    {"symbol": "MO", "kind": "index", "exchange": "CFFEX", "underlying": "ZZ1000", "group": "index_vix"},
    # SSE / SZSE ETF options -> the 4 similarity groups
    {"symbol": "510050.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "SH50",  "group": "blue_chip"},
    {"symbol": "510300.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "HS300", "group": "blue_chip"},
    {"symbol": "159919.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "HS300", "group": "blue_chip"},
    {"symbol": "159901.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "SZ100", "group": "sz_growth"},
    {"symbol": "159915.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "CYB",   "group": "sz_growth"},
    {"symbol": "510500.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "ZZ500", "group": "mid_small"},
    {"symbol": "159922.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "ZZ500", "group": "mid_small"},
    {"symbol": "588000.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "KC50",  "group": "hard_tech"},
    {"symbol": "588080.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "KC50",  "group": "hard_tech"},
]

GROUPS = {
    "index_vix": {"name_cn": "指数VIX",   "name_en": "Index VIX",            "underlyings": ["HS300", "SH50", "ZZ1000"]},
    "blue_chip": {"name_cn": "大盘蓝筹",   "name_en": "Large-cap Blue-chip",  "underlyings": ["SH50", "HS300"]},
    "sz_growth": {"name_cn": "深市成长",   "name_en": "Shenzhen Growth",      "underlyings": ["SZ100", "CYB"]},
    "mid_small": {"name_cn": "中小盘",     "name_en": "Mid-Small Cap",        "underlyings": ["ZZ500"]},
    "hard_tech": {"name_cn": "硬科技",     "name_en": "Hard-tech / STAR",     "underlyings": ["KC50"]},
}

VIX_PARAMS = {
    "target_days": 30,       # constant-maturity target
    "min_near_days": 7,      # roll the near term when < this many calendar days to expiry
    "annual_days": 365,      # actual/365 convention
    "weight_mode": "oi",     # composite weighting: open interest
    "atm_flag_threshold": 0.05,  # |model-free VIX - ATM IV| above this -> data-quality flag
}

# Official iVIX ground truth in RQ (see design §9): 70 trading days only.
IVIX_CODE = "000188.XSHG"
IVIX_WINDOW = ("2017-09-12", "2017-12-25")


# Half-hour monitoring uses completed 30-minute bars. Chinese financial options
# trade from 09:31-11:30 and 13:01-15:00, therefore there are eight completed
# half-hour observation points per full trading day.
INTRADAY_PARAMS = {
    "frequency": "30m",
    "sample_times": [
        "10:00", "10:30", "11:00", "11:30",
        "13:30", "14:00", "14:30", "15:00",
    ],
    "history_days": 5,
    "request_batch_size": 180,
    "max_retries": 3,
    "retry_sleep_seconds": 4.0,
}


def _five_minute_slots():
    """Completed five-minute bars for the Chinese financial-option sessions."""
    out = []
    for start_h, start_m, end_h, end_m in ((9, 35, 11, 30), (13, 5, 15, 0)):
        h, m = start_h, start_m
        while (h, m) <= (end_h, end_m):
            out.append(f"{h:02d}:{m:02d}")
            m += 5
            if m >= 60:
                h += 1
                m -= 60
    return out


LIVE_DASHBOARD_PARAMS = {
    "frequency": "5m",
    "sample_times": _five_minute_slots(),
    "halfday_times": ["11:30", "15:00"],
    "history_trading_days": 5,
    "halfday_history_start": "2026-01-01",
    "browser_poll_seconds": 20,
    "stale_after_minutes": 7,
    "request_batch_size": 180,
    "max_retries": 3,
    "retry_sleep_seconds": 4.0,
}
