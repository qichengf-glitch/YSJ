#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m compileall -q jin10_us_dashboard_site/app cn_option_vix
node --check public/market-radar/app.js
node --check cn_option_vix/web/static/app.js
bash -n scripts/*.sh cn_option_vix/scripts/*.sh
for required in \
  cn_option_vix/pipeline/sync_missing_5m.py \
  cn_option_vix/pipeline/monitor_repair.py \
  cn_option_vix/data/rq_process_lock.py \
  scripts/sync_cn_vix_through.sh; do
  [[ -f "$required" ]] || { echo "Missing $required" >&2; exit 1; }
done

python3 - <<'PY_DB'
import sqlite3
from pathlib import Path
for path in [
    Path('jin10_us_dashboard_site/data/us_dashboard.db'),
    Path('cn_option_vix/data/live_vix.sqlite'),
]:
    with sqlite3.connect(path) as conn:
        result = conn.execute('pragma integrity_check').fetchone()[0]
    if result != 'ok':
        raise SystemExit(f'{path}: integrity_check={result}')
    print(f'{path}: integrity ok')
PY_DB

if [[ -x jin10_us_dashboard_site/.venv/bin/python ]]; then
  (
    cd jin10_us_dashboard_site
    .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
  )
else
  echo "Jin10 virtualenv missing; skipping its unit tests."
fi

if [[ -x cn_option_vix/.venv/bin/python ]]; then
  (
    export PYTHONPATH="$ROOT"
    cn_option_vix/.venv/bin/python -m pytest -q cn_option_vix/tests
  )
else
  echo "CN VIX virtualenv missing; skipping its pytest suite."
fi

if [[ -d node_modules ]]; then
  npm run build
else
  echo "node_modules missing; skipping Next build. Run ./scripts/setup_server.sh first."
fi

echo "Package validation passed."
