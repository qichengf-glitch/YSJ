# Dashboard YTD + Moving Averages Upgrade

This patch changes only the dashboard query, API, and presentation layer. It does not change the option-VIX calculation, 30-day interpolation, OI weighting, or live RQData collection schedule.

## Changes

- Replaces the rolling two-month half-day panel with 2026 year-to-date half-day history, beginning at the first stored trading observation on or after 2026-01-01.
- Adds a six-row 30/60 trading-day average table.
  - One point per trading date is used: the latest available half-day observation, normally 15:00 (or 11:30 before the PM point exists).
  - The latest column uses the live 5-minute value when available.
- Adds two main-chart display modes:
  - `VIX level`: exact VIX values.
  - `Indexed 100`: each chain is rebased to 100 at the first loaded point, while tooltips and cards continue to show exact VIX values.
- Clicking a metric card or legend pill now truly isolates Overall plus the selected chain. Hidden chains no longer influence the vertical autoscale, producing the tighter roadshow-style comparison requested.
- Raw samples are preserved: all native 5-minute points and all AM/PM half-day points are shown. There is no interpolation or smoothing.

## Install

From the directory containing `cn_option_vix`:

```bash
unzip -o ~/Downloads/cn_option_vix_dashboard_ytd_patch.zip
```

Restart the dashboard:

```bash
cd /Users/wonderfulren/Desktop/coding/quant
conda activate rqvix
export RQDATA_URI='tcp://YOUR_URI'
bash cn_option_vix/scripts/run_live_dashboard.sh
```

Then hard-refresh the browser with `Command + Shift + R`.

No bootstrap or RQData re-download is required if the existing SQLite database was originally seeded from the full two-year 30-minute file. The half-day table already contains the history; this patch changes the query window to 2026 YTD.
