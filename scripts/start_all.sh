#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/run"
LOG_DIR="$ROOT/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Missing $ROOT/.env. Run ./scripts/setup_server.sh and configure it first."
  exit 2
fi
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a

if [[ -z "${YSJ_ACCESS_PASSCODE:-}" ||
      "${YSJ_ACCESS_PASSCODE}" == "CHANGE_ME" ||
      -z "${YSJ_ACCESS_SECRET:-}" ||
      "${YSJ_ACCESS_SECRET}" == CHANGE_ME* ]]; then
  echo "YSJ_ACCESS_PASSCODE and YSJ_ACCESS_SECRET must be configured in .env."
  exit 2
fi
if [[ -z "${JIN10_SECRET_KEY:-}" ]]; then
  echo "WARNING: JIN10_SECRET_KEY is empty; Jin10 live sync jobs will fail until configured."
fi

require_file() {
  [[ -f "$1" ]] || { echo "Missing $1. Run ./scripts/setup_server.sh first."; exit 2; }
}

start_service() {
  local name="$1"; shift
  local pid_file="$RUN_DIR/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name already running (pid $(cat "$pid_file"))"
    return 0
  fi
  rm -f "$pid_file"
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid "$@" >>"$LOG_DIR/$name.log" 2>&1 &
  else
    nohup "$@" >>"$LOG_DIR/$name.log" 2>&1 &
  fi
  local pid=$!
  echo "$pid" > "$pid_file"
  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name failed to start. See $LOG_DIR/$name.log"
    exit 1
  fi
  echo "$name started (pid $pid)"
}

require_file "$ROOT/jin10_us_dashboard_site/.venv/bin/python"
require_file "$ROOT/cn_option_vix/.venv/bin/python"

if [[ ! -d "$ROOT/.next" ]]; then
  echo "Missing production build; running npm run build"
  (cd "$ROOT" && npm run build)
fi

start_service jin10 bash -lc \
  "cd '$ROOT/jin10_us_dashboard_site' && exec '$ROOT/jin10_us_dashboard_site/.venv/bin/python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

start_service cn_vix bash -lc \
  "cd '$ROOT' && exec bash '$ROOT/scripts/start_vix_service.sh'"

start_service ysj_web bash -lc \
  "cd '$ROOT' && export NODE_ENV=production; exec npm run start -- --hostname 0.0.0.0 --port 3000"

echo "All services started. Website: http://127.0.0.1:3000"
