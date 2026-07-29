#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="${1:-$ROOT/backups/$STAMP}"
mkdir -p "$DEST"

python3 - "$ROOT" "$DEST" <<'PY_BACKUP'
import sqlite3
import sys
from pathlib import Path
root=Path(sys.argv[1]); dest=Path(sys.argv[2])
for source, name in [
    (root/'jin10_us_dashboard_site/data/us_dashboard.db', 'us_dashboard.db'),
    (root/'cn_option_vix/data/live_vix.sqlite', 'live_vix.sqlite'),
]:
    target=dest/name
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    print(f'backed up {source} -> {target}')
PY_BACKUP

if [[ -f "$ROOT/.env" ]]; then
  cp -p "$ROOT/.env" "$DEST/.env"
  chmod 600 "$DEST/.env"
fi

echo "Backup complete: $DEST"
