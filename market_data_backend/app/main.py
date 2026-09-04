from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import clickhouse_connect
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


APP_NAME = "YSJ A-Share Market Data API"


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _client():
    return clickhouse_connect.get_client(
        host=_env("CLICKHOUSE_HOST"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "8443")),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=_env("CLICKHOUSE_PASSWORD"),
        secure=os.environ.get("CLICKHOUSE_SECURE", "true").lower() != "false",
    )


def _rq_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".SZ"):
        return value.removesuffix(".SZ") + ".XSHE"
    if value.endswith(".SH"):
        return value.removesuffix(".SH") + ".XSHG"
    return value


def _panel_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".XSHE"):
        return value.removesuffix(".XSHE") + ".SZ"
    if value.endswith(".XSHG"):
        return value.removesuffix(".XSHG") + ".SH"
    return value


def _quote_list(values: list[str]) -> str:
    return ",".join("'" + value.replace("'", "\\'") + "'" for value in values)


def _require_token(authorization: str | None = Header(default=None)) -> None:
    token = os.environ.get("MARKET_DATA_API_TOKEN")
    if not token:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Invalid market data API token.")


def _serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _rows(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        item = {column: _serialise(value) for column, value in zip(columns, row)}
        if "symbol" in item:
            item["symbol"] = _panel_symbol(str(item["symbol"]))
        if "total_turnover" in item:
            item["amount"] = item.pop("total_turnover")
        output.append(item)
    return output


def _symbol_filter(symbols: list[str] | None) -> str:
    if not symbols:
        return ""
    return f" AND symbol IN ({_quote_list([_rq_symbol(symbol) for symbol in symbols])})"


class RangeRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    start_time: str | None = None
    end_time: str | None = None
    start: str | None = None
    end: str | None = None
    limit: int = 200_000

    @property
    def start_value(self) -> str | None:
        return self.start_time or self.start

    @property
    def end_value(self) -> str | None:
        return self.end_time or self.end


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health(_: None = Depends(_require_token)) -> dict[str, Any]:
    client = _client()
    ok = client.query("SELECT 1").result_rows[0][0]
    return {"status": "ok", "clickhouse": ok}


@app.get("/api/market-data/summary")
def summary(_: None = Depends(_require_token)) -> dict[str, Any]:
    client = _client()
    one_m = client.query(
        """
        SELECT
            min(trade_date),
            max(trade_date),
            countDistinct(trade_date),
            countDistinct(symbol),
            count()
        FROM market.a_share_bars_1m
        """
    ).result_rows[0]
    one_d = client.query(
        """
        SELECT
            min(trade_date),
            max(trade_date),
            countDistinct(trade_date),
            countDistinct(symbol),
            count()
        FROM market.a_share_bars_1d
        """
    ).result_rows[0]
    latest = client.query(
        """
        SELECT max(ts)
        FROM market.a_share_bars_1m
        """
    ).result_rows[0][0]
    return {
        "status": "ok",
        "latest_ts": _serialise(latest),
        "minute": {
            "min_date": _serialise(one_m[0]),
            "max_date": _serialise(one_m[1]),
            "dates": one_m[2],
            "symbols": one_m[3],
            "rows": one_m[4],
        },
        "daily": {
            "min_date": _serialise(one_d[0]),
            "max_date": _serialise(one_d[1]),
            "dates": one_d[2],
            "symbols": one_d[3],
            "rows": one_d[4],
        },
    }


@app.get("/api/market-data/latest")
def latest(
    symbols: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    _: None = Depends(_require_token),
) -> dict[str, Any]:
    client = _client()
    symbol_list = [item.strip() for item in symbols.split(",")] if symbols else None
    where = _symbol_filter(symbol_list)
    columns = ["symbol", "datetime", "open", "high", "low", "close", "volume", "total_turnover"]
    result = client.query(
        f"""
        SELECT symbol, ts AS datetime, open, high, low, close, volume, total_turnover
        FROM market.v_a_share_latest_1m
        WHERE 1 = 1 {where}
        ORDER BY total_turnover DESC
        LIMIT {limit}
        """
    ).result_rows
    return {"data": _rows(columns, result)}


@app.post("/api/market-data/minute")
def minute(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    start = request.start_value
    end = request.end_value
    if not start or not end:
        raise HTTPException(status_code=400, detail="start_time and end_time are required.")
    client = _client()
    where = _symbol_filter(request.symbols)
    columns = ["symbol", "datetime", "open", "high", "low", "close", "volume", "total_turnover"]
    result = client.query(
        f"""
        SELECT symbol, ts AS datetime, open, high, low, close, volume, total_turnover
        FROM market.a_share_bars_1m
        WHERE ts >= parseDateTimeBestEffort('{start}')
          AND ts <= parseDateTimeBestEffort('{end}')
          {where}
        ORDER BY symbol, datetime
        LIMIT {int(request.limit)}
        """
    ).result_rows
    return {"data": _rows(columns, result)}


@app.post("/api/market-data/full_minute")
def full_minute(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    return minute(request, _)


@app.post("/api/market-data/daily")
def daily(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    start = request.start_value
    end = request.end_value
    if not start or not end:
        raise HTTPException(status_code=400, detail="start_time and end_time are required.")
    client = _client()
    where = _symbol_filter(request.symbols)
    columns = ["symbol", "date", "open", "high", "low", "close", "volume", "total_turnover"]
    result = client.query(
        f"""
        SELECT symbol, trade_date AS date, open, high, low, close, volume, total_turnover
        FROM market.a_share_bars_1d
        WHERE trade_date >= toDate('{start}')
          AND trade_date <= toDate('{end}')
          {where}
        ORDER BY symbol, date
        LIMIT {int(request.limit)}
        """
    ).result_rows
    return {"data": _rows(columns, result)}


@app.get("/api/market-data/realtime")
def realtime(
    symbols: str | None = Query(default=None),
    limit: int = Query(default=6000, ge=1, le=10000),
    _: None = Depends(_require_token),
) -> dict[str, Any]:
    client = _client()
    symbol_list = [item.strip() for item in symbols.split(",")] if symbols else None
    where = _symbol_filter(symbol_list)
    columns = [
        "symbol",
        "datetime",
        "last_price",
        "open",
        "high",
        "low",
        "volume",
        "total_turnover",
    ]
    result = client.query(
        f"""
        SELECT symbol, ts AS datetime, close AS last_price, open, high, low, volume, total_turnover
        FROM market.v_a_share_latest_1m
        WHERE 1 = 1 {where}
        ORDER BY total_turnover DESC
        LIMIT {limit}
        """
    ).result_rows
    data = _rows(columns, result)
    for item in data:
        item["prev_close"] = None
        item["change_amount"] = None
        item["change_pct"] = None
    return {"data": data}


@app.post("/daily")
def tick_panel_daily(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    return daily(request, _)


@app.post("/minute")
def tick_panel_minute(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    return minute(request, _)


@app.post("/full_minute")
def tick_panel_full_minute(request: RangeRequest, _: None = Depends(_require_token)) -> dict[str, Any]:
    return full_minute(request, _)


@app.get("/realtime")
def tick_panel_realtime(
    symbols: str | None = Query(default=None),
    _: None = Depends(_require_token),
) -> dict[str, Any]:
    return realtime(symbols=symbols, _=_)
