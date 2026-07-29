import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_conn():
    ensure_parent_dir(settings.database_path)
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def init_db() -> None:
    with get_conn() as conn:
        # WAL allows readers to keep serving the dashboard while a sync is committing.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS us_data_current (
                source_id INTEGER PRIMARY KEY,
                indicator_id INTEGER,
                company_name TEXT,
                ticker TEXT,
                exchange_name TEXT,
                measure TEXT,
                time_period TEXT,
                full_time_period TEXT,
                pub_time TEXT,
                actual TEXT,
                previous TEXT,
                consensus TEXT,
                revised TEXT,
                unit TEXT,
                star INTEGER,
                affect INTEGER,
                affect_status TEXT,
                time_status TEXT,
                title TEXT,
                stock_logo TEXT,
                ahead_url TEXT,
                is_deleted INTEGER DEFAULT 0,
                last_action TEXT,
                last_modify_time TEXT,
                first_seen_at TEXT,
                last_synced_at TEXT,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS us_event_current (
                source_id INTEGER PRIMARY KEY,
                event_time TEXT,
                event_content TEXT,
                country TEXT,
                determine INTEGER,
                note TEXT,
                people TEXT,
                region TEXT,
                star INTEGER,
                emergencies INTEGER,
                time_status TEXT,
                is_deleted INTEGER DEFAULT 0,
                last_action TEXT,
                last_modify_time TEXT,
                first_seen_at TEXT,
                last_synced_at TEXT,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS us_holiday_current (
                source_id INTEGER PRIMARY KEY,
                date TEXT,
                event_time TEXT,
                event_content TEXT,
                country TEXT,
                exchange_name TEXT,
                name TEXT,
                rest_note TEXT,
                determine INTEGER,
                note TEXT,
                people TEXT,
                region TEXT,
                star INTEGER,
                time_status TEXT,
                is_deleted INTEGER DEFAULT 0,
                last_action TEXT,
                last_modify_time TEXT,
                first_seen_at TEXT,
                last_synced_at TEXT,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_jin10_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                data_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                modify_time TEXT,
                raw_json TEXT NOT NULL,
                received_at TEXT NOT NULL,
                UNIQUE(category, source_type, log_id)
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_us_data_pub_time ON us_data_current(pub_time);
            CREATE INDEX IF NOT EXISTS idx_us_data_ticker ON us_data_current(ticker);
            CREATE INDEX IF NOT EXISTS idx_us_data_star ON us_data_current(star);
            CREATE INDEX IF NOT EXISTS idx_us_event_time ON us_event_current(event_time);
            CREATE INDEX IF NOT EXISTS idx_us_holiday_date ON us_holiday_current(date);
            CREATE TABLE IF NOT EXISTS price_bars (
                ticker TEXT NOT NULL,
                provider TEXT NOT NULL,
                interval TEXT NOT NULL,
                ts TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                raw_json TEXT,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (ticker, provider, interval, ts)
            );

            CREATE TABLE IF NOT EXISTS price_fetch_cache (
                ticker TEXT NOT NULL,
                provider TEXT NOT NULL,
                interval TEXT NOT NULL,
                range_key TEXT NOT NULL,
                last_fetched_at TEXT,
                status TEXT,
                error TEXT,
                PRIMARY KEY (ticker, provider, interval, range_key)
            );

            CREATE INDEX IF NOT EXISTS idx_raw_logs_modify_time ON raw_jin10_logs(modify_time);
            CREATE INDEX IF NOT EXISTS idx_price_bars_lookup ON price_bars(ticker, provider, interval, ts);

            CREATE TABLE IF NOT EXISTS pm_events (
                event_id TEXT PRIMARY KEY,
                title TEXT,
                source_category TEXT,
                tags_json TEXT,
                active INTEGER,
                closed INTEGER,
                volume REAL,
                liquidity REAL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pm_markets (
                condition_id TEXT PRIMARY KEY,
                event_id TEXT,
                token_id TEXT,
                bucket TEXT,
                bucket_reason TEXT,
                source_category TEXT,
                event_title TEXT,
                question TEXT,
                price_now REAL,
                price_7d_ago REAL,
                change_7d REAL,
                change_1d REAL,
                change_1mo REAL,
                bid REAL,
                ask REAL,
                spread REAL,
                volume_7d REAL,
                volume_total REAL,
                volume_24h REAL,
                volume_spike_ratio REAL,
                volume_10d_avg REAL,
                volume_baseline_days INTEGER,
                volume_baseline_source TEXT,
                liquidity REAL,
                signal_type TEXT,
                signal_score REAL,
                asset_impact_json TEXT,
                active INTEGER DEFAULT 1,
                closed INTEGER DEFAULT 0,
                last_seen_at TEXT,
                fetched_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pm_price_history (
                condition_id TEXT NOT NULL,
                token_id TEXT,
                ts TEXT NOT NULL,
                price REAL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (condition_id, ts)
            );

            CREATE TABLE IF NOT EXISTS pm_volume_history (
                condition_id TEXT NOT NULL,
                date TEXT NOT NULL,
                v24 REAL,
                question TEXT,
                bucket TEXT,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (condition_id, date)
            );

            CREATE TABLE IF NOT EXISTS pm_whale_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition_id TEXT NOT NULL,
                address TEXT NOT NULL,
                name TEXT,
                outcome TEXT,
                asset TEXT,
                value REAL,
                size REAL,
                avg_price REAL,
                cash_pnl REAL,
                win_rate REAL,
                wins INTEGER,
                losses INTEGER,
                fetched_at TEXT NOT NULL,
                raw_json TEXT
            );

            CREATE TABLE IF NOT EXISTS pm_whale_sync_runs (
                fetched_at TEXT PRIMARY KEY,
                wallet_count INTEGER,
                positions_saved INTEGER,
                errors_json TEXT,
                finished_at TEXT,
                status TEXT,
                trades_saved INTEGER DEFAULT 0,
                wallets_failed INTEGER DEFAULT 0,
                wallets_carried INTEGER DEFAULT 0,
                positions_carried INTEGER DEFAULT 0,
                wallet_set_hash TEXT
            );


            CREATE TABLE IF NOT EXISTS pm_whale_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition_id TEXT NOT NULL,
                address TEXT NOT NULL,
                name TEXT,
                outcome TEXT,
                side TEXT,
                size REAL,
                price REAL,
                usd REAL,
                trade_ts TEXT NOT NULL,
                transaction_hash TEXT,
                raw_json TEXT,
                fetched_at TEXT NOT NULL,
                UNIQUE(condition_id, address, outcome, side, size, price, trade_ts)
            );

            CREATE INDEX IF NOT EXISTS idx_pm_markets_bucket ON pm_markets(bucket);
            CREATE INDEX IF NOT EXISTS idx_pm_markets_signal ON pm_markets(signal_type, signal_score);
            CREATE INDEX IF NOT EXISTS idx_pm_markets_volume ON pm_markets(volume_7d);
            CREATE INDEX IF NOT EXISTS idx_pm_markets_v24 ON pm_markets(volume_24h);
            CREATE INDEX IF NOT EXISTS idx_pm_history_lookup ON pm_price_history(condition_id, ts);
            CREATE INDEX IF NOT EXISTS idx_pm_volume_history_lookup ON pm_volume_history(condition_id, date);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_latest ON pm_whale_positions(condition_id, fetched_at);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_wallet ON pm_whale_positions(address, condition_id, fetched_at);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_asset ON pm_whale_positions(address, asset, fetched_at);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_sync_runs ON pm_whale_sync_runs(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_trades_lookup ON pm_whale_trades(condition_id, address, trade_ts);
            CREATE INDEX IF NOT EXISTS idx_pm_whale_trades_time ON pm_whale_trades(trade_ts);

            CREATE TABLE IF NOT EXISTS sync_job_status (
                job TEXT PRIMARY KEY,
                started_at TEXT,
                finished_at TEXT,
                status TEXT,
                error TEXT,
                details_json TEXT
            );
            """
        )
        # Lightweight migrations for older local SQLite files.
        for sql in [
            "ALTER TABLE pm_markets ADD COLUMN volume_24h REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_spike_ratio REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_10d_avg REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_baseline_days INTEGER",
            "ALTER TABLE pm_markets ADD COLUMN volume_baseline_source TEXT",
            "ALTER TABLE pm_markets ADD COLUMN volume_total REAL",
            "ALTER TABLE pm_markets ADD COLUMN active INTEGER DEFAULT 1",
            "ALTER TABLE pm_markets ADD COLUMN closed INTEGER DEFAULT 0",
            "ALTER TABLE pm_markets ADD COLUMN last_seen_at TEXT",
            "ALTER TABLE pm_whale_positions ADD COLUMN size REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN avg_price REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN cash_pnl REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN raw_json TEXT",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN finished_at TEXT",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN status TEXT",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN trades_saved INTEGER DEFAULT 0",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN wallets_failed INTEGER DEFAULT 0",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN wallets_carried INTEGER DEFAULT 0",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN positions_carried INTEGER DEFAULT 0",
            "ALTER TABLE pm_whale_sync_runs ADD COLUMN wallet_set_hash TEXT",
            "ALTER TABLE pm_whale_trades ADD COLUMN transaction_hash TEXT",
        ]:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_markets_active ON pm_markets(active, closed, fetched_at)")


def update_job_status(job: str, status: str, *, started_at: Optional[str] = None, finished_at: Optional[str] = None, error: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sync_job_status(job, started_at, finished_at, status, error, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job) DO UPDATE SET
                started_at=COALESCE(excluded.started_at, sync_job_status.started_at),
                finished_at=COALESCE(excluded.finished_at, sync_job_status.finished_at),
                status=excluded.status,
                error=excluded.error,
                details_json=COALESCE(excluded.details_json, sync_job_status.details_json)
            """,
            (job, started_at, finished_at, status, error, json.dumps(details, ensure_ascii=False) if details is not None else None),
        )


def get_job_statuses() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM sync_job_status ORDER BY job").fetchall())


def get_state(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
        return None if row is None else row["value"]


def set_state(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sync_state(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, value, utc_now()),
        )


def record_log(category: str, source_type: str, log: Dict[str, Any]) -> bool:
    try:
        log_id = int(log.get("log_id"))
    except (TypeError, ValueError):
        return False
    raw_data_id = log.get("data_id") or (log.get("data") or {}).get("id")
    try:
        data_id = int(raw_data_id) if raw_data_id is not None else 0
    except (TypeError, ValueError):
        data_id = 0
    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO raw_jin10_logs(log_id, category, source_type, data_id, action, modify_time, raw_json, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id, category, source_type, data_id,
                    log.get("action") or "unknown",
                    log.get("modify_time"),
                    json.dumps(log, ensure_ascii=False),
                    utc_now(),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False
