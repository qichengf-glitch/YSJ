#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-3000}"
DATA_DIR="${RENDER_DATA_DIR:-/var/data}"
mkdir -p "$DATA_DIR"

JIN10_DIR=""
if [[ -d "$ROOT/jin10_us_dashboard_site" ]]; then
  JIN10_DIR="$ROOT/jin10_us_dashboard_site"
elif [[ -d "$ROOT/jin10_us_dashboard_site_v6_5" ]]; then
  JIN10_DIR="$ROOT/jin10_us_dashboard_site_v6_5"
fi

export DATABASE_PATH="${DATABASE_PATH:-$DATA_DIR/us_dashboard.db}"
export CN_VIX_DB="${CN_VIX_DB:-$DATA_DIR/live_vix.sqlite}"
export CN_VIX_RQ_LOCK="${CN_VIX_RQ_LOCK:-$DATA_DIR/cn_vix_rqdata.lock}"
export MARKET_RADAR_BACKEND_URL="${MARKET_RADAR_BACKEND_URL:-http://127.0.0.1:8000}"
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

if [[ -n "$JIN10_DIR" ]]; then
  seed_sqlite "$JIN10_DIR/data/us_dashboard.db" "$DATABASE_PATH"
fi
seed_sqlite "$ROOT/cn_option_vix/data/live_vix.sqlite" "$CN_VIX_DB"

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

if [[ -n "$JIN10_DIR" ]]; then
  (
    cd "$JIN10_DIR"
    exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ) &
  PIDS+=("$!")
  echo "Jin10 backend started on 127.0.0.1:8000"
else
  echo "WARNING: Jin10 backend directory not found."
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
