# new-YSJ-main deployment

## Runtime topology

```text
Browser
  -> :3000 Next.js (access cookie + pages)
       -> /api/market-radar/*            -> 127.0.0.1:8000 Jin10 FastAPI
       -> /api/cn-option-vix-dashboard/* -> 127.0.0.1:8765 CN VIX FastAPI

Jin10 scheduler -> Jin10 / Polymarket upstreams -> jin10_us_dashboard_site/data/us_dashboard.db
CN VIX collector -> RQData -> cn_option_vix/data/live_vix.sqlite
```

Only Next.js should be exposed publicly. Ports 8000 and 8765 remain bound to loopback. Both proxy routes require the same authenticated `ysj_access` cookie as their pages.

## First deployment

```bash
unzip new-YSJ-main-vix-auto.zip
cd new-YSJ-main-vix-auto
./scripts/setup_server.sh
nano .env
./scripts/start_all.sh
./scripts/status_all.sh
```

Required production values:

- `YSJ_ACCESS_PASSCODE`: private website login code.
- `YSJ_ACCESS_SECRET`: long random token-signing secret.
- `JIN10_SECRET_KEY`: Jin10 API credential.
- `RQDATA_URI`: RQData credential URI. Without it, VIX starts in web-only mode using packaged data.
- Python 3.11 is recommended; the setup script accepts Python 3.10-3.12.

The uploaded Jin10 `.env` was intentionally not copied into this package. Secrets must be configured on the server.

## Data migration and persistence

The package retains both uploaded SQLite databases:

- `jin10_us_dashboard_site/data/us_dashboard.db`
- `cn_option_vix/data/live_vix.sqlite`

Back these up before replacing a running release. During future code-only upgrades, preserve both database files and the server `.env`.

Do not commit runtime SQLite databases to a public GitHub repository. GitHub rejects files over 100 MB, and the Jin10 database is expected to live on the server's persistent disk. Push code, scripts, and static assets through GitHub; migrate or back up the database directly on the deployment server.

## Lifecycle

```bash
./scripts/start_all.sh
./scripts/status_all.sh
./scripts/stop_all.sh
./scripts/validate_package.sh
./scripts/sync_jin10_now.sh
./scripts/backfill_cn_vix_day.sh YYYY-MM-DD
./scripts/sync_cn_vix_through.sh YYYY-MM-DD
./scripts/backup_data.sh
```

Logs are written under `logs/`; PID files are under `run/`. `backup_data.sh` uses SQLite's online backup API and stores a permission-restricted copy of `.env`; keep the backup directory private.

## Reverse proxy

`deploy/nginx/ysj.conf.example` proxies only to Next.js on port 3000. Next.js performs authenticated internal routing to both Python services.

## Production process manager

For automatic restart after reboot, use the templates in `deploy/systemd/`. Replace `__YSJ_ROOT__` with the absolute project path and `__YSJ_USER__` with the service account before installing them.

## Health checks

- Jin10 direct: `http://127.0.0.1:8000/api/health`
- CN VIX direct: `http://127.0.0.1:8765/healthz`
- Authenticated aggregate: `/api/services/health`

## Service behavior

- Jin10 v6.6.1 runs current quotes, history, whales, Jin10 logs, and full-window sync as independent scheduler jobs.
- CN VIX web reads SQLite only. RQData credentials are used by the collector, never by the browser or Next.js.
- With `RQDATA_URI` configured, CN VIX automatically catches up incomplete dates at startup, collects completed 5-minute slots, reconciles at 08:50 and 15:20 Shanghai time, and restarts failed workers.
- See `docs/CN_VIX_AUTO_UPDATE.md` for the July 23 catch-up command and diagnostics.
- Both dashboards disable browser caching for live data.
