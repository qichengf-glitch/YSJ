#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/cn_option_vix/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Missing VIX virtualenv. Run ./scripts/setup_server.sh" >&2; exit 2; }

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export CN_VIX_DB="${CN_VIX_DB:-$ROOT/cn_option_vix/data/live_vix.sqlite}"
export DASHBOARD_HOST="${DASHBOARD_HOST:-127.0.0.1}"
export DASHBOARD_PORT="${DASHBOARD_PORT:-8765}"
export PATH="$ROOT/cn_option_vix/.venv/bin:$PATH"
cd "$ROOT"

if [[ -n "${RQDATA_URI:-${RQDATAC_URI:-}}" ]]; then
  exec bash "$ROOT/cn_option_vix/scripts/run_live_dashboard.sh"
fi

echo "RQDATA_URI is empty: serving the packaged CN VIX database without starting the collector."
exec "$PY" -m uvicorn cn_option_vix.web.app:app \
  --host "$DASHBOARD_HOST" \
  --port "$DASHBOARD_PORT"
