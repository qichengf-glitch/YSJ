#!/usr/bin/env python3
"""Background scheduler for Stock Grader production refreshes.

The website reads CSV reports. This process is responsible for periodically
creating a fresh full_scores_YYYYMMDD.csv without doing that expensive work in a
web request.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
REPORT_DIR = Path(os.environ.get("STOCK_GRADER_REPORT_DIR", ROOT / "data" / "reports"))
LOG_DIR = Path(os.environ.get("STOCK_GRADER_LOG_DIR", REPORT_DIR.parent / "logs"))

WEEKDAYS = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def scheduler_timezone() -> ZoneInfo:
    return ZoneInfo(os.environ.get("STOCK_GRADER_SCHEDULER_TZ", "America/New_York"))


def next_run_time(now: datetime) -> datetime:
    day_name = os.environ.get("STOCK_GRADER_WEEKLY_DAY", "MON").strip().upper()[:3]
    target_day = WEEKDAYS.get(day_name, 0)
    target_hour = int(os.environ.get("STOCK_GRADER_WEEKLY_HOUR", "7"))
    target_minute = int(os.environ.get("STOCK_GRADER_WEEKLY_MINUTE", "0"))

    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    days_ahead = (target_day - now.weekday()) % 7
    target = target + timedelta(days=days_ahead)
    if target <= now:
        target = target + timedelta(days=7)
    return target


def report_exists_today(tz: ZoneInfo) -> bool:
    today = datetime.now(tz).strftime("%Y%m%d")
    return (REPORT_DIR / f"full_scores_{today}.csv").exists()


def run_refresh(reason: str) -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "run.py", "--grade-all", "--force"]
    if not bool_env("STOCK_GRADER_USE_LLM", False):
        cmd.append("--no-llm")

    timeout_seconds = int(os.environ.get("STOCK_GRADER_REFRESH_TIMEOUT_SECONDS", "21600"))
    log_path = LOG_DIR / "stock_grader_scheduler.log"
    started = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    env = os.environ.copy()
    env.setdefault("STOCK_GRADER_RESUME_TODAY", "true")
    env.setdefault("STOCK_GRADER_FETCH_CACHE", "true")
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{started}] starting Stock Grader refresh ({reason}): {' '.join(cmd)}\n")
        log.flush()
        try:
            result = subprocess.run(
                cmd,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                env=env,
                timeout=timeout_seconds,
            )
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
            log.write(
                f"\nStock Grader refresh timed out after {timeout_seconds} seconds.\n"
            )
        finished = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        log.write(f"[{finished}] Stock Grader refresh exited with code {returncode}\n")
    return returncode


def main() -> int:
    tz = scheduler_timezone()
    run_on_start = bool_env("STOCK_GRADER_UPDATE_ON_START", True)
    skip_if_today = bool_env("STOCK_GRADER_SKIP_IF_REPORT_TODAY", True)

    if run_on_start and not (skip_if_today and report_exists_today(tz)):
        run_refresh("service-start")

    while True:
        now = datetime.now(tz)
        target = next_run_time(now)
        sleep_seconds = max(60, int((target - now).total_seconds()))
        print(
            f"Next Stock Grader refresh scheduled for {target.isoformat()} "
            f"({os.environ.get('STOCK_GRADER_SCHEDULER_TZ', 'America/New_York')})",
            flush=True,
        )
        time.sleep(sleep_seconds)
        run_refresh("weekly-schedule")


if __name__ == "__main__":
    raise SystemExit(main())
