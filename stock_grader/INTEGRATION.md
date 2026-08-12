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
before the first production run.

## Suggested Cadence

Weekly trigger scan:

```bash
cd stock_grader
python3 run.py --weekly
```

Post-earnings or monthly/quarterly scoring:

```bash
cd stock_grader
python3 run.py --grade-all
python3 run.py --report
```

Full refresh:

```bash
cd stock_grader
python3 run.py --grade-all --force
```

## Website Endpoints

```text
GET /stock-grader
GET /api/stock-grader/scores
```

Both require the existing `ysj_access` browser session.

## Production Notes

- Install Python dependencies from `stock_grader/requirements.txt` before running jobs.
- Replace `settings.sec_user_agent` in `config/universe.yaml` with a team contact email.
- Keep generated cache, snapshots, peer files, and tier3 files on persistent storage.
- Do not run grading inside a page request; the job can take minutes and depends on external data sources.
