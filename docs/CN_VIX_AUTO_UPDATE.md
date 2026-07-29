# CN Option VIX automatic update chain

## Actual update behavior

The dashboard is not updated by the browser. The Python collector must be running on the server with a valid `RQDATA_URI`.

The repaired chain now has three safeguards:

1. **Startup catch-up**: before live collection starts, SQLite is inspected and every incomplete trading date is rebuilt from native RQData 5-minute bars.
2. **Live collection**: one synchronized option-chain snapshot is collected at every completed 5-minute market slot. The 11:30 and 15:00 points are also written to the half-day series.
3. **Scheduled reconciliation**: at 08:50 and 15:20 Shanghai time, missing completed points are checked and repaired. Collector, repair worker, and web server are independently restarted if they exit.

All RQData workflows share `CN_VIX_RQ_LOCK`, preventing overlapping downloads or duplicate account sessions.

## Fill through July 23, 2026

Run on the server that has the RQData credential:

```bash
cd /path/to/new-YSJ-main-vix-auto
./scripts/sync_cn_vix_through.sh 2026-07-23
sudo systemctl restart ysj-vix
./scripts/status_all.sh
```

Expected final status after the market close:

- `last_5m=2026-07-23 15:00:00`
- `last_halfday=2026-07-23 15:00:00`

During the trading session, `last_5m` should equal the most recently completed five-minute slot; the 15:00 point cannot exist before market close.

## Failure diagnosis

```bash
sudo systemctl status ysj-vix --no-pager
sudo journalctl -u ysj-vix -n 200 --no-pager
tail -n 200 cn_option_vix/outputs/dashboard_logs/collector_5m.log
tail -n 200 cn_option_vix/outputs/dashboard_logs/repair.log
```

`login machine num exceeds` is an RQData account/session limit, not a VIX algorithm error. Stop other machines or processes using the same RQData account, then restart `ysj-vix`.
