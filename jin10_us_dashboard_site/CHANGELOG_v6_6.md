## v6.6.1 hotfix — 2026-07-17

- Removed the brittle `archived=false` parameter from the Gamma `/events` request.
- Added automatic HTTP 422 fallback: documented `volume_24hr` order → `volume24hr` order → minimal pagination with local 24h-volume sorting.
- Added Gamma response-body diagnostics for non-422 HTTP failures.
- Wrapped Prediction quote/history/whale scheduler jobs so failures are recorded without uncaught APScheduler tracebacks.
- Added regression coverage for the real 422 failure path.

# v6.6 Changelog

- Prediction quote refresh separated from historical price refresh and Whale sync.
- Fixed Gamma `/events` offset pagination and repeated-page detection.
- Replaced lifetime-volume-as-7D bug with `volume1wk` / CLOB+AMM weekly fields.
- Correctly maps YES outcome index to both price and token ID.
- Added active/closed lifecycle and rollback guards for empty/invalid upstream snapshots.
- Added retry/backoff HTTP sessions.
- Added WAL, busy timeout, explicit rollback and sync job status storage.
- Added `/api/health` and `/api/data-status`.
- Added incremental Whale trade backfill, real 24h trade activity and safe partial snapshots.
- Added Jin10 multi-page log catch-up.
- Fixed frontend cache, timezone parsing, partial endpoint failures and undefined variable.
- Production launcher no longer enables `--reload` by default.
- Added regression tests and environment template.
- Added page-cap completeness detection so truncated event snapshots never deactivate unseen valid markets.
- Whale daily grouping now uses dashboard local-day boundaries; explicit failed partial runs cannot override valid legacy snapshots.
- Jin10 raw log persistence now falls back to nested `data.id`; delete records inherit the resolved ID.
- SQLite migrations only ignore expected duplicate-column errors and surface real migration failures.
- Gamma event parsing accepts both the documented array form and an `events`/`has_more` response envelope.

- Added exact wallet-set hashing and safe per-wallet carry-forward so one temporary positions failure does not freeze all fresh Whale data or look like a liquidation.
- Prediction volume snapshots now use the configured dashboard local date rather than UTC day boundaries.
- Rejects malformed markets without an explicit YES outcome instead of guessing outcome index 0.
- Handles string boolean fields defensively and fails loudly when an entire sync yields zero valid markets.
- Jin10 malformed logs with missing/invalid data IDs are retained and no longer pin the incremental cursor.
