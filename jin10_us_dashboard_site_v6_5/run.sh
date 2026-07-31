#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "Missing .env. Please run: cp .env.example .env and fill JIN10_SECRET_KEY"
  exit 1
fi
PYTHON_BIN="${PYTHON_BIN:-python}"
exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
