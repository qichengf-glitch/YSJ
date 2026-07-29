# Integration note

The CN VIX calculation, collector, database, caches, outputs, and API logic are copied from the uploaded final v4 package.

Two frontend-only changes were made for server integration:

1. dashboard CSS/JS asset URLs are relative so the page works both directly on port 8765 and behind the Next.js route;
2. browser API requests automatically use `/api/cn-option-vix-dashboard` when embedded by YSJ.

`SOURCE_FINAL_MANIFEST.json` is the original uploaded manifest and therefore records the pre-integration hashes of those static files.

## July 23 automatic-update repair

The integrated v5 service adds startup catch-up, 08:50/15:20 scheduled reconciliation, independent worker supervision, and a cross-process RQData lock. `scripts/sync_cn_vix_through.sh YYYY-MM-DD` repairs all incomplete published five-minute slots through the requested trading date. Static source provenance remains recorded in `SOURCE_FINAL_MANIFEST.json`.
