"""Cross-process lock for all RQData traffic made by the CN VIX service.

The live collector, startup catch-up, manual repair, and scheduled reconciliation
must never open overlapping RQData jobs. Apart from avoiding duplicate traffic,
this reduces the chance of account login-machine/session conflicts.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, Iterator, TypeVar

import fcntl

T = TypeVar("T")

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK_PATH = PACKAGE_ROOT.parent / "run" / "cn_vix_rqdata.lock"


def _lock_path() -> Path:
    configured = os.environ.get("CN_VIX_RQ_LOCK")
    return Path(configured).expanduser() if configured else DEFAULT_LOCK_PATH


@contextmanager
def rqdata_process_lock(timeout_seconds: float | None = None) -> Iterator[Path]:
    """Acquire the exclusive process lock used by every RQData workflow."""
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else os.environ.get("CN_VIX_RQ_LOCK_TIMEOUT_SECONDS", "900")
    )
    started = time.monotonic()
    with path.open("a+") as handle:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if timeout >= 0 and time.monotonic() - started >= timeout:
                    raise TimeoutError(
                        f"timed out waiting {timeout:.0f}s for RQData lock: {path}"
                    )
                time.sleep(0.25)
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(f"pid={os.getpid()} acquired_at={time.time():.6f}\n")
            handle.flush()
            yield path
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def rqdata_locked(
    fn: Callable[..., T] | None = None,
    *,
    timeout_seconds: float | None = None,
):
    """Decorator for a complete RQData transaction."""

    def decorate(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with rqdata_process_lock(timeout_seconds=timeout_seconds):
                return func(*args, **kwargs)

        return wrapper

    return decorate(fn) if fn is not None else decorate
