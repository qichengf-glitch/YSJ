"""FastAPI application for the dual-time-scale VIX monitoring terminal."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cn_option_vix.config import GROUPS, LIVE_DASHBOARD_PARAMS, ROSTER
from cn_option_vix.web.storage import (
    DEFAULT_DB_PATH,
    VIX_COLUMNS,
    database_summary,
    latest_collector_event,
    latest_by_resolution,
    moving_average_snapshot,
    previous_by_resolution,
    query_series,
)

TZ = ZoneInfo("Asia/Shanghai")
STATIC_DIR = Path(__file__).resolve().parent / "static"
DB_PATH = Path(os.environ.get("CN_VIX_DB", str(DEFAULT_DB_PATH)))

COLORS = {
    "overall": "#263248",
    "index_vix": "#6957D5",
    "blue_chip": "#2878D0",
    "sz_growth": "#16A39A",
    "mid_small": "#E39A32",
    "hard_tech": "#D85087",
}
LABELS = {
    "overall": "Overall",
    "index_vix": "Index VIX",
    "blue_chip": "Blue Chip",
    "sz_growth": "SZ Growth",
    "mid_small": "Mid-Small",
    "hard_tech": "Hard Tech",
}

BUILD_ID = "20260723-auto-catchup-v5"

app = FastAPI(title="China Option Volatility Monitor", version="1.3.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _jsonable(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if value is None:
            out[key] = None
        elif isinstance(value, float) and pd.isna(value):
            out[key] = None
        else:
            out[key] = value
    return out


def _in_session(now: datetime) -> bool:
    hm = now.hour * 60 + now.minute
    return (9 * 60 + 31 <= hm <= 11 * 60 + 30) or (
        13 * 60 + 1 <= hm <= 15 * 60
    )


def _next_time(now: datetime, sample_times: list[str]) -> datetime:
    # The web process deliberately does not call RQData. Skip weekends locally;
    # the collector remains the source of truth for exchange holidays.
    for day_offset in range(0, 8):
        day = now.date() + timedelta(days=day_offset)
        if day.weekday() >= 5:
            continue
        for hhmm in sample_times:
            hh, mm = map(int, hhmm.split(":"))
            candidate = datetime(day.year, day.month, day.day, hh, mm, tzinfo=TZ)
            if candidate > now:
                return candidate
    raise AssertionError("unreachable")


def _status_payload() -> dict:
    now = datetime.now(TZ)
    latest_5m = latest_by_resolution("5m", DB_PATH, published_only=True)
    latest_raw = latest_by_resolution("5m", DB_PATH, published_only=False)
    latest_half = latest_by_resolution("halfday", DB_PATH, published_only=True)
    last_ts = (
        pd.Timestamp(latest_5m["timestamp"]).to_pydatetime().replace(tzinfo=TZ)
        if latest_5m
        else None
    )
    age_minutes = (
        max(0.0, (now - last_ts).total_seconds() / 60.0) if last_ts else None
    )
    today_has_data = bool(last_ts and last_ts.date() == now.date())
    weekday = now.weekday() < 5
    in_session = _in_session(now) and weekday
    hm = now.hour * 60 + now.minute
    stale_for_today = bool(
        last_ts
        and last_ts.date() < now.date()
        and weekday
        and hm >= 9 * 60 + 35
    )
    last_event = latest_collector_event(DB_PATH)
    raw_is_partial = bool(
        latest_raw
        and latest_raw.get("expected_instruments") is not None
        and latest_raw.get("n_instruments") != latest_raw.get("expected_instruments")
        and (latest_5m is None or latest_raw["timestamp"] >= latest_5m["timestamp"])
    )
    has_recent_error = bool(
        last_event
        and last_event.get("level") in {"ERROR", "WARNING"}
        and (
            latest_5m is None
            or str(last_event["event_time"]) >= str(latest_5m["timestamp"])
        )
    )
    if in_session and today_has_data and age_minutes is not None:
        state = (
            "LIVE"
            if age_minutes <= float(LIVE_DASHBOARD_PARAMS["stale_after_minutes"])
            and not raw_is_partial
            else "DELAYED"
        )
    elif in_session and (has_recent_error or raw_is_partial):
        state = "DELAYED"
    elif stale_for_today:
        state = "STALE"
    elif in_session:
        state = "WAITING"
    else:
        state = "CLOSED"

    next_5m = _next_time(now, LIVE_DASHBOARD_PARAMS["sample_times"])
    next_half = _next_time(now, LIVE_DASHBOARD_PARAMS["halfday_times"])
    diagnostic = latest_raw or latest_5m
    valid = diagnostic.get("n_instruments") if diagnostic else None
    expected = diagnostic.get("expected_instruments") if diagnostic else len(ROSTER)
    if stale_for_today:
        quality = "STALE"
    else:
        quality = "OK" if valid == expected and valid is not None else "PARTIAL"
    return {
        "build_id": BUILD_ID,
        "now": now.isoformat(),
        "state": state,
        "market_session": "OPEN" if in_session else "CLOSED",
        "last_5m": latest_5m["timestamp"] if latest_5m else None,
        "last_raw_5m": latest_raw["timestamp"] if latest_raw else None,
        "last_halfday": latest_half["timestamp"] if latest_half else None,
        "next_5m": next_5m.isoformat(),
        "next_halfday": next_half.isoformat(),
        "age_minutes": age_minutes,
        "quality": quality,
        "valid_instruments": valid,
        "expected_instruments": expected,
        "valid_contracts": diagnostic.get("valid_contracts") if diagnostic else None,
        "missing_quotes": diagnostic.get("missing_quotes") if diagnostic else None,
        "provider_timestamp": diagnostic.get("provider_timestamp") if diagnostic else None,
        "calculated_at": diagnostic.get("calculated_at") if diagnostic else None,
        "last_collector_event": last_event,
    }


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
def config():
    return {
        "build_id": BUILD_ID,
        "series": [
            {"key": key, "label": LABELS[key], "color": COLORS[key]}
            for key in VIX_COLUMNS
        ],
        "spreads": [
            {
                "key": f"spread_{gid}_overall",
                "group": gid,
                "label": f"{LABELS[gid]} − Overall",
                "color": COLORS[gid],
            }
            for gid in GROUPS
        ],
        "poll_seconds": LIVE_DASHBOARD_PARAMS["browser_poll_seconds"],
        "halfday_history_start": LIVE_DASHBOARD_PARAMS["halfday_history_start"],
    }


@app.get("/api/series")
def series(
    resolution: str = Query(pattern="^(5m|halfday)$"),
):
    rows = query_series(
        resolution,
        db_path=DB_PATH,
        trading_days=LIVE_DASHBOARD_PARAMS["history_trading_days"],
        start_date=(
            LIVE_DASHBOARD_PARAMS["halfday_history_start"]
            if resolution == "halfday"
            else None
        ),
    )
    return {
        "resolution": resolution,
        "count": len(rows),
        "points": [_jsonable(row) for row in rows],
    }


@app.get("/api/averages")
def averages():
    payload = moving_average_snapshot(db_path=DB_PATH, windows=(30, 60))
    for row in payload["rows"]:
        row["label"] = LABELS[row["key"]]
        row["color"] = COLORS[row["key"]]
    return _jsonable(payload)


@app.get("/api/latest")
def latest():
    current = latest_by_resolution("5m", DB_PATH)
    previous = previous_by_resolution("5m", DB_PATH)
    halfday = latest_by_resolution("halfday", DB_PATH)
    if current is None:
        return {"timestamp": None, "cards": [], "halfday_timestamp": None}
    cards = []
    for key in VIX_COLUMNS:
        value = current.get(key)
        prev = previous.get(key) if previous else None
        change = value - prev if value is not None and prev is not None else None
        spread = None if key == "overall" else current.get(f"spread_{key}_overall")
        cards.append(
            {
                "key": key,
                "label": LABELS[key],
                "color": COLORS[key],
                "value": value,
                "change": change,
                "spread": spread,
            }
        )
    return {
        "timestamp": current["timestamp"],
        "halfday_timestamp": halfday["timestamp"] if halfday else None,
        "cards": cards,
    }


@app.get("/api/status")
def status():
    try:
        return _status_payload()
    except Exception as exc:
        now = datetime.now(TZ)
        return {
            "now": now.isoformat(),
            "state": "ERROR",
            "market_session": "UNKNOWN",
            "last_5m": None,
            "last_halfday": None,
            "next_5m": None,
            "next_halfday": None,
            "age_minutes": None,
            "quality": "ERROR",
            "valid_instruments": None,
            "expected_instruments": len(ROSTER),
            "valid_contracts": None,
            "missing_quotes": None,
            "provider_timestamp": None,
            "calculated_at": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


@app.get("/api/quality")
def quality():
    status = _status_payload()
    return {
        "timestamp": status["last_raw_5m"],
        "published_timestamp": status["last_5m"],
        "quality": status["quality"],
        "valid_instruments": status["valid_instruments"],
        "expected_instruments": status["expected_instruments"],
        "valid_contracts": status["valid_contracts"],
        "missing_quotes": status["missing_quotes"],
        "provider_timestamp": status["provider_timestamp"],
        "calculated_at": status["calculated_at"],
        "last_collector_event": status["last_collector_event"],
        "database": database_summary(DB_PATH),
    }


@app.get("/healthz")
def healthz():
    try:
        summary = database_summary(DB_PATH)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "database": summary}
