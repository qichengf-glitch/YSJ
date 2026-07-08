import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import settings
from .database import get_conn, rows_to_dicts, utc_now
from .logic import parse_dt, safe_float, ticker_root


def yahoo_symbol(ticker: str) -> str:
    """Convert Jin10 symbols such as TSM.N / ILMN.O to Yahoo Finance symbols."""
    root = ticker_root(ticker)
    # Most US ADR/common tickers are directly supported by Yahoo without suffix.
    # If special class-share tickers are added later, map them here, e.g. BRK.B -> BRK-B.
    special = {
        "BRK.B": "BRK-B",
        "BRK.A": "BRK-A",
        "BF.B": "BF-B",
    }
    return special.get(root, root)


def _cache_fresh(last_fetched_at: Optional[str]) -> bool:
    dt = parse_dt(last_fetched_at)
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - dt <= timedelta(minutes=max(1, settings.price_cache_minutes))


def _cache_key(range_key: str, interval: str) -> Tuple[str, str]:
    supported_ranges = {"1d", "5d", "1mo"}
    supported_intervals = {"1m", "2m", "5m", "15m", "30m", "60m"}
    r = range_key if range_key in supported_ranges else "1d"
    i = interval if interval in supported_intervals else "5m"
    if r == "1mo" and i in {"1m", "2m"}:
        i = "30m"
    return r, i


def _read_cached_bars(ticker: str, interval: str, range_key: str) -> Optional[Dict[str, Any]]:
    provider = settings.price_provider or "yfinance"
    with get_conn() as conn:
        cache = conn.execute(
            "SELECT * FROM price_fetch_cache WHERE ticker=? AND provider=? AND interval=? AND range_key=?",
            (ticker, provider, interval, range_key),
        ).fetchone()
        # Do not cache empty/no-data results as valid UI data; they often happen when Yahoo throttles,
        # when it is a market holiday, or when the symbol cannot be resolved.
        if not cache or cache["status"] != "ok" or not _cache_fresh(cache["last_fetched_at"]):
            return None
        rows = rows_to_dicts(conn.execute(
            "SELECT * FROM price_bars WHERE ticker=? AND provider=? AND interval=? ORDER BY datetime(ts) ASC",
            (ticker, provider, interval),
        ).fetchall())
    if len(rows) < 2:
        return None
    return _format_price_response(ticker, provider, interval, range_key, rows, cached=True)


def _write_cache(ticker: str, interval: str, range_key: str, rows: List[Dict[str, Any]], status: str = "ok", error: Optional[str] = None) -> None:
    provider = settings.price_provider or "yfinance"
    now = utc_now()
    with get_conn() as conn:
        for r in rows:
            conn.execute(
                """
                INSERT INTO price_bars(ticker, provider, interval, ts, open, high, low, close, volume, raw_json, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, provider, interval, ts) DO UPDATE SET
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    raw_json=excluded.raw_json,
                    fetched_at=excluded.fetched_at
                """,
                (
                    ticker, provider, interval, r["time"], r.get("open"), r.get("high"), r.get("low"),
                    r.get("close"), r.get("volume"), json.dumps(r, ensure_ascii=False), now,
                ),
            )
        conn.execute(
            """
            INSERT INTO price_fetch_cache(ticker, provider, interval, range_key, last_fetched_at, status, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, provider, interval, range_key) DO UPDATE SET
                last_fetched_at=excluded.last_fetched_at,
                status=excluded.status,
                error=excluded.error
            """,
            (ticker, provider, interval, range_key, now, status, error),
        )


def _format_price_response(
    ticker: str,
    provider: str,
    interval: str,
    range_key: str,
    rows: List[Dict[str, Any]],
    cached: bool,
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    clean = []
    seen = set()
    for r in rows:
        close = safe_float(r.get("close"))
        ts = r.get("time") or r.get("ts")
        if close is None or not ts or ts in seen:
            continue
        seen.add(ts)
        clean.append({
            "time": ts,
            "open": safe_float(r.get("open")),
            "high": safe_float(r.get("high")),
            "low": safe_float(r.get("low")),
            "close": close,
            "volume": safe_float(r.get("volume")) or 0,
        })
    first = clean[0]["close"] if clean else None
    last = clean[-1]["close"] if clean else None
    high = max((x["high"] for x in clean if x["high"] is not None), default=None)
    low = min((x["low"] for x in clean if x["low"] is not None), default=None)
    volume = sum((x["volume"] or 0) for x in clean)
    change = None if first is None or last is None else last - first
    change_pct = None if first in (None, 0) or change is None else change / abs(first) * 100
    return {
        "ticker": ticker,
        "normalized_ticker": yahoo_symbol(ticker),
        "provider": provider,
        "range": range_key,
        "interval": interval,
        "cached": cached,
        "bars": clean,
        "summary": {
            "first": first,
            "last": last,
            "change": change,
            "change_pct": change_pct,
            "high": high,
            "low": low,
            "volume": volume,
            "points": len(clean),
        },
        "diagnostics": diagnostics or {},
        "note": "Price data is for reference only and may be delayed. yfinance is suitable for internal reference and prototyping, not production trading systems.",
    }


def _df_to_rows(df: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if df is None or getattr(df, "empty", True):
        return rows
    # yfinance may return a MultiIndex for columns in some versions.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    for idx, row in df.iterrows():
        try:
            ts = idx.to_pydatetime().isoformat()
        except Exception:
            ts = str(idx)
        try:
            rows.append({
                "time": ts,
                "open": None if row.get("Open") is None else float(row.get("Open")),
                "high": None if row.get("High") is None else float(row.get("High")),
                "low": None if row.get("Low") is None else float(row.get("Low")),
                "close": None if row.get("Close") is None else float(row.get("Close")),
                "volume": None if row.get("Volume") is None else float(row.get("Volume")),
            })
        except Exception:
            continue
    return rows


def _fetch_yfinance(symbol: str, range_key: str, interval: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    import yfinance as yf  # type: ignore

    attempts = []

    def attempt(label: str, period: str, intrvl: str, method: str = "history") -> List[Dict[str, Any]]:
        attempts.append({"label": label, "period": period, "interval": intrvl, "method": method})
        if method == "download":
            df = yf.download(symbol, period=period, interval=intrvl, auto_adjust=True, prepost=True, progress=False, threads=False)
        else:
            df = yf.Ticker(symbol).history(period=period, interval=intrvl, auto_adjust=True, prepost=True)
        return _df_to_rows(df)

    # Primary request.
    rows = attempt("requested", range_key, interval, "history")
    if len(rows) >= 2:
        return rows, {"symbol": symbol, "attempts": attempts, "fallback_used": False}

    # Fallback 1: a one-day intraday request can be empty during holidays / before data is published;
    # pull the last five sessions instead.
    fallback_interval = "15m" if interval in {"1m", "2m", "5m"} else interval
    rows = attempt("fallback_5d", "5d", fallback_interval, "history")
    if len(rows) >= 2:
        return rows, {"symbol": symbol, "attempts": attempts, "fallback_used": True, "effective_range": "5d", "effective_interval": fallback_interval}

    # Fallback 2: use yf.download, which sometimes succeeds when Ticker.history returns empty.
    rows = attempt("fallback_download_5d", "5d", fallback_interval, "download")
    if len(rows) >= 2:
        return rows, {"symbol": symbol, "attempts": attempts, "fallback_used": True, "effective_range": "5d", "effective_interval": fallback_interval}

    # Fallback 3: daily bars, enough to show a meaningful trend when intraday is unavailable.
    rows = attempt("fallback_1mo_daily", "1mo", "1d", "history")
    return rows, {"symbol": symbol, "attempts": attempts, "fallback_used": True, "effective_range": "1mo", "effective_interval": "1d"}


def get_intraday_price(ticker: str, range_key: str = "1d", interval: str = "5m", force: bool = False) -> Dict[str, Any]:
    if not ticker:
        raise ValueError("ticker is required")
    range_key, interval = _cache_key(range_key, interval)
    ticker = ticker.strip().upper()
    provider = settings.price_provider or "yfinance"

    if not force:
        cached = _read_cached_bars(ticker, interval, range_key)
        if cached:
            return cached

    if provider != "yfinance":
        raise ValueError(f"Unsupported PRICE_PROVIDER={provider}; current MVP supports yfinance")

    try:
        symbol = yahoo_symbol(ticker)
        rows, diagnostics = _fetch_yfinance(symbol, range_key, interval)
        status = "ok" if len(rows) >= 2 else "no_data"
        error = None if status == "ok" else f"yfinance returned {len(rows)} usable price bars for {symbol}"
        _write_cache(ticker, interval, range_key, rows, status=status, error=error)
        return _format_price_response(ticker, provider, interval, range_key, rows, cached=False, diagnostics=diagnostics)
    except Exception as exc:
        _write_cache(ticker, interval, range_key, [], status="error", error=str(exc))
        # Last-resort stale cache, if any.
        with get_conn() as conn:
            rows = rows_to_dicts(conn.execute(
                "SELECT * FROM price_bars WHERE ticker=? AND provider=? AND interval=? ORDER BY datetime(ts) ASC",
                (ticker, provider, interval),
            ).fetchall())
        if rows:
            data = _format_price_response(ticker, provider, interval, range_key, rows, cached=True)
            data["warning"] = f"Using stale cached price bars because provider fetch failed: {exc}"
            return data
        raise
