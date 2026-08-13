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
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.OperationalError:
        pass
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            );

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
                volume_24h REAL,
                volume_spike_ratio REAL,
                volume_10d_avg REAL,
                volume_baseline_days INTEGER,
                volume_baseline_source TEXT,
                liquidity REAL,
                signal_type TEXT,
                signal_score REAL,
                asset_impact_json TEXT,
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
                errors_json TEXT
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
                raw_json TEXT,
                fetched_at TEXT NOT NULL,
                UNIQUE(condition_id, address, outcome, side, size, price, trade_ts)
            );
            """
        )
        for sql in [
            "ALTER TABLE pm_markets ADD COLUMN volume_24h REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_spike_ratio REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_10d_avg REAL",
            "ALTER TABLE pm_markets ADD COLUMN volume_baseline_days INTEGER",
            "ALTER TABLE pm_markets ADD COLUMN volume_baseline_source TEXT",
            "ALTER TABLE pm_whale_positions ADD COLUMN asset TEXT",
            "ALTER TABLE pm_whale_positions ADD COLUMN value REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN size REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN avg_price REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN cash_pnl REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN win_rate REAL",
            "ALTER TABLE pm_whale_positions ADD COLUMN wins INTEGER",
            "ALTER TABLE pm_whale_positions ADD COLUMN losses INTEGER",
            "ALTER TABLE pm_whale_positions ADD COLUMN raw_json TEXT",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass
        conn.executescript(
            """
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
            """
        )


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
