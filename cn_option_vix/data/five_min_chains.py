"""Strict five-minute option-chain acquisition for dashboard history.

This module changes only the observation frequency. Contract selection, strike
handling, expiry selection, keyed joins, and the VIX calculation path remain the
same as the validated 30-minute implementation.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import rqdatac as rq

from cn_option_vix.config import LIVE_DASHBOARD_PARAMS
from cn_option_vix.data.intraday_chains import (
    ChainAudit,
    _chunks,
    _normalise_price_frame,
    _plan_hash,
    _retry,
    _safe_symbol,
    ensure_rq,
)

_BASE = Path(__file__).resolve().parent / "cache_5m"
_BAR_DIR = _BASE / "bars"


def _bar_path(symbol: str, date: pd.Timestamp, plan: pd.DataFrame) -> Path:
    return _BAR_DIR / (
        f"{_safe_symbol(symbol)}_{date.date()}_5m_{_plan_hash(plan)}.parquet"
    )


def fetch_historical_5m_bars(
    symbol: str,
    date,
    plan: pd.DataFrame,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch native RQData five-minute close and open-interest bars."""
    ensure_rq()
    date = pd.Timestamp(date).normalize()
    path = _bar_path(symbol, date, plan)
    if path.exists() and not force:
        bars = pd.read_parquet(path)
        bars["datetime"] = pd.to_datetime(bars["datetime"], errors="raise")
        return bars

    ids = plan["order_book_id"].astype(str).tolist()
    frames = []
    for batch in _chunks(ids, int(LIVE_DASHBOARD_PARAMS["request_batch_size"])):
        raw = _retry(
            f"5m bars {symbol} {date.date()} ({len(batch)} contracts)",
            lambda batch=batch: rq.get_price(
                batch,
                start_date=date,
                end_date=date,
                frequency=LIVE_DASHBOARD_PARAMS["frequency"],
                fields=["close", "open_interest"],
                adjust_type="none",
                skip_suspended=True,
            ),
        )
        df = _normalise_price_frame(raw, batch)
        if not df.empty:
            frames.append(df[["order_book_id", "datetime", "close", "open_interest"]])

    if not frames:
        bars = pd.DataFrame(
            columns=["order_book_id", "datetime", "close", "open_interest"]
        )
    else:
        bars = pd.concat(frames, ignore_index=True)
        bars["close"] = pd.to_numeric(bars["close"], errors="coerce")
        bars["open_interest"] = pd.to_numeric(
            bars["open_interest"], errors="coerce"
        )
        bars = bars.sort_values(["order_book_id", "datetime"])
        bars = bars.drop_duplicates(["order_book_id", "datetime"], keep="last")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.parquet")
    bars.to_parquet(tmp, index=False)
    tmp.replace(path)
    return bars.reset_index(drop=True)


def expected_5m_timestamps(date) -> list[pd.Timestamp]:
    date = pd.Timestamp(date).normalize()
    return [
        pd.Timestamp(f"{date.date()} {hhmm}:00")
        for hhmm in LIVE_DASHBOARD_PARAMS["sample_times"]
    ]


def assemble_historical_5m_snapshot(
    symbol: str,
    date,
    timestamp,
    plan: pd.DataFrame,
    bars: pd.DataFrame,
) -> tuple[dict | None, ChainAudit, pd.DataFrame]:
    """Build one exact five-minute chain snapshot with explicit keyed joins."""
    date = pd.Timestamp(date).normalize()
    timestamp = pd.Timestamp(timestamp)
    raw_point = bars[bars["datetime"] == timestamp].copy()
    point = raw_point.merge(
        plan[["order_book_id", "days", "term", "cp", "strike", "maturity_date"]],
        on="order_book_id",
        how="inner",
        validate="one_to_one",
    )
    point["price"] = pd.to_numeric(point["close"], errors="coerce")
    point["oi"] = pd.to_numeric(point["open_interest"], errors="coerce").fillna(0.0)
    point = point[point["price"].gt(0)].copy()
    point["symbol"] = symbol
    point["timestamp"] = timestamp
    point["price_source"] = "5m_close"

    days = sorted(int(x) for x in plan["days"].unique())
    near_d = days[0] if len(days) >= 1 else None
    next_d = days[1] if len(days) >= 2 else None
    calls = int((point["cp"] == "c").sum()) if not point.empty else 0
    puts = int((point["cp"] == "p").sum()) if not point.empty else 0

    if len(days) < 2:
        status = "missing_expiry_plan"
        snap = None
    else:
        by_expiry = {
            dd: point[point["days"] == dd][["strike", "cp", "price", "oi"]]
            .sort_values(["strike", "cp"])
            .reset_index(drop=True)
            for dd in (near_d, next_d)
        }
        if any(frame.empty for frame in by_expiry.values()):
            status = "missing_bar_for_expiry"
            snap = None
        else:
            status = "chain_ready"
            snap = {
                "underlying": symbol,
                "date": date,
                "timestamp": timestamp,
                "expiries": [near_d, next_d],
                "by_expiry": by_expiry,
                "price_source": "5m_close",
            }

    audit = ChainAudit(
        symbol=symbol,
        timestamp=timestamp,
        near_days=near_d,
        next_days=next_d,
        expected_contracts=len(plan),
        bars_found=len(raw_point),
        valid_prices=len(point),
        calls=calls,
        puts=puts,
        status=status,
    )
    return snap, audit, point
