#!/usr/bin/env python3
"""Probe the current RiceQuant/RQData account capabilities.

The script is intentionally read-only and prints no credential values. It checks
whether the configured account can access the data classes required by the
market-data service: instruments, daily bars, minute bars, realtime snapshots,
point-in-time financials, performance reports, and listed option basics.
"""

from __future__ import annotations

import os
import signal
import socket
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse


def _len(value: Any) -> int | str:
    try:
        return len(value)
    except Exception:
        return "unknown"


def _shape(value: Any) -> str:
    shape = getattr(value, "shape", None)
    if shape:
        return f"shape={shape}"
    return f"rows={_len(value)}"


def _probe(name: str, fn: Callable[[], Any]) -> dict[str, str]:
    try:
        value = fn()
        return {"name": name, "status": "OK", "detail": _shape(value)}
    except Exception as exc:  # noqa: BLE001 - probe should continue after failures
        return {
            "name": name,
            "status": "FAIL",
            "detail": f"{type(exc).__name__}: {exc}",
        }


@contextmanager
def _hard_timeout(seconds: int, label: str):
    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"{label} did not finish within {seconds}s")

    previous = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _clean_uri(raw_uri: str) -> str:
    uri = raw_uri.strip()
    if len(uri) >= 2 and uri[0] == uri[-1] and uri[0] in {"'", '"'}:
        uri = uri[1:-1].strip()
    return uri


def _describe_endpoint(uri: str) -> tuple[str, int] | None:
    parsed = urlparse(uri)
    if not parsed.hostname or not parsed.port:
        return None
    return parsed.hostname, parsed.port


def _probe_tcp(uri: str) -> None:
    endpoint = _describe_endpoint(uri)
    if endpoint is None:
        print("endpoint: could not parse host/port from URI")
        return
    host, port = endpoint
    print(f"endpoint: {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=5):
            print("tcp connectivity: OK")
    except Exception as exc:  # noqa: BLE001 - diagnostics should be clear
        print(f"tcp connectivity: FAIL ({type(exc).__name__}: {exc})")


def main() -> int:
    raw_uri = os.getenv("RQDATA_URI") or os.getenv("RQDATAC_URI") or os.getenv("RQ_LICENSE")
    if not raw_uri:
        print("RQDATA_URI/RQDATAC_URI/RQ_LICENSE is not set in this shell.")
        print("Example:")
        print("  export RQDATA_URI='tcp://...'\n")
        return 2
    uri = _clean_uri(raw_uri)

    try:
        import rqdatac as rq
    except Exception:
        traceback.print_exc()
        return 2

    print(f"rqdatac version: {getattr(rq, '__version__', 'unknown')}")
    print("credential: <set, hidden>")
    _probe_tcp(uri)
    try:
        with _hard_timeout(20, "rq.init"):
            rq.init(uri=uri, connect_timeout=5, timeout=15)
    except Exception as exc:  # noqa: BLE001 - keep the failure actionable
        print(f"rq.init: FAIL ({type(exc).__name__}: {exc})")
        return 2
    print("rq.init: OK")

    today = date.today()
    end = today - timedelta(days=1)
    start = end - timedelta(days=10)
    symbol = "000001.XSHE"

    probes = [
        (
            "A-share instruments",
            lambda: rq.all_instruments(type="CS", date=str(end), market="cn"),
        ),
        (
            "A-share daily bars",
            lambda: rq.get_price(
                symbol,
                start_date=str(start),
                end_date=str(end),
                frequency="1d",
                fields=["open", "high", "low", "close", "volume", "total_turnover"],
                adjust_type="none",
                expect_df=True,
            ),
        ),
        (
            "A-share 1m bars",
            lambda: rq.get_price(
                symbol,
                start_date=str(start),
                end_date=str(end),
                frequency="1m",
                fields=["open", "high", "low", "close", "volume", "total_turnover"],
                adjust_type="none",
                expect_df=True,
            ),
        ),
        (
            "Realtime/current snapshot",
            lambda: rq.current_snapshot([symbol]),
        ),
        (
            "PIT financials",
            lambda: rq.get_pit_financials_ex(
                order_book_ids=[symbol],
                fields=["revenue", "net_profit"],
                start_quarter="2024q1",
                end_quarter="2024q4",
                date=str(end),
                statements="latest",
                market="cn",
            ),
        ),
        (
            "Financial performance report",
            lambda: rq.current_performance(
                order_book_ids=[symbol],
                fields=["revenue", "net_profit_parent_company"],
                market="cn",
            ),
        ),
        (
            "Listed option instruments",
            lambda: rq.all_instruments(type="Option", date=str(end), market="cn"),
        ),
        (
            "Index option daily bars",
            lambda: rq.get_price(
                ["IO"],
                start_date=str(start),
                end_date=str(end),
                frequency="1d",
                fields=["close"],
                expect_df=True,
            ),
        ),
    ]

    results = [_probe(name, fn) for name, fn in probes]
    width = max(len(item["name"]) for item in results)
    print("\nCapability probe:")
    for item in results:
        print(f"- {item['name']:<{width}}  {item['status']:<4}  {item['detail']}")

    failed = [item for item in results if item["status"] != "OK"]
    print("\nSummary:")
    print(f"  OK: {len(results) - len(failed)}")
    print(f"  FAIL: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
