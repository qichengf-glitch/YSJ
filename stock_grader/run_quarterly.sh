#!/usr/bin/env bash
# Post-earnings: grade everything the triggers queue, then emit the update sheet.
set -euo pipefail
cd "$(dirname "$0")"
python3 run.py --grade-all
python3 run.py --report
