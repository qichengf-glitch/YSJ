#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  PYTHON_BIN="$(command -v python3)"
fi

"$PYTHON_BIN" - <<'PY_VERSION'
import sys
if not ((3, 10) <= sys.version_info[:2] <= (3, 12)):
    raise SystemExit(
        f"Python 3.10-3.12 required; found {sys.version.split()[0]}. "
        "Set PYTHON_VERSION=3.11.9 on Render."
    )
print("Using Python", sys.version.split()[0])
PY_VERSION

npm ci

PREDICTION_MARKET_DIR="$ROOT/prediction_market_backend"
if [[ -d "$PREDICTION_MARKET_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$PREDICTION_MARKET_DIR/.venv"
  "$PREDICTION_MARKET_DIR/.venv/bin/python" -m pip install --upgrade pip
  "$PREDICTION_MARKET_DIR/.venv/bin/python" -m pip install -r "$PREDICTION_MARKET_DIR/requirements.txt"
else
  echo "No prediction_market_backend directory found; skipping Prediction Market Python install."
fi

if [[ -d "$ROOT/cn_option_vix" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT/cn_option_vix/.venv"
  "$ROOT/cn_option_vix/.venv/bin/python" -m pip install --upgrade pip
  "$ROOT/cn_option_vix/.venv/bin/python" -m pip install -r "$ROOT/cn_option_vix/requirements.txt"
else
  echo "No cn_option_vix directory found; skipping CN VIX Python install."
fi

if [[ -d "$ROOT/stock_grader" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT/stock_grader/.venv"
  "$ROOT/stock_grader/.venv/bin/python" -m pip install --upgrade pip
  "$ROOT/stock_grader/.venv/bin/python" -m pip install -r "$ROOT/stock_grader/requirements.txt"
else
  echo "No stock_grader directory found; skipping Stock Grader Python install."
fi

npm run build
