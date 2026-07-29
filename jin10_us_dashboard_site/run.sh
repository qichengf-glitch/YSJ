#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env, then fill JIN10_SECRET_KEY"
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"

if [ "${DEV_RELOAD:-false}" = "true" ]; then
  exec "$PYTHON_BIN" -m uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --reload
else
  exec "$PYTHON_BIN" -m uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}"
fi
