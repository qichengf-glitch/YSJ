Replace `__YSJ_ROOT__` and `__YSJ_USER__`, copy the three unit files to `/etc/systemd/system/`, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ysj-jin10 ysj-vix ysj-web
sudo systemctl status ysj-jin10 ysj-vix ysj-web
```

Build the Next.js app and create both Python virtual environments before enabling the units.

The `ysj-vix` unit runs the v5 supervisor. With `RQDATA_URI` configured in the project `.env`, it starts the dashboard, performs startup catch-up, supervises the five-minute collector, and runs the 08:50/15:20 reconciliation worker. Verify freshness with:

```bash
./scripts/status_all.sh
sudo journalctl -u ysj-vix -n 200 --no-pager
```
