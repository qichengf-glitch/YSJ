from datetime import date, datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .database import init_db
from .jin10_client import Jin10ClientError
from .price_service import get_intraday_price
from .prediction_market_service import (
    get_prediction_history,
    get_prediction_market_detail,
    get_prediction_markets,
    get_prediction_overview,
    sync_prediction_markets,
)
from .services import (
    aggregate_earnings,
    dashboard_summary,
    get_holidays,
    get_updates,
    sync_all_logs,
    sync_default_window,
    sync_full,
)

app = FastAPI(title="US Event Intelligence", version="4.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

scheduler = BackgroundScheduler()


class SyncRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    past_days: Optional[int] = None
    future_days: Optional[int] = None


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.on_event("startup")
def startup_event():
    init_db()
    if settings.enable_scheduler and not scheduler.running:
        scheduler.add_job(sync_all_logs, "interval", minutes=max(1, settings.log_poll_interval_minutes), id="sync_logs", replace_existing=True)
        scheduler.add_job(sync_default_window, "interval", minutes=max(30, settings.full_sync_interval_minutes), id="sync_full", replace_existing=True)
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/")
def index():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}



@app.post("/api/sync/full")
def api_sync_full(req: SyncRequest):
    try:
        if req.start and req.end:
            start = parse_date(req.start)
            end = parse_date(req.end)
        else:
            past = req.past_days if req.past_days is not None else settings.sync_past_days
            future = req.future_days if req.future_days is not None else settings.sync_future_days
            today = date.today()
            start = today - timedelta(days=past)
            end = today + timedelta(days=future)
        return {"ok": True, "start": start.isoformat(), "end": end.isoformat(), "counts": sync_full(start, end)}
    except Jin10ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sync/default")
def api_sync_default():
    try:
        return {"ok": True, **sync_default_window()}
    except Jin10ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sync/logs")
def api_sync_logs():
    try:
        return {"ok": True, "result": sync_all_logs()}
    except Jin10ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/dashboard")
def api_dashboard(days: int = Query(7, ge=1, le=60)):
    return dashboard_summary(days=days)


@app.get("/api/earnings")
def api_earnings(start: Optional[str] = None, end: Optional[str] = None):
    return {"data": aggregate_earnings(start=start, end=end)}


@app.get("/api/updates")
def api_updates(limit: int = Query(80, ge=1, le=500), source_type: Optional[str] = None):
    return {"data": get_updates(limit=limit, source_type=source_type)}



@app.get("/api/price/intraday")
def api_price_intraday(
    ticker: str,
    range_key: str = Query("1d", pattern="^(1d|5d|1mo)$"),
    interval: str = Query("5m", pattern="^(1m|2m|5m|15m|30m|60m)$"),
    force: bool = False,
):
    try:
        return get_intraday_price(ticker=ticker, range_key=range_key, interval=interval, force=force)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/holidays")
def api_holidays(start: Optional[str] = None, end: Optional[str] = None, limit: int = Query(100, ge=1, le=500)):
    return {"data": get_holidays(start=start, end=end, limit=limit)}

@app.post("/api/prediction-markets/sync")
def api_prediction_markets_sync(
    min_prob: float = Query(0.10, ge=0, le=1),
    min_volume: float = Query(10000, ge=0),
    max_pages: int = Query(15, ge=1, le=50),
    fetch_history: bool = True,
):
    try:
        return {
            "ok": True,
            "result": sync_prediction_markets(
                min_prob=min_prob,
                min_volume=min_volume,
                max_pages=max_pages,
                fetch_history=fetch_history,
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/prediction-markets/overview")
def api_prediction_markets_overview():
    return get_prediction_overview()


@app.get("/api/prediction-markets/markets")
def api_prediction_markets(
    bucket: str = Query("all", pattern="^(all|rates_usd|geo_commodities|growth_risk)$"),
    signal: Optional[str] = None,
    min_volume: float = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    return {"data": get_prediction_markets(bucket=bucket, signal=signal, min_volume=min_volume, limit=limit)}


@app.get("/api/prediction-markets/market/{condition_id}")
def api_prediction_market_detail(condition_id: str):
    item = get_prediction_market_detail(condition_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prediction market not found. Sync Polymarket first.")
    return item


@app.get("/api/prediction-markets/history/{condition_id}")
def api_prediction_market_history(condition_id: str):
    return {"data": get_prediction_history(condition_id)}
