# Stock Grader Website Integration

## Runtime Shape

Stock Grader is a batch pipeline, not a request-time web service. The website reads
the latest CSV report from:

```text
stock_grader/data/reports/full_scores_YYYYMMDD.csv
```

Set `STOCK_GRADER_REPORT_DIR` if reports should live on a Render persistent disk,
for example:

```text
STOCK_GRADER_DATA_DIR=/var/data/stock_grader
STOCK_GRADER_REPORT_DIR=/var/data/stock_grader/reports
```

The checked-in `full_scores_20260804.csv` is a seed report so the page has data
before the first production run. On Render, `scripts/render_start.sh` seeds that
report into the persistent report directory if no production report exists yet.

## Production Cadence

Render starts `stock_grader/scheduler.py` as a background process in the main Web
Service. By default it:

- runs a full refresh on service start unless today's report already exists;
- runs a full refresh every Monday at 07:00 America/New_York;
- writes `full_scores_YYYYMMDD.csv` to `STOCK_GRADER_REPORT_DIR`;
- logs to `STOCK_GRADER_LOG_DIR/stock_grader_scheduler.log`.

The production refresh command is:

```bash
cd stock_grader
python3 run.py --grade-all --force --no-llm
```

The LLM tier is disabled by default for scheduled runs because discretionary
categories are reviewed through the admin override layer. Set
`STOCK_GRADER_USE_LLM=true` and provide the relevant API key only if you want
scheduled Tier 3 extraction.

Useful scheduler variables:

```text
STOCK_GRADER_UPDATE_ON_START=true
STOCK_GRADER_SKIP_IF_REPORT_TODAY=true
STOCK_GRADER_SCHEDULER_TZ=America/New_York
STOCK_GRADER_WEEKLY_DAY=MON
STOCK_GRADER_WEEKLY_HOUR=7
STOCK_GRADER_WEEKLY_MINUTE=0
STOCK_GRADER_REFRESH_TIMEOUT_SECONDS=21600
```

The first production refresh can take longer than later runs because peer sets
and market-data caches are built from scratch on the persistent disk.

## Website Endpoints

```text
GET /stock-grader
GET /api/stock-grader/scores
GET /stock-grader/admin
```

The public dashboard and scores API require the existing `ysj_access` browser
session. The admin console requires that session plus a separate
`STOCK_GRADER_ADMIN_PASSCODE`.

## Admin Override Layer

The admin console only edits the discretionary categories:

```text
Business Quality
Income
Market Sentiment
Industry/Sector Tailwinds
```

Each `ticker + category` has exactly one active override record. Saving the same
pair updates that record. Deleting the card removes the override and the public
dashboard falls back to the system score and system marker.

Production variables:

```text
STOCK_GRADER_ADMIN_PASSCODE=<admin passcode>
STOCK_GRADER_ADMIN_SECRET=<long random secret>
STOCK_GRADER_OVERRIDE_PATH=/var/data/stock_grader/overrides.json
STOCK_GRADER_OVERRIDE_AUDIT_PATH=/var/data/stock_grader/override_audit.jsonl
```

If `STOCK_GRADER_DATA_DIR=/var/data/stock_grader` is set, the default override
paths already live there.

## Production Notes

- Install Python dependencies from `stock_grader/requirements.txt` before running jobs.
- Replace `settings.sec_user_agent` in `config/universe.yaml` with a team contact email.
- Keep generated cache, snapshots, peer files, and tier3 files on persistent storage.
- Do not run grading inside a page request; the job can take minutes and depends on external data sources.
