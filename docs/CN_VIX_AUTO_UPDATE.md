# CN Option VIX automatic update chain

## Actual update behavior

The dashboard is not updated by the browser. The Python collector must be running on the server with a valid `RQDATA_URI`.

The repaired chain now has four safeguards:

1. **Packaged history seed**: when the persistent database does not contain the full packaged two-year half-day history, that history is imported before the services start. A consistent SQLite backup is created first.
2. **Startup catch-up**: before live collection starts, SQLite is inspected and every incomplete trading date in at least the latest 18-trading-day window is rebuilt from native RQData 5-minute bars.
3. **Live collection**: one synchronized option-chain snapshot is collected at every completed 5-minute market slot. The 11:30 and 15:00 points are also written to the half-day series.
4. **Scheduled reconciliation**: at 08:50 and 15:20 Shanghai time, missing completed points are checked and repaired. Collector, repair worker, and web server are independently restarted if they exit.

All RQData workflows share `CN_VIX_RQ_LOCK`, preventing overlapping downloads or duplicate account sessions.

## Render configuration

The Render web service must use:

- Build command: `./scripts/setup_server.sh`
- Start command: `./scripts/render_start.sh`
- Persistent disk mounted at `/var/data`
- `RQDATA_URI`: the RiceQuant TCP URI, without extra quote characters
- `CN_VIX_AUTO_BACKFILL=1`
- `CN_VIX_REPAIR_TIMES=08:50,15:20`

Optional history controls:

- `CN_VIX_SEED_HISTORY_ON_START=1`
- `CN_VIX_HISTORY_30M=/path/to/vix_30m_2y.csv`
- `CN_VIX_MIN_CATCHUP_LOOKBACK_TRADING_DAYS=18`

`scripts/render_start.sh` stores SQLite, logs, and the RQData process lock under
`/var/data`. If the persistent VIX database exists but contains no points, it is
first seeded from the packaged snapshot and then repaired from RQData.

## Manual catch-up

Run this inside a server shell that has the RQData credential:

```bash
python -m cn_option_vix.pipeline.sync_missing_5m \
  --db /var/data/live_vix.sqlite \
  --through 2026-07-23 \
  --lookback-trading-days 10 \
  --reserve-mib 64
```

Expected final status after the market close:

- `last_5m=2026-07-23 15:00:00`
- `last_halfday=2026-07-23 15:00:00`

During the trading session, `last_5m` should equal the most recently completed five-minute slot; the 15:00 point cannot exist before market close.

## Failure diagnosis

```bash
curl -s http://127.0.0.1:8765/api/status
tail -n 200 /var/data/dashboard_logs/collector_5m.log
tail -n 200 /var/data/dashboard_logs/repair.log
tail -n 200 /var/data/dashboard_logs/web.log
```

`login machine num exceeds` is an RQData account/session limit, not a VIX algorithm error. Stop other machines or processes using the same RQData account, then restart `ysj-vix`.
