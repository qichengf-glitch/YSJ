# YSJ Prediction Market Backend

Standalone FastAPI service for the internal Prediction Market dashboard.

It owns the full Polymarket chain used by the internal dashboard:

- Polymarket Gamma event and market sync
- CLOB price-history snapshots
- 24h volume snapshot and spike detection
- tracked-wallet position and trade backfill
- rates/USD and geopolitical/commodity macro buckets

Calendar, earnings, holiday, and log-sync APIs are intentionally not included.
