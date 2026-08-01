#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
LOG_DIR="${CN_VIX_LOG_DIR:-$PACKAGE_DIR/outputs/dashboard_logs}"
mkdir -p "$LOG_DIR"
cd "$WORKSPACE_DIR"

PY="${PYTHON_BIN:-python}"
export PYTHONUNBUFFERED=1
export CN_VIX_DB="${CN_VIX_DB:-$PACKAGE_DIR/data/live_vix.sqlite}"
HOST="${DASHBOARD_HOST:-127.0.0.1}"
PORT="${DASHBOARD_PORT:-8765}"
RESTART_SECONDS="${CN_VIX_SUPERVISOR_RESTART_SECONDS:-5}"
RESERVE_MIB="${CN_VIX_BACKFILL_RESERVE_MIB:-64}"
LOOKBACK_DAYS="${CN_VIX_CATCHUP_LOOKBACK_TRADING_DAYS:-10}"
AUTO_BACKFILL="${CN_VIX_AUTO_BACKFILL:-1}"

rotate_log() {
  local path="$1"
  if [[ -f "$path" ]] && [[ $(wc -c < "$path") -gt 20971520 ]]; then
    mv "$path" "$path.1"
  fi
}

WEB_LOG="$LOG_DIR/web.log"
COLLECTOR_LOG="$LOG_DIR/collector_5m.log"
REPAIR_LOG="$LOG_DIR/repair.log"
for log in "$WEB_LOG" "$COLLECTOR_LOG" "$REPAIR_LOG"; do
  rotate_log "$log"
done

supervise() {
  local name="$1"
  local log="$2"
  shift 2
  local child_pid=""
  stop_child() {
    if [[ -n "$child_pid" ]]; then
      kill "$child_pid" 2>/dev/null || true
      wait "$child_pid" 2>/dev/null || true
    fi
    exit 0
  }
  trap stop_child TERM INT
  set +e
  while true; do
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] starting $name" >> "$log"
    "$@" >> "$log" 2>&1 &
    child_pid=$!
    wait "$child_pid"
    rc=$?
    child_pid=""
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $name exited rc=$rc; restarting in ${RESTART_SECONDS}s" >> "$log"
    sleep "$RESTART_SECONDS"
  done
}

PIDS=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

supervise web "$WEB_LOG" \
  "$PY" -m uvicorn cn_option_vix.web.app:app --host "$HOST" --port "$PORT" &
PIDS+=("$!")

echo "dashboard: http://$HOST:$PORT"
echo "web log: $WEB_LOG"

# Repair missed days before the live collector chooses its next five-minute slot.
# Failure is non-fatal: the live collector must still start and scheduled repair
# will try again at the configured reconciliation times.
if [[ "$AUTO_BACKFILL" != "0" ]]; then
  echo "startup catch-up: enabled"
  "$PY" -m cn_option_vix.pipeline.sync_missing_5m \
    --db "$CN_VIX_DB" \
    --reserve-mib "$RESERVE_MIB" \
    --lookback-trading-days "$LOOKBACK_DAYS" \
    --best-effort \
    >> "$REPAIR_LOG" 2>&1 || true
else
  echo "startup catch-up: disabled (CN_VIX_AUTO_BACKFILL=0)"
fi

supervise collector "$COLLECTOR_LOG" \
  "$PY" -m cn_option_vix.pipeline.monitor_live_5m --db "$CN_VIX_DB" &
PIDS+=("$!")

if [[ "$AUTO_BACKFILL" != "0" ]]; then
  supervise repair "$REPAIR_LOG" \
    "$PY" -m cn_option_vix.pipeline.monitor_repair \
      --db "$CN_VIX_DB" \
      --reserve-mib "$RESERVE_MIB" \
      --lookback-trading-days "$LOOKBACK_DAYS" \
      --no-startup &
  PIDS+=("$!")
fi

echo "collector log: $COLLECTOR_LOG"
echo "repair log: $REPAIR_LOG"
wait "${PIDS[@]}"
