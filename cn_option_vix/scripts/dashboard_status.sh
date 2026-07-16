#!/usr/bin/env bash
set -euo pipefail
PORT="${DASHBOARD_PORT:-8765}"
curl -fsS "http://127.0.0.1:$PORT/api/status" | python -m json.tool
