#!/usr/bin/env bash
set -euo pipefail

cd /Users/wonderfulren/Desktop/coding/quant
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rqvix

: "${RQDATA_URI:?Export RQDATA_URI before running this script}"

python -m cn_option_vix.pipeline.build_recent_30m --days 5
