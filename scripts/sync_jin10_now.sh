#!/usr/bin/env bash
set -euo pipefail
BASE="${MARKET_RADAR_DIRECT_URL:-http://127.0.0.1:8000}"

echo "Refreshing Jin10 default window and logs"
curl -fsS -X POST "$BASE/api/sync/default"; echo
curl -fsS -X POST "$BASE/api/sync/logs"; echo

echo "Refreshing Polymarket current quotes"
curl -fsS -X POST "$BASE/api/prediction-markets/sync?fetch_history=false"; echo

echo "Refreshing Whale snapshots"
curl -fsS -X POST "$BASE/api/prediction-markets/sync-whales"; echo
