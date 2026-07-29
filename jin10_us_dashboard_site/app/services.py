import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import settings
from .time_utils import dashboard_now, dashboard_today
from .database import get_conn, get_state, record_log, rows_to_dicts, set_state, utc_now
from .jin10_client import Jin10Client, Jin10ClientError, split_date_windows
from .logic import (
    company_groups,
    compute_metric_analysis,
    fmt_pct,
    parse_company_name_and_ticker,
    parse_dt,
    safe_float,
    serialize_raw,
    ticker_root,
)

CATEGORY = "us"


def display_cutoff_date() -> str:
    """Frontend policy: do not display events whose event/pub date is older than 7 days.

    Raw data/logs are still kept in SQLite for audit; this only affects display queries.
    """
    return (dashboard_today() - timedelta(days=7)).isoformat()


def is_recent_enough(value: Any) -> bool:
    dt = parse_dt(str(value)) if value not in (None, "") else None
    if not dt:
        return True
    now = dashboard_now()
    if dt.tzinfo is not None:
        dt_cmp = dt.astimezone(now.tzinfo)
    else:
        # Jin10's naive calendar timestamps are interpreted in dashboard local time.
        dt_cmp = dt.replace(tzinfo=now.tzinfo)
    return dt_cmp >= now - timedelta(days=7)


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\s\u3000]+", "", text)
    text = re.sub(r"[，。、“”‘’：:；;（）()【】\[\]\-—_.,!?！？]", "", text)
    return text


def region_for_payload(source_type: str, data: Dict[str, Any], ticker: str = "") -> str:
    text = " ".join(str(x or "") for x in [
        data.get("country"), data.get("exchange_name"), data.get("region"), data.get("name"),
        data.get("title"), data.get("event_content"), ticker,
    ])
    t = text.upper()
    # America bucket: US exchanges/tickers and US-focused events.
    if any(k in text for k in ["美国", "纽交所", "纳斯达克", "芝商所", "CME", "美股"]) or ticker.endswith((".N", ".O")) or any(k in t for k in ["NYSE", "NASDAQ", "CME", "UNITED STATES", "USA"]):
        return "美国"
    if any(k in text for k in ["英国", "德国", "法国", "意大利", "西班牙", "瑞士", "欧元区", "欧洲", "欧盟", "伦敦", "法兰克福"]) or any(k in t for k in ["EURO", "EUROPE", "UK", "GERMANY", "FRANCE"]):
        return "欧洲"
    if any(k in text for k in ["中国", "日本", "韩国", "香港", "台湾", "新加坡", "澳大利亚", "印度", "亚洲", "东京", "港交所"]) or any(k in t for k in ["CHINA", "JAPAN", "KOREA", "HONG KONG", "SINGAPORE", "AUSTRALIA", "ASIA"]):
        return "亚洲"
    return "其他"


def data_update_kind(action: str, data: Dict[str, Any]) -> Optional[str]:
    """Classify only display-worthy data changes.

    Latest Updates should surface material changes, not every raw log row.
    We intentionally hide ordinary inserts of unreleased indicators because those
    already belong in the Earnings calendar and create noisy duplicates.
    """
    if action == "delete":
        return None
    actual = data.get("actual")
    revised = data.get("revised")
    consensus = data.get("consensus")
    previous = data.get("previous")
    if actual not in (None, ""):
        return "数据公布"
    if revised not in (None, ""):
        return "数据修正"
    if action == "update" and consensus not in (None, ""):
        return "预测更新"
    if action == "update" and previous not in (None, ""):
        return "前值更新"
    return None


def event_update_kind(action: str, data: Dict[str, Any]) -> Optional[str]:
    if action == "delete":
        return None
    content = str(data.get("event_content") or "").strip()
    if not content:
        return None
    # The Updates "全部" tab must include valid event records across all star levels.
    # Star-based filtering is only applied by explicit UI filters such as Star 4+.
    return "市场事件"


def material_update_kind(source_type: str, action: str, data: Dict[str, Any]) -> Optional[str]:
    if source_type == "data":
        return data_update_kind(action, data)
    if source_type == "event":
        return event_update_kind(action, data)
    # Holiday changes are shown only in the Holidays page, not in Updates.
    return None


def meaningful_update(update: Dict[str, Any]) -> bool:
    title = normalize_text(update.get("title"))
    change = normalize_text(update.get("change"))
    if update.get("action") == "delete":
        return False
    if update.get("display_kind") is None:
        return False
    if not title or not change:
        return False
    if update.get("source_type") == "event":
        content = normalize_text((update.get("data") or {}).get("event_content"))
        if not content or content in {"companyevent", "event"}:
            return False
    return True


def update_display_title(source_type: str, data: Dict[str, Any], ticker: str, company: str) -> str:
    if source_type == "data":
        parts = [ticker or company, data.get("time_period"), data.get("measure")]
        return " · ".join(str(x) for x in parts if x)
    if source_type == "event":
        return str(data.get("event_content") or "").strip()
    return holiday_display_title(data)

def upsert_us_data(item: Dict[str, Any], action: str = "sync", modify_time: Optional[str] = None) -> None:
    company, ticker = parse_company_name_and_ticker(item.get("name"))
    now = utc_now()
    raw = serialize_raw(item)
    with get_conn() as conn:
        existing = conn.execute("SELECT first_seen_at FROM us_data_current WHERE source_id = ?", (item.get("id"),)).fetchone()
        first_seen = existing["first_seen_at"] if existing else now
        conn.execute(
            """
            INSERT INTO us_data_current(
                source_id, indicator_id, company_name, ticker, exchange_name, measure,
                time_period, full_time_period, pub_time, actual, previous, consensus, revised,
                unit, star, affect, affect_status, time_status, title, stock_logo, ahead_url,
                is_deleted, last_action, last_modify_time, first_seen_at, last_synced_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                indicator_id=excluded.indicator_id,
                company_name=excluded.company_name,
                ticker=excluded.ticker,
                exchange_name=excluded.exchange_name,
                measure=excluded.measure,
                time_period=excluded.time_period,
                full_time_period=excluded.full_time_period,
                pub_time=excluded.pub_time,
                actual=excluded.actual,
                previous=excluded.previous,
                consensus=excluded.consensus,
                revised=excluded.revised,
                unit=excluded.unit,
                star=excluded.star,
                affect=excluded.affect,
                affect_status=excluded.affect_status,
                time_status=excluded.time_status,
                title=excluded.title,
                stock_logo=excluded.stock_logo,
                ahead_url=excluded.ahead_url,
                is_deleted=excluded.is_deleted,
                last_action=excluded.last_action,
                last_modify_time=excluded.last_modify_time,
                last_synced_at=excluded.last_synced_at,
                raw_json=excluded.raw_json
            """,
            (
                int(item.get("id")),
                item.get("indicator_id"),
                company,
                ticker,
                item.get("country"),
                item.get("measure"),
                item.get("time_period"),
                item.get("full_time_period"),
                item.get("pub_time"),
                None if item.get("actual") is None else str(item.get("actual")),
                None if item.get("previous") is None else str(item.get("previous")),
                None if item.get("consensus") is None else str(item.get("consensus")),
                None if item.get("revised") is None else str(item.get("revised")),
                item.get("unit"),
                item.get("star") or 0,
                item.get("affect"),
                item.get("affect_status"),
                item.get("time_status"),
                item.get("title"),
                item.get("stock_logo"),
                item.get("ahead_url"),
                0 if action != "delete" else 1,
                action,
                modify_time,
                first_seen,
                now,
                raw,
            ),
        )


def upsert_us_event(item: Dict[str, Any], action: str = "sync", modify_time: Optional[str] = None) -> None:
    now = utc_now()
    raw = serialize_raw(item)
    with get_conn() as conn:
        existing = conn.execute("SELECT first_seen_at FROM us_event_current WHERE source_id = ?", (item.get("id"),)).fetchone()
        first_seen = existing["first_seen_at"] if existing else now
        conn.execute(
            """
            INSERT INTO us_event_current(
                source_id, event_time, event_content, country, determine, note, people, region,
                star, emergencies, time_status, is_deleted, last_action, last_modify_time,
                first_seen_at, last_synced_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                event_time=excluded.event_time,
                event_content=excluded.event_content,
                country=excluded.country,
                determine=excluded.determine,
                note=excluded.note,
                people=excluded.people,
                region=excluded.region,
                star=excluded.star,
                emergencies=excluded.emergencies,
                time_status=excluded.time_status,
                is_deleted=excluded.is_deleted,
                last_action=excluded.last_action,
                last_modify_time=excluded.last_modify_time,
                last_synced_at=excluded.last_synced_at,
                raw_json=excluded.raw_json
            """,
            (
                int(item.get("id")),
                item.get("event_time"),
                item.get("event_content"),
                item.get("country"),
                item.get("determine"),
                item.get("note"),
                item.get("people"),
                item.get("region"),
                item.get("star") or 0,
                item.get("emergencies"),
                item.get("time_status"),
                0 if action != "delete" else 1,
                action,
                modify_time,
                first_seen,
                now,
                raw,
            ),
        )


def upsert_us_holiday(item: Dict[str, Any], action: str = "sync", modify_time: Optional[str] = None) -> None:
    now = utc_now()
    raw = serialize_raw(item)
    event_time = item.get("event_time")
    holiday_date = item.get("date") or (event_time[:10] if event_time else None)
    with get_conn() as conn:
        existing = conn.execute("SELECT first_seen_at FROM us_holiday_current WHERE source_id = ?", (item.get("id"),)).fetchone()
        first_seen = existing["first_seen_at"] if existing else now
        conn.execute(
            """
            INSERT INTO us_holiday_current(
                source_id, date, event_time, event_content, country, exchange_name, name, rest_note,
                determine, note, people, region, star, time_status, is_deleted, last_action,
                last_modify_time, first_seen_at, last_synced_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                date=excluded.date,
                event_time=excluded.event_time,
                event_content=excluded.event_content,
                country=excluded.country,
                exchange_name=excluded.exchange_name,
                name=excluded.name,
                rest_note=excluded.rest_note,
                determine=excluded.determine,
                note=excluded.note,
                people=excluded.people,
                region=excluded.region,
                star=excluded.star,
                time_status=excluded.time_status,
                is_deleted=excluded.is_deleted,
                last_action=excluded.last_action,
                last_modify_time=excluded.last_modify_time,
                last_synced_at=excluded.last_synced_at,
                raw_json=excluded.raw_json
            """,
            (
                int(item.get("id")),
                holiday_date,
                event_time,
                item.get("event_content"),
                item.get("country"),
                item.get("exchange_name"),
                item.get("name"),
                item.get("rest_note"),
                item.get("determine"),
                item.get("note"),
                item.get("people"),
                item.get("region"),
                item.get("star") or 0,
                item.get("time_status"),
                0 if action != "delete" else 1,
                action,
                modify_time,
                first_seen,
                now,
                raw,
            ),
        )


def mark_deleted(source_type: str, source_id: int, action: str = "delete", modify_time: Optional[str] = None, fallback_data: Optional[Dict[str, Any]] = None) -> None:
    # If a delete log contains a data object not yet in current table, insert it as deleted for traceability.
    if fallback_data:
        if source_type == "data":
            upsert_us_data(fallback_data, action=action, modify_time=modify_time)
        elif source_type == "event":
            upsert_us_event(fallback_data, action=action, modify_time=modify_time)
        elif source_type == "holiday":
            upsert_us_holiday(fallback_data, action=action, modify_time=modify_time)
        return
    table = {"data": "us_data_current", "event": "us_event_current", "holiday": "us_holiday_current"}[source_type]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET is_deleted = 1, last_action = ?, last_modify_time = ?, last_synced_at = ? WHERE source_id = ?",
            (action, modify_time, utc_now(), source_id),
        )


def sync_full(start: date, end: date) -> Dict[str, int]:
    client = Jin10Client()
    counts = {"data": 0, "event": 0, "holiday": 0}
    for s, e in split_date_windows(start, end, max_days=7):
        for item in client.fetch_calendar_data(CATEGORY, s, e):
            upsert_us_data(item)
            counts["data"] += 1
        for item in client.fetch_calendar_event(CATEGORY, s, e):
            upsert_us_event(item)
            counts["event"] += 1
        for item in client.fetch_calendar_holiday(CATEGORY, s, e):
            upsert_us_holiday(item)
            counts["holiday"] += 1
    set_state("last_full_sync_at", utc_now())
    return counts


def sync_default_window() -> Dict[str, Any]:
    today = dashboard_today()
    start = today - timedelta(days=settings.sync_past_days)
    end = today + timedelta(days=settings.sync_future_days)
    return {"start": start.isoformat(), "end": end.isoformat(), "counts": sync_full(start, end)}


def process_logs_for(source_type: str) -> Dict[str, Any]:
    client = Jin10Client()
    state_key = f"last_{source_type}_log_id"
    last = get_state(state_key)
    cursor = int(last) if last else None
    processed = 0
    skipped_missing_data_id = 0
    pages = 0
    seen_ids: set[int] = set()

    # A single response can be capped after downtime. Keep advancing until the
    # API returns no strictly newer log ids, with a hard safety bound.
    for _ in range(20):
        logs = client.fetch_log(source_type, CATEGORY, last_log_id=cursor)
        logs = sorted(logs, key=lambda x: int(x.get("log_id") or 0))
        fresh = []
        for log in logs:
            log_id = int(log.get("log_id") or 0)
            if log_id <= (cursor or 0) or log_id in seen_ids:
                continue
            seen_ids.add(log_id)
            fresh.append(log)
        if not fresh:
            break
        pages += 1
        for log in fresh:
            action = log.get("action") or "unknown"
            data = log.get("data") or {}
            raw_id = log.get("data_id") or data.get("id")
            modify_time = log.get("modify_time")
            # Persist and advance malformed upstream logs too. Otherwise one log
            # with no data id can pin the incremental cursor forever.
            record_log(CATEGORY, source_type, log)
            try:
                data_id = int(raw_id) if raw_id is not None else None
            except (TypeError, ValueError):
                data_id = None
            if data_id is None:
                cursor = max(cursor or 0, int(log.get("log_id") or 0))
                skipped_missing_data_id += 1
                processed += 1
                continue
            if action in {"insert", "update"}:
                if source_type == "data":
                    upsert_us_data(data, action=action, modify_time=modify_time)
                elif source_type == "event":
                    upsert_us_event(data, action=action, modify_time=modify_time)
                elif source_type == "holiday":
                    upsert_us_holiday(data, action=action, modify_time=modify_time)
            elif action == "delete":
                fallback = dict(data) if data else None
                if fallback is not None:
                    fallback.setdefault("id", data_id)
                mark_deleted(source_type, data_id, action=action, modify_time=modify_time, fallback_data=fallback)
            cursor = max(cursor or 0, int(log.get("log_id") or 0))
            processed += 1
        set_state(state_key, str(cursor or 0))
        if len(logs) == 0:
            break

    set_state(f"last_{source_type}_log_poll_at", utc_now())
    return {
        "source_type": source_type, "processed": processed,
        "skipped_missing_data_id": skipped_missing_data_id,
        "last_log_id": cursor or 0, "pages": pages,
    }

def sync_all_logs() -> Dict[str, Any]:
    return {"data": process_logs_for("data"), "event": process_logs_for("event"), "holiday": process_logs_for("holiday")}


def query_data_rows(start: Optional[str] = None, end: Optional[str] = None, include_deleted: bool = False) -> List[Dict[str, Any]]:
    where = [] if include_deleted else ["is_deleted = 0"]
    params: List[Any] = []
    # Display policy: never show items whose pub_time is more than 7 days in the past.
    cutoff = display_cutoff_date()
    effective_start = max(start, cutoff) if start else cutoff
    where.append("date(pub_time) >= date(?)")
    params.append(effective_start)
    if end:
        where.append("date(pub_time) <= date(?)")
        params.append(end)
    clause = "WHERE " + " AND ".join(where) if where else ""
    with get_conn() as conn:
        return rows_to_dicts(conn.execute(f"SELECT * FROM us_data_current {clause} ORDER BY datetime(pub_time) ASC, star DESC", params).fetchall())


def dedup_metrics(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Display-level dedup: ticker + time_period + measure. Prefer released, newer modify time, newer pub_time, larger source_id.
    best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in rows:
        key = (r.get("ticker") or "", r.get("time_period") or "", r.get("measure") or "")
        old = best.get(key)
        if old is None:
            best[key] = r
            continue
        def rank(x: Dict[str, Any]) -> Tuple[int, str, str, int]:
            actual_rank = 1 if x.get("actual") not in (None, "") else 0
            return (
                actual_rank,
                x.get("last_modify_time") or "",
                x.get("pub_time") or "",
                int(x.get("source_id") or 0),
            )
        if rank(r) >= rank(old):
            best[key] = r
    return list(best.values())


def build_metric(row: Dict[str, Any]) -> Dict[str, Any]:
    analysis = compute_metric_analysis(row)
    return {
        **row,
        **analysis,
        "groups": company_groups(row.get("ticker") or ""),
        "ticker_root": ticker_root(row.get("ticker") or ""),
        "actual_num": safe_float(row.get("actual")),
        "previous_num": safe_float(row.get("previous")),
        "consensus_num": safe_float(row.get("consensus")),
        "surprise_pct_display": fmt_pct(analysis["surprise_pct"]),
        "change_pct_display": fmt_pct(analysis["change_pct"]),
    }


def aggregate_earnings(start: Optional[str] = None, end: Optional[str] = None) -> List[Dict[str, Any]]:
    metrics = [build_metric(r) for r in dedup_metrics(query_data_rows(start, end))]
    groups: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for m in metrics:
        pub_date = (m.get("pub_time") or "")[:10]
        key = (m.get("ticker") or "", m.get("time_period") or "", pub_date, m.get("time_status") or "")
        groups[key].append(m)
    events: List[Dict[str, Any]] = []
    now = dashboard_now().replace(tzinfo=None)
    for key, items in groups.items():
        if not items:
            continue
        items = sorted(items, key=lambda x: (x.get("measure") or ""))
        first = items[0]
        released = sum(1 for x in items if x.get("actual") not in (None, ""))
        comparable = [x for x in items if x.get("surprise_pct") is not None]
        max_surprise = None
        if comparable:
            max_surprise = max(comparable, key=lambda x: abs(x.get("surprise_pct") or 0))
        if released == 0:
            status = "upcoming"
        elif released < len(items):
            status = "partially_released"
        else:
            status = "released"
        pub_dt = parse_dt(first.get("pub_time"))
        if status == "upcoming" and pub_dt and pub_dt < now:
            status = "stale_pending_release"
        star = max(int(x.get("star") or 0) for x in items)
        event = {
            "event_key": "|".join([str(x) for x in key]),
            "company_name": first.get("company_name"),
            "ticker": first.get("ticker"),
            "exchange_name": first.get("exchange_name"),
            "time_period": first.get("time_period"),
            "pub_time": first.get("pub_time"),
            "time_status": first.get("time_status"),
            "star": star,
            "status": status,
            "metrics_count": len(items),
            "released_count": released,
            "measures": [x.get("measure") for x in items if x.get("measure")],
            "groups": company_groups(first.get("ticker") or ""),
            "metrics": items,
            "max_surprise_metric": max_surprise,
            "max_surprise_pct": None if max_surprise is None else max_surprise.get("surprise_pct"),
            "max_surprise_pct_display": "—" if max_surprise is None else fmt_pct(max_surprise.get("surprise_pct")),
            "logo": first.get("stock_logo"),
        }
        events.append(event)
    events.sort(key=lambda e: (-(e.get("star") or 0), e.get("pub_time") or ""))
    return events


def get_updates(limit: int = 60, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return material, display-level updates.

    This is not a raw log viewer. It hides deletes, holiday logs, ordinary
    unreleased metric inserts, and duplicate insert/update pairs for the same
    company-period-measure. The goal is to show what changed in a way that is
    useful to investors and traders.
    """
    params: List[Any] = []
    where = ["category = 'us'"]
    if source_type in {"data", "event"}:
        where.append("source_type = ?")
        params.append(source_type)
    params.append(max(limit * 12, 240))
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            f"SELECT * FROM raw_jin10_logs WHERE {' AND '.join(where)} ORDER BY log_id DESC LIMIT ?",
            params,
        ).fetchall())

    out: List[Dict[str, Any]] = []
    seen_subjects = set()
    for r in rows:
        source_type_row = r.get("source_type")
        action = r.get("action") or "unknown"
        if action == "delete":
            continue
        raw = json.loads(r.get("raw_json") or "{}")
        data = raw.get("data") or {}
        display_kind = material_update_kind(source_type_row, action, data)
        if display_kind is None:
            continue
        # Hide logs whose underlying event/pub date is older than 7 days, even if the log was fetched recently.
        display_time = data.get("pub_time") or data.get("event_time") or data.get("date") or r.get("modify_time")
        if not is_recent_enough(display_time):
            continue

        ticker = ""
        company = ""
        time_status = None
        if source_type_row == "data":
            company, ticker = parse_company_name_and_ticker(data.get("name"))
            title = update_display_title(source_type_row, data, ticker, company)
            change = update_change_text(action, data, display_kind)
            star = data.get("star") or 0
            time_status = data.get("time_status")
            # Collapse insert/update duplicates and repeated logs for the same metric.
            subject_fp = (
                "data",
                ticker or company,
                normalize_text(data.get("time_period")),
                normalize_text(data.get("measure")),
            )
        elif source_type_row == "event":
            title = update_display_title(source_type_row, data, ticker, company)
            change = event_update_change_text(action, data, display_kind)
            star = data.get("star") or 0
            time_status = data.get("time_status")
            subject_fp = (
                "event",
                normalize_text(data.get("event_content")),
                str(data.get("event_time") or "")[:10],
                normalize_text(data.get("people")),
            )
        else:
            continue

        if subject_fp in seen_subjects:
            continue
        seen_subjects.add(subject_fp)
        region = region_for_payload(source_type_row, data, ticker=ticker)
        item = {
            **r,
            "data": data,
            "title": title,
            "change": change,
            "star": star,
            "time_status": time_status,
            "ticker": ticker,
            "company_name": company,
            "region": region,
            "display_kind": display_kind,
        }
        if not meaningful_update(item):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def get_updates_by_region(limit_per_region: int = 4) -> Dict[str, List[Dict[str, Any]]]:
    updates = get_updates(limit=max(limit_per_region * 12, 80))
    buckets: Dict[str, List[Dict[str, Any]]] = {"美国": [], "欧洲": [], "亚洲": []}
    for u in updates:
        region = u.get("region") if u.get("region") in buckets else None
        if not region:
            continue
        buckets[region].append(u)
    for region, items in buckets.items():
        items.sort(key=lambda x: (int(x.get("star") or 0), int(x.get("log_id") or 0)), reverse=True)
        buckets[region] = items[:limit_per_region]
    return buckets


def update_change_text(action: str, data: Dict[str, Any], display_kind: Optional[str] = None) -> str:
    measure = data.get("measure") or "指标"
    unit = data.get("unit") or ""
    actual = data.get("actual")
    consensus = data.get("consensus")
    previous = data.get("previous")
    revised = data.get("revised")
    affect = data.get("affect_status") or ""
    if display_kind == "数据公布" and actual not in (None, ""):
        parts = [f"{measure}公布：{actual}{unit}"]
        if consensus not in (None, ""):
            parts.append(f"预测 {consensus}{unit}")
        if previous not in (None, ""):
            parts.append(f"前值 {previous}{unit}")
        if affect and affect != "未公布":
            parts.append(str(affect))
        return " · ".join(parts)
    if display_kind == "数据修正" and revised not in (None, ""):
        return f"{measure}修正值更新为 {revised}{unit}"
    if display_kind == "预测更新" and consensus not in (None, ""):
        return f"{measure}预测值更新为 {consensus}{unit}"
    if display_kind == "前值更新" and previous not in (None, ""):
        return f"{measure}前值更新为 {previous}{unit}"
    return f"{measure}出现更新"


def event_update_change_text(action: str, data: Dict[str, Any], display_kind: Optional[str] = None) -> str:
    event_time = data.get("event_time") or ""
    people = data.get("people") or ""
    country = data.get("country") or ""
    parts = ["重要市场事件"]
    if event_time:
        parts.append(str(event_time))
    if people:
        parts.append(str(people))
    if country:
        parts.append(str(country))
    return " · ".join(parts)


def holiday_display_title(data: Dict[str, Any]) -> str:
    name = data.get("name") or data.get("event_content") or ""
    exch = data.get("exchange_name") or data.get("country") or ""
    if name and exch:
        return f"{name} · {exch}"
    return name or exch or ""


def holiday_update_change_text(action: str, data: Dict[str, Any]) -> str:
    date_v = data.get("date") or (data.get("event_time") or "")[:10]
    note = data.get("rest_note") or data.get("note") or data.get("event_content") or ""
    prefix = "新增假期/交易安排" if action == "insert" else "假期/交易安排更新"
    return " · ".join([x for x in [prefix, date_v, note] if x])


def get_company_events(start: Optional[str] = None, end: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    where = ["is_deleted = 0"]
    params: List[Any] = []
    cutoff = display_cutoff_date()
    effective_start = max(start, cutoff) if start else cutoff
    where.append("date(event_time) >= date(?)")
    params.append(effective_start)
    if end:
        where.append("date(event_time) <= date(?)")
        params.append(end)
    params.append(limit)
    with get_conn() as conn:
        return rows_to_dicts(conn.execute(
            f"SELECT * FROM us_event_current WHERE {' AND '.join(where)} ORDER BY datetime(event_time) ASC, star DESC LIMIT ?",
            params,
        ).fetchall())


def holiday_rank(row: Dict[str, Any]) -> Tuple[int, str, int]:
    exch = str(row.get("exchange_name") or row.get("country") or "")
    note = str(row.get("rest_note") or row.get("note") or row.get("event_content") or "")
    priority = 0
    # For duplicate holiday names on the same date, prefer main US equity-market closures.
    if any(k in exch for k in ["纽交所", "纳斯达克", "NYSE", "Nasdaq"]):
        priority += 50
    if "休市" in note:
        priority += 20
    if any(k in exch for k in ["芝商所", "CME"]):
        priority += 5
    if "提前" in note:
        priority += 3
    return (priority, row.get("last_modify_time") or row.get("last_synced_at") or "", int(row.get("source_id") or 0))


def get_holidays(start: Optional[str] = None, end: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    where = ["is_deleted = 0"]
    params: List[Any] = []
    date_col = "COALESCE(date, substr(event_time,1,10))"
    cutoff = display_cutoff_date()
    effective_start = max(start, cutoff) if start else cutoff
    where.append(f"date({date_col}) >= date(?)")
    params.append(effective_start)
    if end:
        where.append(f"date({date_col}) <= date(?)")
        params.append(end)
    # Fetch extra rows; display-level dedup may remove many exchange-level duplicates.
    params.append(max(limit * 5, 200))
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            f"SELECT * FROM us_holiday_current WHERE {' AND '.join(where)} ORDER BY date({date_col}) ASC LIMIT ?",
            params,
        ).fetchall())
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in rows:
        d = r.get("date") or (r.get("event_time") or "")[:10]
        # Exchange-level rows often repeat the same holiday. Display one row per
        # date + holiday name, preferring NYSE/Nasdaq equity-market closure.
        name = normalize_text(r.get("name") or r.get("event_content"))
        if not d or not name:
            continue
        key = (d, name)
        old = best.get(key)
        if old is None or holiday_rank(r) >= holiday_rank(old):
            best[key] = r
    out = sorted(best.values(), key=lambda x: (x.get("date") or (x.get("event_time") or "")[:10], -(holiday_rank(x)[0]), x.get("source_id") or 0))
    return out[:limit]


def dashboard_summary(days: int = 7) -> Dict[str, Any]:
    today = dashboard_today()
    start = today.isoformat()
    end = (today + timedelta(days=days)).isoformat()
    events = aggregate_earnings(start, end)
    all_metrics = [m for e in events for m in e.get("metrics", [])]
    high_star = [e for e in events if (e.get("star") or 0) >= 4]
    released_metrics = [m for m in all_metrics if m.get("actual") not in (None, "")]
    upcoming_events = [e for e in events if e.get("status") in {"upcoming", "stale_pending_release"}]
    pre = [e for e in events if e.get("time_status") == "盘前"]
    post = [e for e in events if e.get("time_status") == "盘后"]
    group_counter = Counter(g for e in events for g in e.get("groups", []))
    ticker_counter = Counter(e.get("ticker") for e in events if e.get("ticker"))
    comparable = [m for m in all_metrics if m.get("surprise_pct") is not None]
    pos = [m for m in comparable if (m.get("surprise_pct") or 0) > 0]
    neg = [m for m in comparable if (m.get("surprise_pct") or 0) < 0]
    top_surprises = sorted(comparable, key=lambda x: abs(x.get("surprise_pct") or 0), reverse=True)[:8]
    holidays = get_holidays(start, end)
    latest_updates = get_updates(limit=60)
    latest_updates_by_region = get_updates_by_region(limit_per_region=4)
    today_events = [e for e in events if (e.get("pub_time") or "")[:10] == start]
    next_48h_events = [
        e for e in events
        if start <= (e.get("pub_time") or "")[:10] <= (today + timedelta(days=1)).isoformat()
    ]
    unique_tickers = {e.get("ticker") for e in events if e.get("ticker")}
    brief = build_market_brief(events, group_counter, high_star, pre, post, released_metrics, pos, neg, holidays)
    return {
        "window": {"start": start, "end": end, "days": days},
        "brief": brief,
        "metrics": {
            # Dashboard-facing metrics. They intentionally separate company-level
            # earnings events from metric-level published results.
            "active_companies": len(unique_tickers),
            "high_star_companies": len(high_star),
            "next_48h_events": len(next_48h_events),
            "comparable_results": len(comparable),
            "positive_surprises": len(pos),
            "negative_surprises": len(neg),
            "material_updates": len(latest_updates),
            # Backward-compatible fields used by older frontends.
            "earnings_events": len(events),
            "high_star_events": len(high_star),
            "released_metrics": len(released_metrics),
            "upcoming_events": len(upcoming_events),
            "pre_market": len(pre),
            "after_hours": len(post),
            "updates_last_loaded": len(latest_updates),
        },
        "group_distribution": group_counter.most_common(8),
        "ticker_focus": ticker_counter.most_common(10),
        "latest_updates": latest_updates,
        "latest_updates_by_region": latest_updates_by_region,
        "top_surprises": top_surprises,
        "today_focus": {
            "pre_market": [e for e in today_events if e.get("time_status") == "盘前"][:8],
            "after_hours": [e for e in today_events if e.get("time_status") == "盘后"][:8],
            "released": [e for e in today_events if e.get("status") in {"released", "partially_released"}][:8],
        },
        "holidays": holidays[:5],
    }


def build_market_brief(events, group_counter, high_star, pre, post, released_metrics, pos, neg, holidays) -> Dict[str, Any]:
    if not events:
        return {
            "headline": "等待同步美股日历数据",
            "paragraph": "当前数据库暂无美股财报数据。请先执行“同步数据”拉取真实金十数据。",
            "bullets": ["同步后将展示财报集中度、盘前/盘后窗口、已公布数据和 surprise 排名。"],
            "chips": [],
        }
    top_group = group_counter.most_common(1)[0][0] if group_counter else "未分类公司"
    time_focus = "盘后" if len(post) >= len(pre) else "盘前"
    headline = f"{top_group}进入事件关注窗口"
    paragraph = (
        f"未来窗口内共有 {len(events)} 个聚合财报事件，其中 Star 4/5 事件 {len(high_star)} 个。"
        f"事件更多集中在{time_focus}公布，适合优先跟踪对应的开盘/盘后风险窗口。"
    )
    bullets = [
        f"事件最集中组别：{top_group}，共 {group_counter.most_common(1)[0][1] if group_counter else 0} 个事件。",
        f"盘前 {len(pre)} 个，盘后 {len(post)} 个；盘后事件更可能影响次日盘前定价。",
        f"已公布指标 {len(released_metrics)} 条；可比较指标中超预期 {len(pos)} 条，低于预期 {len(neg)} 条。",
    ]
    if holidays:
        bullets.append("未来窗口内存在假期/休市安排，需要注意流动性和交易时间变化。")
    chips = [f"{name} {count}" for name, count in group_counter.most_common(5)]
    return {"headline": headline, "paragraph": paragraph, "bullets": bullets, "chips": chips}
