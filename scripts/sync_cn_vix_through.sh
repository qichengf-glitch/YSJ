#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THROUGH="${1:-}"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
if [[ -z "${RQDATA_URI:-${RQDATAC_URI:-}}" ]]; then
  echo "RQDATA_URI is not configured in $ROOT/.env or the shell." >&2
  exit 2
fi
if [[ -n "${CN_VIX_PYTHON:-}" ]]; then
  PY="$CN_VIX_PYTHON"
elif [[ -x "$ROOT/cn_option_vix/.venv/bin/python" ]]; then
  PY="$ROOT/cn_option_vix/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "No Python interpreter found. Run ./scripts/setup_server.sh or activate the rqvix environment." >&2
  exit 2
fi
"$PY" - <<'PY_CHECK'
import rqdatac, pandas, pyarrow
PY_CHECK
cd "$ROOT"
ARGS=(
  -m cn_option_vix.pipeline.sync_missing_5m
  --db "${CN_VIX_DB:-$ROOT/cn_option_vix/data/live_vix.sqlite}"
  --reserve-mib "${CN_VIX_BACKFILL_RESERVE_MIB:-64}"
  --lookback-trading-days "${CN_VIX_CATCHUP_LOOKBACK_TRADING_DAYS:-10}"
)
if [[ -n "$THROUGH" ]]; then
  ARGS+=(--through "$THROUGH")
fi
exec "$PY" "${ARGS[@]}"
