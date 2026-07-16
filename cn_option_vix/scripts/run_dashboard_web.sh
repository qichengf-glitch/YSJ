#!/usr/bin/env bash
set -euo pipefail
PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
cd "$WORKSPACE_DIR"

export CN_VIX_DB="${CN_VIX_DB:-$PACKAGE_DIR/data/live_vix.sqlite}"
HOST="${DASHBOARD_HOST:-127.0.0.1}"
PORT="${DASHBOARD_PORT:-8765}"

exec python -m uvicorn cn_option_vix.web.app:app \
  --host "$HOST" \
  --port "$PORT"
