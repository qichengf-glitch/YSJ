from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .database import get_job_statuses, init_db, update_job_status, utc_now
from .jin10_client import Jin10ClientError
from .price_service import get_intraday_price
from .prediction_market_service import (
    get_prediction_history,
    get_prediction_market_detail,
    get_prediction_markets,
    get_prediction_overview,
    refresh_prediction_history,
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
from .time_utils import dashboard_now, dashboard_today
from .whale_service import get_whale_daily_overview, get_whale_summary, sync_tracked_whales

app = FastAPI(title="US Event Intelligence", version="6.6.1")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
scheduler = BackgroundScheduler(timezone=settings.dashboard_timezone)


@app.middleware("http")
async def disable_api_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/") or request.url.path in {"/", "/static/app.js"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _run_job(job: str, fn: Callable[[], Any]) -> Any:
    started_at = utc_now()
    update_job_status(job, "running", started_at=started_at, error=None)
    try:
        result = fn()
        update_job_status(job, "success", finished_at=utc_now(), error=None, details=result if isinstance(result, dict) else {"result": result})
        return result
    except Exception as exc:
        update_job_status(job, "failed", finished_at=utc_now(), error=str(exc))
        print(f"[{job}] failed: {exc}")
        return {"ok": False, "error": str(exc)}


def sync_jin10_logs_job():
    return _run_job("jin10_logs", sync_all_logs)


def sync_jin10_full_job():
    return _run_job("jin10_full", sync_default_window)


def sync_prediction_quotes_job():
    # Current prices/volumes commit quickly; history is a separate slower task.
    return _run_job(
        "prediction_quotes",
        lambda: sync_prediction_markets(
            min_prob=settings.prediction_sync_min_prob,
            min_volume=settings.prediction_sync_min_volume,
            max_pages=settings.prediction_sync_max_pages,
            fetch_history=False,
        ),
    )


def sync_prediction_history_job():
    return _run_job("prediction_history", refresh_prediction_history)


def sync_prediction_whales_job():
    return _run_job("prediction_whales", sync_tracked_whales)


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
        now = dashboard_now()
        scheduler.add_job(
            sync_jin10_logs_job, "interval", minutes=max(1, settings.log_poll_interval_minutes),
            id="sync_logs", replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=now + timedelta(seconds=2),
        )
        scheduler.add_job(
            sync_jin10_full_job, "interval", minutes=max(30, settings.full_sync_interval_minutes),
            id="sync_full", replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=now + timedelta(seconds=8),
        )
        scheduler.add_job(
            sync_prediction_quotes_job, "interval", minutes=max(1, settings.prediction_sync_interval_minutes),
            id="sync_prediction_quotes", replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=now,
        )
        scheduler.add_job(
            sync_prediction_history_job, "interval", minutes=max(5, settings.prediction_history_interval_minutes),
            id="sync_prediction_history", replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=now + timedelta(seconds=20),
        )
        scheduler.add_job(
            sync_prediction_whales_job, "interval", minutes=max(5, settings.prediction_whale_interval_minutes),
            id="sync_prediction_whales", replace_existing=True, max_instances=1, coalesce=True,
            next_run_time=now + timedelta(seconds=35),
        )
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/")
def index():
    return FileResponse("app/static/index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "version": app.version,
        "time": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scheduler_running": scheduler.running,
        "jobs": get_job_statuses(),
    }


@app.get("/api/data-status")
def data_status():
    prediction = get_prediction_overview()
    whales = get_whale_daily_overview(bucket="all")
    return {
        "version": app.version,
        "prediction": {
            "fetched_at": prediction.get("fetched_at"),
            "age_seconds": prediction.get("age_seconds"),
            "is_stale": prediction.get("is_stale"),
            "market_count": prediction.get("market_count"),
            "sync_status": prediction.get("sync_status"),
        },
        "whales": {
            "fetched_at": whales.get("fetched_at"),
            "age_seconds": whales.get("age_seconds"),
            "is_stale": whales.get("is_stale"),
            "sync_status": whales.get("sync_status"),
        },
        "jobs": get_job_statuses(),
    }


@app.post("/api/sync/full")
def api_sync_full(req: SyncRequest):
    try:
        if req.start and req.end:
            start = parse_date(req.start)
            end = parse_date(req.end)
        else:
            past = req.past_days if req.past_days is not None else settings.sync_past_days
            future = req.future_days if req.future_days is not None else settings.sync_future_days
            today = dashboard_today()
            start = today - timedelta(days=past)
            end = today + timedelta(days=future)
        counts = sync_full(start, end)
        return {"ok": True, "start": start.isoformat(), "end": end.isoformat(), "counts": counts}
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
    fetch_history: bool = False,
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


@app.post("/api/prediction-markets/sync-history")
def api_prediction_markets_sync_history():
    try:
        return {"ok": True, "result": refresh_prediction_history()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/prediction-markets/overview")
def api_prediction_markets_overview():
    return get_prediction_overview()


@app.get("/api/prediction-markets/markets")
def api_prediction_markets(
    bucket: str = Query("all", pattern="^(all|rates_usd|geo_commodities)$"),
    signal: Optional[str] = None,
    min_volume: float = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    return {"data": get_prediction_markets(bucket=bucket, signal=signal, min_volume=min_volume, limit=limit)}


@app.post("/api/prediction-markets/sync-whales")
def api_prediction_markets_sync_whales(discover: bool = False, max_wallets: int = Query(0, ge=0, le=500)):
    try:
        return {"ok": True, "result": sync_tracked_whales(discover=discover, max_wallets=max_wallets)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/prediction-markets/whales/summary")
def api_prediction_markets_whale_summary():
    return get_whale_summary()


@app.get("/api/prediction-markets/whales/daily")
def api_prediction_markets_whales_daily(bucket: str = Query("all", pattern="^(all|rates_usd|geo_commodities)$")):
    return get_whale_daily_overview(bucket=bucket)


@app.get("/api/prediction-markets/market/{condition_id}")
def api_prediction_market_detail(condition_id: str):
    item = get_prediction_market_detail(condition_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prediction market not found. Sync Polymarket first.")
    return item


@app.get("/api/prediction-markets/history/{condition_id}")
def api_prediction_market_history(condition_id: str):
    return {"data": get_prediction_history(condition_id)}
