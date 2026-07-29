#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/run"

for name in jin10 cn_vix ysj_web; do
  pid_file="$RUN_DIR/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name: RUNNING pid=$(cat "$pid_file")"
  else
    echo "$name: STOPPED (manual PID mode; systemd may still be active)"
  fi
done

echo
printf 'Jin10 health: '
curl -fsS --max-time 3 http://127.0.0.1:8000/api/health || true
echo
printf 'CN VIX database health: '
curl -fsS --max-time 3 http://127.0.0.1:8765/healthz || true
echo
printf 'CN VIX feed status: '
STATUS="$(curl -fsS --max-time 3 http://127.0.0.1:8765/api/status 2>/dev/null || true)"
if [[ -n "$STATUS" ]]; then
  STATUS_JSON="$STATUS" python - <<'PY'
import json, os
try:
    p=json.loads(os.environ['STATUS_JSON'])
    print(
        f"state={p.get('state')} quality={p.get('quality')} "
        f"last_5m={p.get('last_5m')} last_halfday={p.get('last_halfday')} "
        f"event={((p.get('last_collector_event') or {}).get('event'))}"
    )
except Exception as exc:
    print(f"invalid status response: {exc}")
PY
else
  echo "UNREACHABLE"
fi
printf 'Next.js: '
curl -fsSI --max-time 3 http://127.0.0.1:3000/ | head -n 1 || true
