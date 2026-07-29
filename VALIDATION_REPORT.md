# Validation report — CN VIX automatic update repair

Generated on July 23, 2026.

## Root cause confirmed

The packaged SQLite snapshot is genuinely stale; this is not a browser-cache issue:

- Latest 5-minute point: `2026-07-17 11:15:00`
- Latest half-day point: `2026-07-16 15:00:00`
- Latest collector event: successful point at `2026-07-17 11:15:00`
- Earlier logs contain intermittent RQData `login machine num exceeds` errors.

The old service had two operational gaps:

1. It collected automatically only while the process remained alive with a valid `RQDATA_URI`; downtime was not repaired automatically.
2. The collector was a background child of the web process. If the collector exited, the dashboard could remain reachable and look healthy while data stopped updating.

## Changes validated

- Startup catch-up scans published SQLite points and repairs incomplete trading dates.
- The current trading date is repaired only through already-completed 5-minute slots.
- Historical repairs use native RQData 5-minute `close` and `open_interest`; no interpolation or fabricated rows are allowed.
- 11:30 and 15:00 repaired rows also update the half-day series.
- Scheduled reconciliation runs at 08:50 and 15:20 Asia/Shanghai.
- Web, live collector, and repair scheduler are independently supervised and restarted.
- A cross-process RQData lock prevents concurrent live/backfill sessions.
- A live point delayed more than 90 seconds after waiting for the lock is rejected and left for historical repair, preventing a later quote from being written under an earlier timestamp.
- The systemd VIX service now uses `Restart=always`.
- `scripts/status_all.sh` displays `last_5m`, `last_halfday`, feed state, quality, and latest collector event.

## Checks completed

- Python compilation: passed for all new and modified VIX modules.
- Shell syntax: passed for the live supervisor, manual sync, status, and launcher scripts.
- Automatic-update test subset: 33 tests passed.
- Supervisor smoke test: VIX web process started and `/healthz` returned HTTP 200 using the packaged SQLite database.
- SQLite integrity: `ok`.
- No synthetic July 18–23 observations were inserted.

## Environment limitation

This execution environment does not contain the user's RQData credential, `rqdatac`, or `pyarrow`, so it cannot download the real July 20–23 option bars. The data pull must run on the credentialed server:

```bash
cd /path/to/new-YSJ-main-vix-auto
./scripts/sync_cn_vix_through.sh 2026-07-23
sudo systemctl restart ysj-vix
./scripts/status_all.sh
```

After the July 23 market close, successful completion should show:

```text
last_5m=2026-07-23 15:00:00
last_halfday=2026-07-23 15:00:00
```

During market hours, `last_5m` should be the latest completed five-minute slot, and the PM half-day row will not exist until 15:00.
