"""SQLite storage shared by the live collector and dashboard API.

The database stores only already-computed VIX outputs. The numerical option-VIX
algorithm remains in ``cn_option_vix.core`` and is never reimplemented here.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from cn_option_vix.config import GROUPS, ROSTER

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PACKAGE_ROOT / "data" / "live_vix.sqlite"

VIX_COLUMNS = ["overall", *GROUPS.keys()]
SPREAD_COLUMNS = [f"spread_{gid}_overall" for gid in GROUPS]
DIAGNOSTIC_COLUMNS = [
    "n_instruments",
    "dq_flags",
    "expected_instruments",
    "missing_instruments",
    "valid_contracts",
    "missing_quotes",
    "provider_timestamp",
    "calculated_at",
    "quota_bytes_used",
]


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def initialise(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    column_specs = (
        [(name, "REAL") for name in [*VIX_COLUMNS, *SPREAD_COLUMNS]]
        + [
            ("n_instruments", "INTEGER"),
            ("dq_flags", "INTEGER"),
            ("expected_instruments", "INTEGER"),
            ("missing_instruments", "INTEGER"),
            ("valid_contracts", "INTEGER"),
            ("missing_quotes", "INTEGER"),
            ("provider_timestamp", "TEXT"),
            ("calculated_at", "TEXT"),
            ("quota_bytes_used", "INTEGER"),
        ]
    )
    columns = ",\n".join(f"{name} {spec}" for name, spec in column_specs)
    with connect(db_path) as conn:
        conn.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS vix_points (
                resolution TEXT NOT NULL CHECK (resolution IN ('5m', 'halfday')),
                timestamp TEXT NOT NULL,
                session TEXT,
                source TEXT NOT NULL,
                {columns},
                PRIMARY KEY (resolution, timestamp)
            );
            CREATE INDEX IF NOT EXISTS idx_vix_resolution_timestamp
                ON vix_points (resolution, timestamp);

            CREATE TABLE IF NOT EXISTS collector_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                level TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT
            );
            """
        )
        existing = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(vix_points)").fetchall()
        }
        for name, spec in column_specs:
            if name not in existing:
                conn.execute(f"ALTER TABLE vix_points ADD COLUMN {name} {spec}")


def _clean_number(value):
    if value is None or value is pd.NA:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if pd.notna(numeric) else None


def _timestamp_text(value) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("Asia/Shanghai").tz_localize(None)
    return ts.floor("s").strftime("%Y-%m-%d %H:%M:%S")


def normalise_point(
    row: Mapping,
    *,
    resolution: str,
    source: str,
    session: str | None = None,
) -> dict:
    if resolution not in {"5m", "halfday"}:
        raise ValueError(f"unsupported resolution: {resolution}")
    raw_timestamp = row.get("timestamp", row.get("date"))
    if raw_timestamp is None:
        raise ValueError("row has no timestamp/date")

    point = {
        "resolution": resolution,
        "timestamp": _timestamp_text(raw_timestamp),
        "session": session,
        "source": source,
        "calculated_at": _timestamp_text(
            row.get("calculated_at") or datetime.now()
        ),
    }
    for name in VIX_COLUMNS:
        point[name] = _clean_number(row.get(name))
    overall = point["overall"]
    for gid in GROUPS:
        name = f"spread_{gid}_overall"
        value = _clean_number(row.get(name))
        if value is None and point[gid] is not None and overall is not None:
            value = point[gid] - overall
        point[name] = value

    for name in (
        "n_instruments",
        "dq_flags",
        "expected_instruments",
        "missing_instruments",
        "valid_contracts",
        "missing_quotes",
        "quota_bytes_used",
    ):
        value = row.get(name)
        point[name] = int(value) if value is not None and pd.notna(value) else None
    provider_ts = row.get("provider_timestamp")
    point["provider_timestamp"] = (
        _timestamp_text(provider_ts) if provider_ts is not None and pd.notna(provider_ts) else None
    )
    return point


def upsert_points(
    rows: Iterable[Mapping],
    *,
    resolution: str,
    source: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    session_resolver=None,
) -> int:
    initialise(db_path)
    points = []
    for row in rows:
        session = session_resolver(row) if session_resolver else row.get("session")
        points.append(
            normalise_point(row, resolution=resolution, source=source, session=session)
        )
    if not points:
        return 0

    columns = [
        "resolution",
        "timestamp",
        "session",
        "source",
        *VIX_COLUMNS,
        *SPREAD_COLUMNS,
        "n_instruments",
        "dq_flags",
        "expected_instruments",
        "missing_instruments",
        "valid_contracts",
        "missing_quotes",
        "provider_timestamp",
        "calculated_at",
        "quota_bytes_used",
    ]
    placeholders = ",".join("?" for _ in columns)
    updates = ",".join(
        f"{c}=excluded.{c}" for c in columns if c not in {"resolution", "timestamp"}
    )
    sql = (
        f"INSERT INTO vix_points ({','.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(resolution,timestamp) DO UPDATE SET {updates}"
    )
    values = [[p.get(c) for c in columns] for p in points]
    with connect(db_path) as conn:
        conn.executemany(sql, values)
    return len(points)


def import_halfday_history(
    history_path: str | Path,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Import 11:30 and 15:00 points from an existing 30-minute output file."""
    path = Path(history_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path).reset_index()
    else:
        df = pd.read_csv(path)
    time_col = next(
        (c for c in ("timestamp", "datetime", "date", "index") if c in df.columns),
        None,
    )
    if time_col is None:
        raise ValueError(f"no timestamp column in {path}: {list(df.columns)}")
    df["timestamp"] = pd.to_datetime(df[time_col], errors="raise")
    df = df[df["timestamp"].dt.strftime("%H:%M").isin(["11:30", "15:00"])].copy()
    df["session"] = df["timestamp"].dt.strftime("%H:%M").map(
        {"11:30": "AM", "15:00": "PM"}
    )
    return upsert_points(
        df.to_dict("records"),
        resolution="halfday",
        source="historical_30m_close",
        db_path=db_path,
    )


def query_series(
    resolution: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    trading_days: int = 5,
    months: int | None = None,
    start_date: str | None = None,
) -> list[dict]:
    """Return dashboard points at the requested native resolution.

    Five-minute data is limited by distinct trading dates. Half-day data can be
    anchored to an explicit calendar start (used for the 2026 YTD monitor), or
    fall back to a rolling month window for backward compatibility.
    """
    initialise(db_path)
    with connect(db_path) as conn:
        if resolution == "5m":
            dates = conn.execute(
                """
                SELECT DISTINCT substr(timestamp, 1, 10) AS day
                FROM vix_points WHERE resolution='5m'
                ORDER BY day DESC LIMIT ?
                """,
                (int(trading_days),),
            ).fetchall()
            if not dates:
                return []
            start_day = min(row["day"] for row in dates)
            rows = conn.execute(
                """
                SELECT * FROM vix_points
                WHERE resolution='5m' AND timestamp >= ?
                ORDER BY timestamp
                """,
                (f"{start_day} 00:00:00",),
            ).fetchall()
        elif resolution == "halfday":
            latest = conn.execute(
                "SELECT max(timestamp) AS ts FROM vix_points WHERE resolution='halfday'"
            ).fetchone()["ts"]
            if latest is None:
                return []
            if start_date is not None:
                start = pd.Timestamp(start_date).strftime("%Y-%m-%d 00:00:00")
            elif months is not None:
                start = (pd.Timestamp(latest) - pd.DateOffset(months=int(months))).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                start = pd.Timestamp(latest).replace(month=1, day=1).strftime(
                    "%Y-%m-%d 00:00:00"
                )
            rows = conn.execute(
                """
                SELECT * FROM vix_points
                WHERE resolution='halfday' AND timestamp >= ?
                ORDER BY timestamp
                """,
                (start,),
            ).fetchall()
        else:
            raise ValueError(f"unsupported resolution: {resolution}")
    return [dict(row) for row in rows]


def moving_average_snapshot(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    windows: tuple[int, ...] = (30, 60),
) -> dict:
    """Compute trading-day averages for all six published VIX chains.

    One observation per trading date is used: the latest available half-day
    point for that date (normally 15:00, or 11:30 while the current session is
    still open). This avoids weighting every completed date twice.
    """
    initialise(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT timestamp, {','.join(VIX_COLUMNS)}
            FROM vix_points
            WHERE resolution='halfday'
            ORDER BY timestamp
            """
        ).fetchall()
    if not rows:
        return {
            "asof": None,
            "basis": "latest half-day observation per trading date",
            "available_trading_days": 0,
            "windows": list(windows),
            "rows": [],
        }

    frame = pd.DataFrame([dict(row) for row in rows])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    frame["trading_date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    daily = (
        frame.sort_values("timestamp")
        .groupby("trading_date", as_index=False, sort=True)
        .tail(1)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    latest_live = latest_by_resolution("5m", db_path)
    latest_halfday = daily.iloc[-1].to_dict()
    latest_source = latest_live or latest_halfday

    output_rows = []
    for name in VIX_COLUMNS:
        series = pd.to_numeric(daily[name], errors="coerce").dropna()
        latest_value = _clean_number(latest_source.get(name))
        if latest_value is None:
            latest_value = _clean_number(latest_halfday.get(name))
        item = {
            "key": name,
            "latest": latest_value,
        }
        for window in windows:
            sample = series.tail(int(window))
            avg = float(sample.mean()) if not sample.empty else None
            item[f"avg_{window}"] = avg
            item[f"count_{window}"] = int(sample.size)
            latest_value = item["latest"]
            item[f"vs_avg_{window}"] = (
                latest_value - avg
                if latest_value is not None and avg is not None
                else None
            )
        output_rows.append(item)

    return {
        "asof": (
            _timestamp_text(latest_source.get("timestamp"))
            if latest_source.get("timestamp") is not None
            else None
        ),
        "basis": "latest available half-day observation per trading date",
        "available_trading_days": int(len(daily)),
        "windows": list(windows),
        "rows": output_rows,
    }


def latest_by_resolution(
    resolution: str, db_path: str | Path = DEFAULT_DB_PATH
) -> dict | None:
    initialise(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM vix_points
            WHERE resolution=? ORDER BY timestamp DESC LIMIT 1
            """,
            (resolution,),
        ).fetchone()
    return dict(row) if row is not None else None


def previous_by_resolution(
    resolution: str, db_path: str | Path = DEFAULT_DB_PATH
) -> dict | None:
    initialise(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM vix_points
            WHERE resolution=? ORDER BY timestamp DESC LIMIT 1 OFFSET 1
            """,
            (resolution,),
        ).fetchone()
    return dict(row) if row is not None else None


def log_event(
    level: str,
    event: str,
    details: str | None = None,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    initialise(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO collector_events(event_time, level, event, details) VALUES (?,?,?,?)",
            (_timestamp_text(datetime.now()), level, event, details),
        )


def database_summary(db_path: str | Path = DEFAULT_DB_PATH) -> dict:
    initialise(db_path)
    with connect(db_path) as conn:
        counts = {
            row["resolution"]: row["n"]
            for row in conn.execute(
                "SELECT resolution, count(*) AS n FROM vix_points GROUP BY resolution"
            )
        }
        ranges = {
            row["resolution"]: {"first": row["first"], "last": row["last"]}
            for row in conn.execute(
                """
                SELECT resolution, min(timestamp) AS first, max(timestamp) AS last
                FROM vix_points GROUP BY resolution
                """
            )
        }
    return {
        "path": str(Path(db_path)),
        "counts": counts,
        "ranges": ranges,
        "expected_instruments": len(ROSTER),
    }
