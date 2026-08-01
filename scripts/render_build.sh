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

JIN10_DIR=""
if [[ -d "$ROOT/jin10_us_dashboard_site" ]]; then
  JIN10_DIR="$ROOT/jin10_us_dashboard_site"
elif [[ -d "$ROOT/jin10_us_dashboard_site_v6_5" ]]; then
  JIN10_DIR="$ROOT/jin10_us_dashboard_site_v6_5"
fi

if [[ -n "$JIN10_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$JIN10_DIR/.venv"
  "$JIN10_DIR/.venv/bin/python" -m pip install --upgrade pip
  "$JIN10_DIR/.venv/bin/python" -m pip install -r "$JIN10_DIR/requirements.txt"
else
  echo "No Jin10 backend directory found; skipping Jin10 Python install."
fi

if [[ -d "$ROOT/cn_option_vix" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT/cn_option_vix/.venv"
  "$ROOT/cn_option_vix/.venv/bin/python" -m pip install --upgrade pip
  "$ROOT/cn_option_vix/.venv/bin/python" -m pip install -r "$ROOT/cn_option_vix/requirements.txt"
else
  echo "No cn_option_vix directory found; skipping CN VIX Python install."
fi

npm run build
