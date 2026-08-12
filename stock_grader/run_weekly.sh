#!/usr/bin/env bash
# Weekly cron: sentiment log + trigger scan. Add to crontab:
#   0 7 * * MON cd /path/to/stockgrader && ./run_weekly.sh >> data/cron.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"
python3 run.py --weekly
