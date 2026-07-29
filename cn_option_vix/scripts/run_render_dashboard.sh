#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
cd "$WORKSPACE_DIR"

export PYTHONUNBUFFERED=1
export CN_VIX_DB="${CN_VIX_DB:-/var/data/live_vix.sqlite}"
export DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
export DASHBOARD_PORT="${DASHBOARD_PORT:-${PORT:-8765}}"
export CN_VIX_LOG_DIR="${CN_VIX_LOG_DIR:-/var/data/dashboard_logs}"
HISTORY_PATH="${CN_VIX_HISTORY_30M:-$PACKAGE_DIR/outputs/vix_30m_2y.csv}"

mkdir -p "$(dirname "$CN_VIX_DB")" "$CN_VIX_LOG_DIR"

if [[ "${CN_VIX_BOOTSTRAP_ON_START:-1}" = "1" && ! -f "$CN_VIX_DB" && -f "$HISTORY_PATH" ]]; then
  echo "bootstrapping CN VIX dashboard database from $HISTORY_PATH"
  python -m cn_option_vix.pipeline.bootstrap_dashboard \
    --history-30m "$HISTORY_PATH" \
    --db "$CN_VIX_DB" \
    --skip-5m
fi

exec bash "$PACKAGE_DIR/scripts/run_live_dashboard.sh"
