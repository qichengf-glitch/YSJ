#!/usr/bin/env bash
set -euo pipefail

START_DATE="${1:-2024-07-13}"
END_DATE="${2:-2026-07-13}"
OUT_STEM="${3:-vix_30m_2y}"

python -m cn_option_vix.pipeline.build_history_30m \
  --start "$START_DATE" \
  --end "$END_DATE" \
  --out-stem "$OUT_STEM" \
  --probe-days 10 \
  --reserve-mib 64 \
  --safety-factor 1.15

STATUS=$(python - "$OUT_STEM" <<'PY'
import json
import sys
from pathlib import Path
stem = sys.argv[1]
p = Path("cn_option_vix/outputs") / f"{stem}_summary.json"
print(json.loads(p.read_text()).get("status", "unknown"))
PY
)

if [[ "$STATUS" != "complete" ]]; then
  echo "History build status is '$STATUS'; chart generation is deferred."
  echo "Inspect cn_option_vix/outputs/${OUT_STEM}_summary.json"
  exit 2
fi

python cn_option_vix/scripts/plot_vix_30m_roadshow.py \
  --input "cn_option_vix/outputs/${OUT_STEM}.csv" \
  --output-dir "cn_option_vix/outputs/roadshow_2y" \
  --language en
