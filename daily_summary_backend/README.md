# Daily Summary Backend

This service wraps the intern-provided Jin10 realtime news and Claude summary
pipeline for Render.

## Runtime

- `app/collector.py` keeps the Jin10 websocket open and writes JSONL files.
- `app/summary_generator.py` reads those JSONL files and produces the latest
  daily cross-market summary.
- `app/main.py` exposes FastAPI endpoints consumed by the Next.js UI.

## Required Environment

- `JIN10_SECRET_KEY`: Jin10 websocket/API secret key.

## Optional Environment

- `ANTHROPIC_API_KEY`: Claude API key used for scoring and digest generation.
  Without this key, the service still starts and records the Jin10 classified
  realtime feed, but Claude score/gate fields and structured digests remain
  pending.
- `DAILY_SUMMARY_DATA_DIR`: persistent data directory. Render defaults this to
  `/var/data/daily_summary`.
- `DAILY_SUMMARY_BACKEND_URL`: Next.js proxy target. Render defaults this to
  `http://127.0.0.1:8010`.
- `DAILY_SUMMARY_ENABLE_COLLECTOR`: set `false` to run API only.
- `DAILY_SUMMARY_ENABLE_DIGEST_SCHEDULER`: set `false` to disable scheduled
  digest generation.
- `DAILY_SUMMARY_DIGEST_INTERVAL_MINUTES`: default `30`.
- `DAILY_SUMMARY_CLAUDE_MODEL`: defaults to the intern package model string.
- `DAILY_SUMMARY_LOG_RAW_MESSAGES`: default `false` to reduce disk pressure.

The package currently provides a full A-share and US-stock realtime path from
the intern code. Forex and commodity inputs are supported by the summary layer,
but their collector scripts were not included in the provided zip.
