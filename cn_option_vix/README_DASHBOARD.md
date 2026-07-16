# Dual-Time-Scale VIX Monitoring Dashboard

This extension adds a browser-based monitoring terminal without changing the
validated VIX mathematics in `core/` or the OI-weighted aggregation in
`aggregate/`.

## What the page shows

The page contains two synchronized monitoring modules:

1. **Latest five trading days — native 5-minute data**
   - Overall
   - Index VIX
   - Blue Chip
   - SZ Growth
   - Mid-Small
   - Hard Tech
   - Five separate group-minus-Overall spread panes

2. **Latest two months — half-day data**
   - AM point: 11:30
   - PM point: 15:00
   - The same six VIX series and five spread panes

The five spread panes share one symmetric vertical range, making spread
magnitudes directly comparable. Trading intervals are displayed with equal
horizontal spacing, so overnight, lunch, weekend, and holiday gaps do not create
long diagonal lines.

## Data consistency

All data paths call the existing numerical entry point:

```text
instrument_vix_from_snapshot
  -> compute_forward
  -> build_otm_series
  -> single_expiry_variance
  -> interpolate_to_target
  -> aggregate_variances
```

No VIX formula is duplicated in the dashboard.

Historical five-minute points use:

```text
price = RQData native 5m close
oi    = RQData native 5m open_interest
```

Live five-minute points use:

```text
price = current_snapshot.last
oi    = current_snapshot.open_interest
```

At 11:30 and 15:00, the same already-computed live row is inserted into the
half-day series. There is no second request and no cross-request timestamp drift.
All twelve instruments are calculated from one unioned logical snapshot.

## Installation

From the package directory:

```bash
cd /Users/qichengfu/Desktop/YSJ
source cn_option_vix_runtime/.venv/bin/activate
python -m pip install -r cn_option_vix/requirements.txt
```

Keep the RQData credential in the environment:

```bash
export RQDATA_URI='tcp://...'
```

## First-time bootstrap

Run from the `quant` workspace root or use the supplied script from anywhere:

```bash
bash /Users/qichengfu/Desktop/YSJ/cn_option_vix/scripts/bootstrap_dashboard.sh \
  /Users/qichengfu/Desktop/YSJ/cn_option_vix/outputs/vix_30m_2y.csv
```

This performs two steps:

1. imports all 11:30 and 15:00 observations from the existing 30-minute history;
2. downloads and computes the latest five trading days of native 5-minute data.

The five-minute backfill checkpoints each completed trading date. After the
first date, it measures real RQData usage and stops safely if the other dates
would breach the configured 64 MiB reserve. `Ctrl+C` is safe; rerunning reuses
completed caches and database points.

To import the two-month/half-day history without making any RQData call:

```bash
cd /Users/qichengfu/Desktop/YSJ
python -m cn_option_vix.pipeline.bootstrap_dashboard \
  --history-30m cn_option_vix/outputs/vix_30m_2y.csv \
  --skip-5m
```

## Start the live website

One command starts both the five-minute collector and the website:

```bash
cd /Users/qichengfu/Desktop/YSJ
bash cn_option_vix/scripts/run_live_dashboard.sh
```

Open:

```text
http://127.0.0.1:8765
```

The collector log is written to:

```text
cn_option_vix/outputs/dashboard_logs/collector_5m.log
```

Stopping the foreground command with `Ctrl+C` stops both processes cleanly. All
completed points have already been committed to SQLite and will be reused when
restarted.

To run only the webpage, without the collector:

```bash
cd /Users/qichengfu/Desktop/YSJ
bash cn_option_vix/scripts/run_dashboard_web.sh
```

## Test a single live point

Run only at a configured completed five-minute slot:

```bash
cd /Users/qichengfu/Desktop/YSJ
python -m cn_option_vix.pipeline.monitor_live_5m \
  --once \
  --timestamp '2026-07-15 14:35'
```

Without `--timestamp`, the command uses the current Shanghai time.

## Files

```text
cn_option_vix/data/live_vix.sqlite
cn_option_vix/data/cache_5m/
cn_option_vix/outputs/vix_5m_latest5.csv
cn_option_vix/outputs/vix_5m_latest5_audit.csv
cn_option_vix/outputs/vix_dashboard_5d_5m.csv
cn_option_vix/outputs/vix_dashboard_2m_halfday.csv
cn_option_vix/outputs/vix_5m_live_audit.csv
```

The SQLite database uses WAL mode and a composite `(resolution, timestamp)`
primary key. Repeated runs upsert the exact point instead of creating duplicates.

## API

```text
GET /api/config
GET /api/latest
GET /api/series?resolution=5m
GET /api/series?resolution=halfday
GET /api/status
GET /api/quality
GET /healthz
```

The browser polls every 20 seconds. It does not call RQData directly and does not
reset the user's zoom position on each poll.

## Render deployment

Create a separate Render Web Service for this dashboard.

Recommended Render settings:

```text
Runtime: Python 3
Root Directory: leave blank
Build Command: pip install -r cn_option_vix/requirements.txt
Start Command: bash cn_option_vix/scripts/run_render_dashboard.sh
```

Required environment variables:

```text
RQDATA_URI=<your RiceQuant URI>
CN_VIX_DB=/var/data/live_vix.sqlite
```

Optional environment variables:

```text
CN_VIX_BOOTSTRAP_ON_START=1
CN_VIX_LOG_DIR=/var/data/dashboard_logs
DASHBOARD_HOST=0.0.0.0
```

Attach a persistent disk:

```text
Mount Path: /var/data
```

The Render script imports `outputs/vix_30m_2y.csv` into the SQLite database the
first time `/var/data/live_vix.sqlite` is missing. It then starts the live
five-minute collector in the background and serves the FastAPI dashboard on
Render's assigned `$PORT`.

## UI interaction

- Click any metric card or legend pill to focus that index against Overall.
- Click the same item again, or click **Show all**, to restore all six lines.
- The crosshair tooltip displays all six VIX values and five spreads at one time.
- The Data Quality drawer shows instrument coverage, valid contracts, missing
  quotes, provider time, calculation time, and database ranges.
- Status changes between `LIVE`, `DELAYED`, `WAITING`, and `CLOSED`.

The page uses TradingView Lightweight Charts 5.2 through its official standalone
CDN build and includes TradingView attribution on the page.
