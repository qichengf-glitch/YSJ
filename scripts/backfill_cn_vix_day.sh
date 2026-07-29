#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 YYYY-MM-DD"
  exit 2
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
if [[ -z "${RQDATA_URI:-${RQDATAC_URI:-}}" ]]; then
  echo "RQDATA_URI is not configured."
  exit 2
fi
PY="$ROOT/cn_option_vix/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Missing VIX virtualenv. Run ./scripts/setup_server.sh"; exit 2; }
cd "$ROOT"
exec "$PY" -m cn_option_vix.pipeline.build_recent_5m \
  --days 1 \
  --asof "$1" \
  --force \
  --db "${CN_VIX_DB:-$ROOT/cn_option_vix/data/live_vix.sqlite}"
