#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-3000}"
DATA_DIR="${RENDER_DATA_DIR:-/var/data}"
mkdir -p "$DATA_DIR"

PREDICTION_MARKET_DIR="$ROOT/prediction_market_backend"

export PREDICTION_MARKET_DB="${PREDICTION_MARKET_DB:-${DATABASE_PATH:-$DATA_DIR/us_dashboard.db}}"
export DATABASE_PATH="$PREDICTION_MARKET_DB"
export CN_VIX_DB="${CN_VIX_DB:-$DATA_DIR/live_vix.sqlite}"
export CN_VIX_RQ_LOCK="${CN_VIX_RQ_LOCK:-$DATA_DIR/cn_vix_rqdata.lock}"
export CN_VIX_LOG_DIR="${CN_VIX_LOG_DIR:-$DATA_DIR/dashboard_logs}"
export PREDICTION_MARKET_BACKEND_URL="${PREDICTION_MARKET_BACKEND_URL:-http://127.0.0.1:8000}"
export CN_VIX_BACKEND_URL="${CN_VIX_BACKEND_URL:-http://127.0.0.1:8765}"
export VIX_DASHBOARD_PUBLIC_URL="${VIX_DASHBOARD_PUBLIC_URL:-/api/cn-option-vix-dashboard/index.html}"
export DASHBOARD_HOST="${DASHBOARD_HOST:-127.0.0.1}"
export DASHBOARD_PORT="${DASHBOARD_PORT:-8765}"

seed_sqlite() {
  local source="$1"
  local target="$2"
  mkdir -p "$(dirname "$target")"
  if [[ ! -f "$target" && -f "$source" ]]; then
    cp "$source" "$target"
    echo "Seeded $(basename "$target") from package snapshot."
  fi
}

seed_vix_sqlite_if_empty() {
  local source="$1"
  local target="$2"
  local python_bin="${PYTHON_BIN:-$ROOT/cn_option_vix/.venv/bin/python}"
  if [[ ! -x "$python_bin" ]] && command -v python3 >/dev/null 2>&1; then
    python_bin="$(command -v python3)"
  fi

  seed_sqlite "$source" "$target"
  if [[ ! -f "$source" || ! -f "$target" || ! -x "$python_bin" ]]; then
    return
  fi

  if "$python_bin" - "$target" <<'PY'
import sqlite3
import sys

path = sys.argv[1]
try:
    with sqlite3.connect(path) as conn:
        count = conn.execute("SELECT count(*) FROM vix_points").fetchone()[0]
except (sqlite3.DatabaseError, sqlite3.OperationalError):
    raise SystemExit(1)
raise SystemExit(0 if count == 0 else 1)
PY
  then
    cp "$target" "$target.empty-backup"
    cp "$source" "$target"
    echo "Seeded empty $(basename "$target") from package snapshot."
  fi
}

seed_vix_sqlite_if_empty "$ROOT/cn_option_vix/data/live_vix.sqlite" "$CN_VIX_DB"

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

if [[ -d "$PREDICTION_MARKET_DIR" ]]; then
  (
    cd "$PREDICTION_MARKET_DIR"
    exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ) &
  PIDS+=("$!")
  echo "Prediction Market backend started on 127.0.0.1:8000"
else
  echo "WARNING: prediction_market_backend directory not found."
fi

if [[ -d "$ROOT/cn_option_vix" ]]; then
  (
    cd "$ROOT"
    export PATH="$ROOT/cn_option_vix/.venv/bin:$PATH"
    if [[ -x "$ROOT/scripts/start_vix_service.sh" ]]; then
      exec bash "$ROOT/scripts/start_vix_service.sh"
    else
      exec bash "$ROOT/cn_option_vix/scripts/run_live_dashboard.sh"
    fi
  ) &
  PIDS+=("$!")
  echo "CN VIX service started on ${DASHBOARD_HOST}:${DASHBOARD_PORT}"
else
  echo "WARNING: cn_option_vix directory not found."
fi

echo "Next.js starting on 0.0.0.0:${PORT}"
exec npm run start -- --hostname 0.0.0.0 --port "$PORT"
