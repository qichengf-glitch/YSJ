"""Strict half-hour option-chain data acquisition and keyed assembly.

Data rules
----------
* Contract membership is queried for each symbol and trading date with
  ``rq.options.get_contracts``. No stale global universe is used.
* Near/next expiries are selected by the same ``select_near_next`` function as
  the daily implementation.
* Historical observations use native RQData 30-minute ``close`` and
  ``open_interest`` bars.
* ETF-option strike adjustments are read from that date's option daily data
  when available; the latest instrument strike is only a same-day fallback.
* Every merge is keyed by ``order_book_id`` and timestamp. There is no
  positional concatenation, forward fill or use of a future observation.
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence, TypeVar

import pandas as pd
import rqdatac as rq

from cn_option_vix.config import INTRADAY_PARAMS, VIX_PARAMS, require_rqdata_uri
from cn_option_vix.core.vix_chain import select_near_next

T = TypeVar("T")

_BASE = Path(__file__).resolve().parent / "cache_30m"
_PLAN_DIR = _BASE / "plans"
_BAR_DIR = _BASE / "bars"
_META_PATH = _BASE / "instrument_meta.parquet"
_INDEX_OPTION_ROOTS = {"IO", "HO", "MO"}
_inited = False
_meta_cache: pd.DataFrame | None = None


@dataclass(frozen=True)
class ChainAudit:
    symbol: str
    timestamp: pd.Timestamp
    near_days: int | None
    next_days: int | None
    expected_contracts: int
    bars_found: int
    valid_prices: int
    calls: int
    puts: int
    status: str

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "near_days": self.near_days,
            "next_days": self.next_days,
            "expected_contracts": self.expected_contracts,
            "bars_found": self.bars_found,
            "valid_prices": self.valid_prices,
            "calls": self.calls,
            "puts": self.puts,
            "status": self.status,
        }


def ensure_rq() -> None:
    global _inited
    if not _inited:
        rq.init(uri=require_rqdata_uri())
        _inited = True


def _is_quota_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return "quota" in text or "流量" in text or "bytes_limit" in text


def _retry(label: str, fn: Callable[[], T]) -> T:
    attempts = int(INTRADAY_PARAMS["max_retries"])
    sleep_seconds = float(INTRADAY_PARAMS["retry_sleep_seconds"])
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if _is_quota_error(exc) or attempt == attempts:
                raise RuntimeError(f"{label} failed: {exc}") from exc
            time.sleep(sleep_seconds * attempt)
    raise AssertionError("unreachable")


def _chunks(values: Sequence[str], size: int | None = None) -> Iterable[list[str]]:
    n = int(size or INTRADAY_PARAMS["request_batch_size"])
    for i in range(0, len(values), n):
        yield list(values[i : i + n])


def _safe_symbol(symbol: str) -> str:
    return symbol.replace(".", "_")


def _plan_path(symbol: str, date: pd.Timestamp) -> Path:
    return _PLAN_DIR / f"{_safe_symbol(symbol)}_{date.date()}_plan.parquet"


def _plan_hash(plan: pd.DataFrame) -> str:
    cols = ["order_book_id", "maturity_date", "days", "strike", "cp"]
    payload = plan[cols].sort_values(cols).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def _bar_path(symbol: str, date: pd.Timestamp, plan: pd.DataFrame) -> Path:
    return _BAR_DIR / (
        f"{_safe_symbol(symbol)}_{date.date()}_30m_{_plan_hash(plan)}.parquet"
    )


def _normalise_price_frame(raw, requested_ids: Sequence[str]) -> pd.DataFrame:
    """Normalise all RQData DataFrame index layouts to explicit key columns."""
    if raw is None:
        return pd.DataFrame()
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    elif not isinstance(raw, pd.DataFrame):
        raw = pd.DataFrame(raw)
    if raw.empty:
        return pd.DataFrame()

    df = raw.reset_index()
    # RQData uses `datetime` for minute bars and commonly `date`/`trading_date`
    # for daily bars. Keep whichever is present and normalise below.
    if "order_book_id" not in df.columns:
        if len(requested_ids) != 1:
            raise ValueError(
                "RQData response lacks order_book_id for a multi-contract request"
            )
        df["order_book_id"] = requested_ids[0]

    time_col = next(
        (c for c in ("datetime", "date", "trading_date") if c in df.columns),
        None,
    )
    if time_col is None:
        raise ValueError(f"RQData response has no time key: columns={list(df.columns)}")
    if time_col != "datetime":
        df = df.rename(columns={time_col: "datetime"})

    df["order_book_id"] = df["order_book_id"].astype(str)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df[df["datetime"].notna()].copy()
    return df


def _load_meta_cache() -> pd.DataFrame:
    """Load persistent option metadata keyed by order_book_id.

    Contract metadata is immutable for the fields used here. Persisting it
    avoids downloading the same instrument objects on every trading date.
    """
    global _meta_cache
    if _meta_cache is not None:
        return _meta_cache
    columns = [
        "order_book_id",
        "maturity_date",
        "option_type",
        "strike_static",
    ]
    if _META_PATH.exists():
        try:
            df = pd.read_parquet(_META_PATH)
            for col in columns:
                if col not in df.columns:
                    raise ValueError(f"metadata cache missing column {col}")
            df = df[columns].copy()
            df["order_book_id"] = df["order_book_id"].astype(str)
            df["maturity_date"] = pd.to_datetime(
                df["maturity_date"], errors="coerce"
            )
            df = df.drop_duplicates("order_book_id", keep="last")
            _meta_cache = df
            return _meta_cache
        except Exception:
            # Do not trust a malformed cache. It will be rebuilt from RQData.
            pass
    _meta_cache = pd.DataFrame(columns=columns)
    return _meta_cache


def _save_meta_cache(df: pd.DataFrame) -> None:
    _META_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _META_PATH.with_suffix(".tmp.parquet")
    df.sort_values("order_book_id").to_parquet(tmp, index=False)
    tmp.replace(_META_PATH)


def _download_instrument_rows(ids: Sequence[str]) -> pd.DataFrame:
    rows = []
    for batch in _chunks(list(ids)):
        objects = _retry(
            f"rq.instruments ({len(batch)} new contracts)",
            lambda batch=batch: rq.instruments(batch),
        )
        if objects is None:
            continue
        if not isinstance(objects, (list, tuple)):
            objects = [objects]
        for obj in objects:
            if obj is None:
                continue
            rows.append(
                {
                    "order_book_id": str(getattr(obj, "order_book_id")),
                    "maturity_date": pd.to_datetime(
                        getattr(obj, "maturity_date", None), errors="coerce"
                    ),
                    "option_type": str(getattr(obj, "option_type", "")).upper(),
                    "strike_static": pd.to_numeric(
                        getattr(obj, "strike_price", None), errors="coerce"
                    ),
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates("order_book_id", keep="last")
    return df


def _instrument_rows(ids: Sequence[str]) -> pd.DataFrame:
    """Return metadata for ids, downloading only contracts not cached yet."""
    global _meta_cache
    requested = list(dict.fromkeys(str(x) for x in ids))
    if not requested:
        return pd.DataFrame()

    cache = _load_meta_cache()
    known = set(cache["order_book_id"].astype(str))
    missing = [x for x in requested if x not in known]
    if missing:
        fresh = _download_instrument_rows(missing)
        if not fresh.empty:
            cache = fresh.copy() if cache.empty else pd.concat([cache, fresh], ignore_index=True)
            cache = cache.drop_duplicates("order_book_id", keep="last")
            _meta_cache = cache
            _save_meta_cache(cache)

    out = cache[cache["order_book_id"].isin(requested)].copy()
    # Preserve the requested-set semantics, but all downstream joins are keyed.
    return out.drop_duplicates("order_book_id", keep="last")


def _daily_strikes(ids: Sequence[str], date: pd.Timestamp) -> pd.DataFrame:
    """Get date-correct strikes; daily option bars carry adjusted strikes."""
    frames = []
    for batch in _chunks(list(ids)):
        raw = _retry(
            f"daily strike {date.date()} ({len(batch)} contracts)",
            lambda batch=batch: rq.get_price(
                batch,
                start_date=date,
                end_date=date,
                frequency="1d",
                fields=["strike_price"],
                adjust_type="none",
                skip_suspended=True,
            ),
        )
        df = _normalise_price_frame(raw, batch)
        if not df.empty:
            frames.append(df[["order_book_id", "datetime", "strike_price"]])
    if not frames:
        return pd.DataFrame(columns=["order_book_id", "strike_daily"])
    out = pd.concat(frames, ignore_index=True)
    out["strike_daily"] = pd.to_numeric(out["strike_price"], errors="coerce")
    out = out.sort_values("datetime").drop_duplicates("order_book_id", keep="last")
    return out[["order_book_id", "strike_daily"]]


def latest_trading_dates(n: int = 5, asof=None) -> list[pd.Timestamp]:
    """Return the latest ``n`` Chinese trading dates up to ``asof`` inclusive."""
    if n <= 0:
        raise ValueError("n must be positive")
    ensure_rq()
    end = pd.Timestamp(asof).normalize() if asof is not None else pd.Timestamp(
        _retry("get_latest_trading_date", lambda: rq.get_latest_trading_date())
    ).normalize()
    # 4 calendar weeks comfortably cover five trading days across holidays.
    start = end - pd.Timedelta(days=max(28, n * 5))
    dates = _retry(
        "get_trading_dates",
        lambda: rq.get_trading_dates(start_date=start, end_date=end),
    )
    out = [pd.Timestamp(d).normalize() for d in dates]
    if len(out) < n:
        raise RuntimeError(f"only {len(out)} trading dates available up to {end.date()}")
    return out[-n:]


def trading_dates_between(start, end) -> list[pd.Timestamp]:
    """Return all Chinese trading dates in an inclusive calendar range."""
    ensure_rq()
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end must be on or after start")
    dates = _retry(
        "get_trading_dates",
        lambda: rq.get_trading_dates(start_date=start_ts, end_date=end_ts),
    )
    return [pd.Timestamp(d).normalize() for d in dates]


def load_contract_plan(symbol: str, date, force: bool = False) -> pd.DataFrame:
    """Build the exact near/next contract roster for one symbol and date."""
    ensure_rq()
    date = pd.Timestamp(date).normalize()
    path = _plan_path(symbol, date)
    if path.exists() and not force:
        plan = pd.read_parquet(path)
        plan["maturity_date"] = pd.to_datetime(plan["maturity_date"])
        return plan

    ids = _retry(
        f"options.get_contracts {symbol} {date.date()}",
        lambda: rq.options.get_contracts(underlying=symbol, trading_date=date),
    )
    ids = sorted(set(str(x) for x in (ids or [])))
    if not ids:
        raise RuntimeError(f"no active option contracts for {symbol} on {date.date()}")

    meta = _instrument_rows(ids)
    if meta.empty:
        raise RuntimeError(f"no instrument metadata for {symbol} on {date.date()}")
    meta = meta[
        meta["maturity_date"].notna()
        & meta["option_type"].isin(["C", "P"])
    ].copy()
    meta["days"] = (meta["maturity_date"] - date).dt.days.astype(int)

    near_d, next_d = select_near_next(
        sorted(meta["days"].unique()), VIX_PARAMS["min_near_days"]
    )
    plan = meta[meta["days"].isin([near_d, next_d])].copy()
    plan["term"] = plan["days"].map({near_d: "near", next_d: "next"})
    plan["cp"] = plan["option_type"].str.lower()

    # For historical ETF options, the current instrument object can contain only
    # the latest adjusted strike. The option daily line is the authoritative
    # date-specific value. On an unfinished current day it may not exist yet, so
    # the current instrument strike is a valid same-day fallback.
    if symbol not in _INDEX_OPTION_ROOTS:
        # ETF option strikes can be adjusted after distributions. The date-specific
        # daily strike remains authoritative for historical reconstruction.
        daily = _daily_strikes(plan["order_book_id"].tolist(), date)
        plan = plan.merge(
            daily, on="order_book_id", how="left", validate="one_to_one"
        )
    else:
        # CFFEX index-option strikes are not adjusted; avoid a redundant API pull.
        plan["strike_daily"] = pd.NA
    plan["strike"] = plan["strike_daily"].where(
        pd.to_numeric(plan["strike_daily"], errors="coerce").gt(0),
        plan["strike_static"],
    )
    plan["strike"] = pd.to_numeric(plan["strike"], errors="coerce")
    plan = plan[plan["strike"].gt(0)].copy()

    keep = [
        "order_book_id",
        "maturity_date",
        "days",
        "term",
        "cp",
        "strike",
        "strike_static",
        "strike_daily",
    ]
    plan = plan[keep].sort_values(["days", "strike", "cp", "order_book_id"])
    if plan["order_book_id"].duplicated().any():
        raise AssertionError("contract plan contains duplicate order_book_id")
    if set(plan["days"].unique()) != {near_d, next_d}:
        raise RuntimeError(f"incomplete near/next plan for {symbol} on {date.date()}")

    path.parent.mkdir(parents=True, exist_ok=True)
    plan.to_parquet(path, index=False)
    return plan.reset_index(drop=True)


def fetch_historical_bars(
    symbol: str, date, plan: pd.DataFrame, force: bool = False
) -> pd.DataFrame:
    """Fetch native 30-minute close/OI bars for the planned contracts."""
    ensure_rq()
    date = pd.Timestamp(date).normalize()
    path = _bar_path(symbol, date, plan)
    if path.exists() and not force:
        bars = pd.read_parquet(path)
        bars["datetime"] = pd.to_datetime(bars["datetime"])
        return bars

    ids = plan["order_book_id"].astype(str).tolist()
    frames = []
    for batch in _chunks(ids):
        raw = _retry(
            f"30m bars {symbol} {date.date()} ({len(batch)} contracts)",
            lambda batch=batch: rq.get_price(
                batch,
                start_date=date,
                end_date=date,
                frequency=INTRADAY_PARAMS["frequency"],
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
    bars.to_parquet(path, index=False)
    return bars.reset_index(drop=True)


def expected_timestamps(date) -> list[pd.Timestamp]:
    date = pd.Timestamp(date).normalize()
    return [
        pd.Timestamp(f"{date.date()} {hhmm}:00")
        for hhmm in INTRADAY_PARAMS["sample_times"]
    ]


def assemble_historical_snapshot(
    symbol: str,
    date,
    timestamp,
    plan: pd.DataFrame,
    bars: pd.DataFrame,
) -> tuple[dict | None, ChainAudit, pd.DataFrame]:
    """Join one exact timestamp to its contract metadata and build core schema."""
    date = pd.Timestamp(date).normalize()
    timestamp = pd.Timestamp(timestamp)
    point = bars[bars["datetime"] == timestamp].copy()
    point = point.merge(
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
    point["price_source"] = "30m_close"

    days = sorted(int(x) for x in plan["days"].unique())
    near_d = days[0] if len(days) >= 1 else None
    next_d = days[1] if len(days) >= 2 else None
    calls = int((point["cp"] == "c").sum()) if not point.empty else 0
    puts = int((point["cp"] == "p").sum()) if not point.empty else 0

    if len(days) < 2:
        status = "missing_expiry_plan"
        snap = None
    else:
        by_expiry = {}
        for dd in (near_d, next_d):
            frame = point[point["days"] == dd][["strike", "cp", "price", "oi"]]
            by_expiry[dd] = frame.sort_values(["strike", "cp"]).reset_index(drop=True)
        if any(df.empty for df in by_expiry.values()):
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
                "price_source": "30m_close",
            }

    audit = ChainAudit(
        symbol=symbol,
        timestamp=timestamp,
        near_days=near_d,
        next_days=next_d,
        expected_contracts=len(plan),
        bars_found=len(bars[bars["datetime"] == timestamp]),
        valid_prices=len(point),
        calls=calls,
        puts=puts,
        status=status,
    )
    return snap, audit, point


def quota_snapshot() -> dict:
    ensure_rq()
    q = _retry("user.get_quota", lambda: rq.user.get_quota())
    return dict(q or {})
