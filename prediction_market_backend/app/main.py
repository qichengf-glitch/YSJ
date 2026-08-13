from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .database import init_db
from .prediction_market_service import (
    get_prediction_history,
    get_prediction_market_detail,
    get_prediction_markets,
    get_prediction_overview,
    sync_prediction_markets,
)
from .whale_service import (
    get_whale_daily_overview,
    get_whale_summary,
    sync_tracked_whales,
)

app = FastAPI(title="YSJ Prediction Market", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()


class SyncResponse(BaseModel):
    ok: bool
    result: dict


def sync_prediction_market_stack() -> None:
    try:
        sync_prediction_markets(
            min_prob=settings.prediction_sync_min_prob,
            min_volume=settings.prediction_sync_min_volume,
            max_pages=settings.prediction_sync_max_pages,
            fetch_history=True,
        )
        sync_tracked_whales()
    except Exception as exc:
        print(f"[prediction-market-sync] failed: {exc}")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    if settings.enable_scheduler and not scheduler.running:
        scheduler.add_job(
            sync_prediction_market_stack,
            "interval",
            minutes=max(10, settings.prediction_sync_interval_minutes),
            id="sync_prediction_markets_stack",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now() + timedelta(seconds=45),
        )
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "prediction-market", "time": datetime.utcnow().isoformat() + "Z"}


@app.post("/api/prediction-markets/sync", response_model=SyncResponse)
def api_prediction_markets_sync(
    min_prob: float = Query(0.10, ge=0, le=1),
    min_volume: float = Query(10000, ge=0),
    max_pages: int = Query(15, ge=1, le=50),
    fetch_history: bool = True,
) -> dict:
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
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/prediction-markets/overview")
def api_prediction_markets_overview() -> dict:
    return get_prediction_overview()


@app.get("/api/prediction-markets/markets")
def api_prediction_markets(
    bucket: str = Query("all", pattern="^(all|rates_usd|geo_commodities)$"),
    signal: Optional[str] = None,
    min_volume: float = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    return {
        "data": get_prediction_markets(
            bucket=bucket,
            signal=signal,
            min_volume=min_volume,
            limit=limit,
        )
    }


@app.post("/api/prediction-markets/sync-whales")
def api_prediction_markets_sync_whales(
    discover: bool = False,
    max_wallets: int = Query(0, ge=0, le=500),
) -> dict:
    try:
        return {"ok": True, "result": sync_tracked_whales(discover=discover, max_wallets=max_wallets)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/prediction-markets/whales/summary")
def api_prediction_markets_whale_summary() -> dict:
    return get_whale_summary()


@app.get("/api/prediction-markets/whales/daily")
def api_prediction_markets_whales_daily(
    bucket: str = Query("all", pattern="^(all|rates_usd|geo_commodities)$")
) -> dict:
    return get_whale_daily_overview(bucket=bucket)


@app.get("/api/prediction-markets/market/{condition_id}")
def api_prediction_market_detail(condition_id: str) -> dict:
    item = get_prediction_market_detail(condition_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prediction market not found. Sync Polymarket first.")
    return item


@app.get("/api/prediction-markets/history/{condition_id}")
def api_prediction_market_history(condition_id: str) -> dict:
    return {"data": get_prediction_history(condition_id)}
