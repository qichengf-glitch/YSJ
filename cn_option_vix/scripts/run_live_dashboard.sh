#!/usr/bin/env bash
set -euo pipefail
PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
LOG_DIR="$PACKAGE_DIR/outputs/dashboard_logs"
mkdir -p "$LOG_DIR"
cd "$WORKSPACE_DIR"

export CN_VIX_DB="${CN_VIX_DB:-$PACKAGE_DIR/data/live_vix.sqlite}"
HOST="${DASHBOARD_HOST:-127.0.0.1}"
PORT="${DASHBOARD_PORT:-8765}"

python -m cn_option_vix.pipeline.monitor_live_5m \
  --db "$CN_VIX_DB" \
  >> "$LOG_DIR/collector_5m.log" 2>&1 &
COLLECTOR_PID=$!

cleanup() {
  kill "$COLLECTOR_PID" 2>/dev/null || true
  wait "$COLLECTOR_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "collector pid: $COLLECTOR_PID"
echo "collector log: $LOG_DIR/collector_5m.log"
echo "dashboard: http://$HOST:$PORT"

python -m uvicorn cn_option_vix.web.app:app \
  --host "$HOST" \
  --port "$PORT"
