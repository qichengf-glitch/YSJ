# CN Option VIX Live Dashboard — integrated final v4

- Source build: `20260716-pure-vix-relative-focus-v4`
- Direct backend: `http://127.0.0.1:8765/index.html`
- Authenticated website route: `/api/cn-option-vix-dashboard/index.html`
- Display: raw model-free VIX levels; no indexing or artificial scaling
- Main statistics: Current, 20D/60D relative spread, standard deviation and variance
- A-share sign convention: positive red, negative green

The VIX calculation, collector, database, caches and outputs are copied from the uploaded final package. Integration-only frontend path changes are documented in `INTEGRATION_NOTE.md`.

## Integrated start

From the `new-YSJ-main` root:

```bash
./scripts/setup_server.sh
# edit .env and set RQDATA_URI
./scripts/start_all.sh
./scripts/status_all.sh
```

If `RQDATA_URI` is absent, the unified launcher starts this service in web-only mode using the packaged SQLite database.

## Backfill a missed date

```bash
./scripts/backfill_cn_vix_day.sh 2026-07-17
```

## Canonical data

- Database: `cn_option_vix/data/live_vix.sqlite`
- Caches: `cn_option_vix/data/cache*`
- Exports: `cn_option_vix/outputs/`
- Original uploaded manifest: `cn_option_vix/SOURCE_FINAL_MANIFEST.json`

Snapshot supplied by the uploaded final package:

- database integrity: `ok`
- VIX points: `1271`
- latest 5m point: `2026-07-17 11:15:00`
- latest half-day point: `2026-07-16 15:00:00`
