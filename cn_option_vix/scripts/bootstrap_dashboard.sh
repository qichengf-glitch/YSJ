#!/usr/bin/env bash
set -euo pipefail
PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(dirname "$PACKAGE_DIR")"
cd "$WORKSPACE_DIR"

HISTORY_PATH="${1:-$PACKAGE_DIR/outputs/vix_30m_2y.csv}"
DB_PATH="${CN_VIX_DB:-$PACKAGE_DIR/data/live_vix.sqlite}"

python -m cn_option_vix.pipeline.bootstrap_dashboard \
  --history-30m "$HISTORY_PATH" \
  --db "$DB_PATH" \
  --days 5
