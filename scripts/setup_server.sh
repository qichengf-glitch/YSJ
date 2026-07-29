#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$PYTHON_BIN"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  PYTHON_BIN="$(command -v python3)"
fi

"$PYTHON_BIN" - <<'PY_VERSION'
import sys
if not ((3, 10) <= sys.version_info[:2] <= (3, 12)):
    raise SystemExit(f"Python 3.10-3.12 required; found {sys.version.split()[0]}. Set PYTHON_BIN to a supported interpreter.")
print("Using", sys.version.split()[0])
PY_VERSION

cd "$ROOT"
echo "[1/3] Installing Next.js dependencies"
npm ci

echo "[2/3] Creating Jin10 Python environment"
"$PYTHON_BIN" -m venv "$ROOT/jin10_us_dashboard_site/.venv"
"$ROOT/jin10_us_dashboard_site/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/jin10_us_dashboard_site/.venv/bin/python" -m pip install -r "$ROOT/jin10_us_dashboard_site/requirements.txt"

echo "[3/3] Creating CN VIX Python environment"
"$PYTHON_BIN" -m venv "$ROOT/cn_option_vix/.venv"
"$ROOT/cn_option_vix/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/cn_option_vix/.venv/bin/python" -m pip install -r "$ROOT/cn_option_vix/requirements.txt"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created $ROOT/.env. Fill YSJ access credentials, JIN10_SECRET_KEY, and RQDATA_URI."
fi

echo "Validating backends and building the Next.js production bundle"
"$ROOT/scripts/validate_package.sh"

echo "Setup complete. Configure $ROOT/.env, then run: ./scripts/start_all.sh"
