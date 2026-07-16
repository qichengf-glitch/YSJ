#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
cd "$WORKSPACE_DIR"

export CN_VIX_DB="${CN_VIX_DB:-/var/data/live_vix.sqlite}"
HOST="${DASHBOARD_HOST:-0.0.0.0}"
PORT="${DASHBOARD_PORT:-${PORT:-8765}}"
LOG_DIR="${CN_VIX_LOG_DIR:-/var/data/dashboard_logs}"
HISTORY_PATH="${CN_VIX_HISTORY_30M:-$PACKAGE_DIR/outputs/vix_30m_2y.csv}"

mkdir -p "$(dirname "$CN_VIX_DB")" "$LOG_DIR"

if [ "${CN_VIX_BOOTSTRAP_ON_START:-1}" = "1" ] && [ ! -f "$CN_VIX_DB" ] && [ -f "$HISTORY_PATH" ]; then
  echo "bootstrapping CN VIX dashboard database from $HISTORY_PATH"
  python -m cn_option_vix.pipeline.bootstrap_dashboard \
    --history-30m "$HISTORY_PATH" \
    --db "$CN_VIX_DB" \
    --skip-5m
fi

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
