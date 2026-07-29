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
PUBLISHED_POINT_SQL = "(" + " AND ".join(
    [f"{name} IS NOT NULL" for name in VIX_COLUMNS]
    + ["(expected_instruments IS NULL OR n_instruments >= expected_instruments)"]
) + ")"


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
    columns = ",\n".join(
        [f"{name} REAL" for name in [*VIX_COLUMNS, *SPREAD_COLUMNS]]
        + [
            "n_instruments INTEGER",
            "dq_flags INTEGER",
            "expected_instruments INTEGER",
            "missing_instruments INTEGER",
            "valid_contracts INTEGER",
            "missing_quotes INTEGER",
            "provider_timestamp TEXT",
            "calculated_at TEXT NOT NULL",
            "quota_bytes_used INTEGER",
        ]
    )
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
                f"""
                SELECT DISTINCT substr(timestamp, 1, 10) AS day
                FROM vix_points WHERE resolution='5m'
                  AND {PUBLISHED_POINT_SQL}
                ORDER BY day DESC LIMIT ?
                """,
                (int(trading_days),),
            ).fetchall()
            if not dates:
                return []
            start_day = min(row["day"] for row in dates)
            rows = conn.execute(
                f"""
                SELECT * FROM vix_points
                WHERE resolution='5m' AND timestamp >= ?
                  AND {PUBLISHED_POINT_SQL}
                ORDER BY timestamp
                """,
                (f"{start_day} 00:00:00",),
            ).fetchall()
        elif resolution == "halfday":
            latest = conn.execute(
                f"SELECT max(timestamp) AS ts FROM vix_points WHERE resolution='halfday' AND {PUBLISHED_POINT_SQL}"
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
                f"""
                SELECT * FROM vix_points
                WHERE resolution='halfday' AND timestamp >= ?
                  AND {PUBLISHED_POINT_SQL}
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
    windows: tuple[int, ...] = (20, 60),
) -> dict:
    """Compute VIX-level and relative-spread statistics for the dashboard.

    The option-VIX calculation itself is untouched. This function only performs
    post-processing on already-published VIX outputs:

    * one observation per trading date: the latest available half-day point;
    * relative spread for group ``g``: ``VIX_g - VIX_overall`` at the same point;
    * sample standard deviation and variance use ``ddof=1``;
    * the current values use the latest complete five-minute observation.
    """
    initialise(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT timestamp, {','.join(VIX_COLUMNS)}
            FROM vix_points
            WHERE resolution='halfday' AND {PUBLISHED_POINT_SQL}
            ORDER BY timestamp
            """
        ).fetchall()

    empty_payload = {
        "asof": None,
        "basis": "latest half-day observation per trading date",
        "latest_basis": "latest complete five-minute observation",
        "variance_method": "sample variance (ddof=1)",
        "variance_unit": "VIX points squared",
        "spread_definition": "sector VIX minus Overall VIX at the same timestamp",
        "spread_standard_deviation_unit": "VIX points",
        "spread_variance_unit": "VIX points squared",
        "available_trading_days": 0,
        "windows": list(windows),
        "rows": [],
    }
    if not rows:
        return empty_payload

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

    latest_live = latest_by_resolution("5m", db_path, published_only=True)
    latest_halfday = daily.iloc[-1].to_dict()
    latest_source = latest_live or latest_halfday

    overall_daily = pd.to_numeric(daily["overall"], errors="coerce")
    output_rows = []
    for name in VIX_COLUMNS:
        level_series = pd.to_numeric(daily[name], errors="coerce")
        latest_value = _clean_number(latest_source.get(name))
        if latest_value is None:
            latest_value = _clean_number(latest_halfday.get(name))

        latest_spread = None
        spread_series = None
        if name != "overall":
            spread_key = f"spread_{name}_overall"
            latest_spread = _clean_number(latest_source.get(spread_key))
            if latest_spread is None:
                latest_overall = _clean_number(latest_source.get("overall"))
                if latest_value is not None and latest_overall is not None:
                    latest_spread = latest_value - latest_overall
            spread_series = level_series - overall_daily

        item = {
            "key": name,
            "latest": latest_value,
            "latest_spread": latest_spread,
        }

        for window in windows:
            window = int(window)
            daily_window = daily.tail(window)

            level_sample = pd.to_numeric(
                daily_window[name], errors="coerce"
            ).dropna()
            avg = float(level_sample.mean()) if not level_sample.empty else None
            variance = (
                float(level_sample.var(ddof=1)) if level_sample.size >= 2 else None
            )
            item[f"avg_{window}"] = avg
            item[f"variance_{window}"] = variance
            item[f"count_{window}"] = int(level_sample.size)
            item[f"vs_avg_{window}"] = (
                latest_value - avg
                if latest_value is not None and avg is not None
                else None
            )

            if name == "overall":
                item[f"spread_mean_{window}"] = None
                item[f"spread_std_{window}"] = None
                item[f"spread_variance_{window}"] = None
                item[f"spread_count_{window}"] = 0
            else:
                spread_sample = (
                    pd.to_numeric(daily_window[name], errors="coerce")
                    - pd.to_numeric(daily_window["overall"], errors="coerce")
                ).dropna()
                item[f"spread_mean_{window}"] = (
                    float(spread_sample.mean()) if not spread_sample.empty else None
                )
                item[f"spread_std_{window}"] = (
                    float(spread_sample.std(ddof=1))
                    if spread_sample.size >= 2
                    else None
                )
                item[f"spread_variance_{window}"] = (
                    float(spread_sample.var(ddof=1))
                    if spread_sample.size >= 2
                    else None
                )
                item[f"spread_count_{window}"] = int(spread_sample.size)

        output_rows.append(item)

    payload = dict(empty_payload)
    payload.update(
        {
            "asof": (
                _timestamp_text(latest_source.get("timestamp"))
                if latest_source.get("timestamp") is not None
                else None
            ),
            "available_trading_days": int(len(daily)),
            "rows": output_rows,
        }
    )
    return payload

def latest_by_resolution(
    resolution: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    published_only: bool = True,
) -> dict | None:
    """Return the latest point; dashboard callers default to publishable rows only."""
    initialise(db_path)
    quality_clause = f" AND {PUBLISHED_POINT_SQL}" if published_only else ""
    with connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT * FROM vix_points
            WHERE resolution=?{quality_clause}
            ORDER BY timestamp DESC LIMIT 1
            """,
            (resolution,),
        ).fetchone()
    return dict(row) if row is not None else None


def previous_by_resolution(
    resolution: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    published_only: bool = True,
) -> dict | None:
    initialise(db_path)
    quality_clause = f" AND {PUBLISHED_POINT_SQL}" if published_only else ""
    with connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT * FROM vix_points
            WHERE resolution=?{quality_clause}
            ORDER BY timestamp DESC LIMIT 1 OFFSET 1
            """,
            (resolution,),
        ).fetchone()
    return dict(row) if row is not None else None


def is_publishable_point(row: Mapping) -> bool:
    """A public dashboard point must contain all six VIX chains and full roster coverage."""
    expected = row.get("expected_instruments")
    observed = row.get("n_instruments")
    if expected is not None and (observed is None or int(observed) < int(expected)):
        return False
    return all(_clean_number(row.get(name)) is not None for name in VIX_COLUMNS)


def delete_unpublishable_points(
    *, db_path: str | Path = DEFAULT_DB_PATH
) -> int:
    """Delete partial dashboard points after the caller has created a DB backup."""
    initialise(db_path)
    with connect(db_path) as conn:
        cursor = conn.execute(f"DELETE FROM vix_points WHERE NOT {PUBLISHED_POINT_SQL}")
        return int(cursor.rowcount or 0)


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


def latest_collector_event(db_path: str | Path = DEFAULT_DB_PATH) -> dict | None:
    """Return the most recent collector event for dashboard diagnostics."""
    initialise(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT event_time, level, event, details
            FROM collector_events
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
    return dict(row) if row is not None else None


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
