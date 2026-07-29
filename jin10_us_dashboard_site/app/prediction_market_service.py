import json
import math
import re
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import settings
from .database import get_conn, rows_to_dicts, utc_now, update_job_status
from .http_utils import build_retry_session
from .time_utils import dashboard_today

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DAYS = 7
DEFAULT_MIN_PROB = 0.10
DEFAULT_MIN_VOLUME = 10_000
_HTTP = build_retry_session("us-event-intelligence/6.6", settings.request_retries)
_SYNC_LOCK = threading.Lock()
_HISTORY_LOCK = threading.Lock()
_LAST_GAMMA_QUERY_MODE = "not_run"
_LAST_GAMMA_VALIDATION_FALLBACKS: List[str] = []

# Raw source tags inherited from the original Excel prototype. The website maps
# these into three trading-oriented buckets rather than many informational labels.
TAG_SLUGS: Dict[str, set[str]] = {
    "treasury": {
        "fed", "fed-rates", "fomc", "economic-policy",
        "jerome-powell", "fed-chair", "interest-rates",
    },
    "international": {
        "geopolitics", "foreign-policy", "diplomacy-ceasefire", "military-strikes",
    },
    "index": {
        "economy", "inflation", "recession", "finance",
        "business", "stocks", "gdp", "cpi",
    },
}

BUCKET_LABELS = {
    "rates_usd": "利率美元",
    "geo_commodities": "地缘商品",
}

BUCKET_SUBTITLES = {
    "rates_usd": "利率预期、美元、美债久期和黄金利率端压力",
    "geo_commodities": "地缘风险溢价、黄金避险和原油供应风险",
}

LOW_MACRO_KEYWORDS = [
    # Equity/private-company markets: keep them out of the boss-facing macro view.
    " ipo", "ipo ", "before 2027", "acquire", "acquisition", "anthropic",
    "openai", "discord", "ramp", "remote", "vanta", "celonis", "databricks",
    "ledger", "lovable", "rippling", "shein", "anduril", "glean",
    # Sports / entertainment markets can be tagged as international, but they are not macro trading events.
    "fifa", "world cup", "goalscorer", "goal scorer", "kylian", "mbappe",
    "messi", "ronaldo", "football", "soccer", "basketball", "nba", "wnba",
    "nfl", "super bowl", "mlb", "ufc", "boxing", "champions league", "premier league",
    "tennis", "wimbledon", "olympic", "grammy", "oscars", "album", "movie", "film",
    # Boss-facing view explicitly excludes Russia/Ukraine war markets for now.
    "russia", "russian", "ukraine", "ukrainian", "zelensky", "zelenskyy", "putin",
    "kremlin", "kyiv", "kiev", "moscow", "donetsk", "kostyantynivka",
]

SQL_LOW_MACRO_TERMS = [
    "ipo", "anthropic", "openai", "discord", "ramp", "remote", "vanta", "celonis",
    "databricks", "ledger", "lovable", "rippling", "shein", "anduril", "glean",
    "fifa", "world cup", "goalscorer", "goal scorer", "kylian", "mbappe", "messi",
    "ronaldo", "football", "soccer", "basketball", "nba", "wnba", "nfl",
    "super bowl", "mlb", "ufc", "boxing", "champions league", "premier league",
    "tennis", "wimbledon", "olympic", "grammy", "oscars", "album", "movie", "film",
    # Boss-facing view explicitly excludes Russia/Ukraine war markets for now.
    "russia", "russian", "ukraine", "ukrainian", "zelensky", "zelenskyy", "putin",
    "kremlin", "kyiv", "kiev", "moscow", "donetsk", "kostyantynivka",
]

RATES_KEYWORDS = [
    "fed", "fomc", "rate", "rates", "interest", "treasury", "yield", "powell",
    "cpi", "pce", "inflation", "recession", "gdp", "mortgage", "dollar", "usd",
]

GEO_KEYWORDS = [
    "iran", "israel", "gaza", "hamas", "hezbollah", "houthi",
    "war", "strike", "military", "attack", "ceasefire", "peace", "diplomatic",
    "diplomacy", "sanction", "nuclear", "missile", "lebanon", "taiwan", "china",
]

GROWTH_KEYWORDS = [
    "recession", "growth", "gdp", "economy", "economic", "nasdaq", "s&p", "spx",
    "stock", "stocks", "tariff", "trade", "credit", "unemployment", "jobs",
]


def _ts_now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _parse_json_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    return default


def _clean_text(*parts: Any) -> str:
    return " ".join(str(p or "") for p in parts).strip()


def _tag_slugs(tags: List[Dict[str, Any]]) -> set[str]:
    return {str(t.get("slug") or "").lower() for t in (tags or [])}


def _source_category(slugs: set[str]) -> Optional[str]:
    for cat in ("treasury", "international", "index"):
        if slugs & TAG_SLUGS[cat]:
            return cat
    return None


def _has_any(text: str, words: List[str]) -> bool:
    t = " " + text.lower() + " "
    return any(w.lower() in t for w in words)


def _is_low_macro_relevance(text: str, slugs: set[str]) -> bool:
    t = " " + text.lower() + " "
    if _has_any(t, LOW_MACRO_KEYWORDS):
        return True
    # Pure IPO/equity/private company markets are not relevant to the boss's macro workflow.
    if " ipo" in t or "ipo " in t:
        return True
    return False


def _macro_sql_filter() -> Tuple[str, List[Any]]:
    """Hide low-macro-relevance records that may already exist in an old local DB."""
    clause = []
    params: List[Any] = []
    for term in SQL_LOW_MACRO_TERMS:
        clause.append("LOWER(COALESCE(event_title,'') || ' ' || COALESCE(question,'')) NOT LIKE ?")
        params.append(f"%{term.lower()}%")
    return " AND ".join(clause) if clause else "1=1", params


def classify_bucket(event_title: str, question: str, tags: List[Dict[str, Any]]) -> Tuple[Optional[str], str]:
    slugs = _tag_slugs(tags)
    text = _clean_text(event_title, question, " ".join(slugs)).lower()
    if _is_low_macro_relevance(text, slugs):
        return None, "low_macro_relevance"

    # Front-end trading buckets are intentionally limited to two boss-facing macro lines.
    # Rates also absorbs inflation/recession/GDP when they mainly affect rates/USD/duration.
    if (slugs & TAG_SLUGS["international"]) or _has_any(text, GEO_KEYWORDS):
        return "geo_commodities", "tags/keywords: geopolitical_commodities"
    if (slugs & TAG_SLUGS["treasury"]) or _has_any(text, RATES_KEYWORDS) or _has_any(text, ["cpi", "pce", "inflation", "recession", "gdp", "unemployment", "jobs"]):
        return "rates_usd", "tags/keywords: rates_usd"
    return None, "not_in_active_trading_buckets"

def signal_type(price_now: float, change_7d: float, change_1d: float, volume: float, liquidity: float, spread: float) -> Tuple[str, float]:
    abs7 = abs(change_7d)
    score = 0.0
    if volume > 0:
        score += min(50.0, math.log10(max(volume, 1)) * 8)
    score += min(35.0, abs7 * 260)
    if spread > 0:
        score += max(0.0, 15.0 - spread * 250)
    if liquidity > 0:
        score += min(10.0, math.log10(max(liquidity, 1)) * 1.5)

    if change_7d * change_1d < 0 and abs(change_7d) >= 0.05 and abs(change_1d) >= 0.02:
        return "反转观察", round(score + 6, 2)
    if abs(change_7d) >= 0.05 and volume >= 100_000:
        return "大成交重定价", round(score + 10, 2)
    if price_now >= 0.80 and volume >= 100_000 and 0 < spread <= 0.03:
        return "拥挤共识", round(score + 4, 2)
    if volume < 20_000 or spread > 0.08:
        return "低信号", round(score * 0.35, 2)
    return "观察", round(score, 2)


def _outcome_tone(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["ceasefire", "peace", "diplomatic", "diplomacy", "deal", "meeting", "agreement"]):
        return "deescalation"
    if any(w in t for w in ["strike", "war", "attack", "military", "sanction", "nuclear", "missile", "invade"]):
        return "escalation"
    if any(w in t for w in ["cut", "cuts", "lower", "decrease"]):
        return "rates_down"
    if any(w in t for w in ["hike", "increase", "raise"]):
        return "rates_up"
    if any(w in t for w in ["no change", "unchanged", "hold"]):
        return "rates_hold"
    if any(w in t for w in ["recession", "unemployment", "crisis"]):
        return "risk_off"
    return "neutral"


def asset_impact(bucket: str, event_title: str, question: str, change_7d: float) -> Dict[str, Any]:
    text = _clean_text(event_title, question)
    tone = _outcome_tone(text)
    rising = change_7d >= 0

    if bucket == "geo_commodities":
        if tone == "deescalation":
            gold = "↓" if rising else "↑"
            oil = "↓" if rising else "↑"
            risk = "↑" if rising else "↓"
            reason = "谈判/停火/协议类 outcome 概率上升通常意味着地缘风险溢价下降。"
        elif tone == "escalation":
            gold = "↑" if rising else "↓"
            oil = "↑" if rising else "↓"
            risk = "↓" if rising else "↑"
            reason = "冲突/制裁/军事升级类 outcome 概率上升通常推升避险和供应风险溢价。"
        else:
            gold, oil, risk = "观察", "观察", "观察"
            reason = "该地缘事件需要结合具体 outcome 判断风险溢价方向。"
        return {"assets": ["Gold", "Oil", "Risk Assets"], "bias": {"Gold": gold, "Oil": oil, "Risk Assets": risk}, "reason": reason}

    if bucket == "rates_usd":
        if tone == "rates_down":
            ust = "收益率↓" if rising else "收益率↑"
            usd = "↓" if rising else "↑"
            gold = "↑" if rising else "↓"
            reason = "降息/利率下行 outcome 概率上升通常压低收益率和美元，对黄金利率端偏支撑。"
        elif tone in {"rates_up", "rates_hold"}:
            ust = "收益率↑/稳" if rising else "收益率↓"
            usd = "↑/稳" if rising else "↓"
            gold = "↓/中性" if rising else "↑"
            reason = "维持高利率或加息类 outcome 概率上升通常削弱降息交易，对黄金利率端偏压制。"
        else:
            ust, usd, gold = "观察", "观察", "观察"
            reason = "利率美元链条需结合该 outcome 对降息/加息路径的含义判断。"
        return {"assets": ["UST", "USD", "Gold", "SPX/Nasdaq"], "bias": {"UST": ust, "USD": usd, "Gold": gold, "SPX/Nasdaq": "估值压力观察"}, "reason": reason}

    if tone == "risk_off":
        spx = "↓" if rising else "↑"
        credit = "利差↑" if rising else "利差↓"
        oil = "需求↓" if rising else "需求↑"
        reason = "衰退/风险事件概率上升通常压制风险资产和原油需求预期。"
    else:
        spx, credit, oil = "观察", "观察", "观察"
        reason = "增长风险类事件主要观察风险偏好和盈利/需求预期变化。"
    return {"assets": ["SPX", "Nasdaq", "Credit", "Oil Demand"], "bias": {"SPX": spx, "Credit": credit, "Oil Demand": oil}, "reason": reason}


def format_market_row(row: Dict[str, Any], include_raw: bool = False) -> Dict[str, Any]:
    def pct(x: Any) -> Optional[float]:
        if x is None:
            return None
        return round(float(x) * 100, 2)
    asset = json.loads(row.get("asset_impact_json") or "{}")
    out = {
        "condition_id": row.get("condition_id"),
        "event_id": row.get("event_id"),
        "bucket": row.get("bucket"),
        "bucket_label": BUCKET_LABELS.get(row.get("bucket"), row.get("bucket") or "其他"),
        "bucket_subtitle": BUCKET_SUBTITLES.get(row.get("bucket"), ""),
        "source_category": row.get("source_category"),
        "event_title": row.get("event_title"),
        "question": row.get("question"),
        "price_now": row.get("price_now"),
        "price_7d_ago": row.get("price_7d_ago"),
        "change_7d": row.get("change_7d"),
        "change_1d": row.get("change_1d"),
        "change_1mo": row.get("change_1mo"),
        "prob_pct": pct(row.get("price_now")),
        "price_7d_ago_pct": pct(row.get("price_7d_ago")),
        "change_7d_pp": pct(row.get("change_7d")),
        "change_1d_pp": pct(row.get("change_1d")),
        "change_1mo_pp": pct(row.get("change_1mo")),
        "bid_pct": pct(row.get("bid")),
        "ask_pct": pct(row.get("ask")),
        "spread_pp": pct(row.get("spread")),
        "volume_7d": row.get("volume_7d"),
        "volume_total": row.get("volume_total"),
        "volume_24h": row.get("volume_24h"),
        "volume_spike_ratio": row.get("volume_spike_ratio"),
        "volume_10d_avg": row.get("volume_10d_avg"),
        "volume_baseline_days": row.get("volume_baseline_days"),
        "volume_baseline_source": row.get("volume_baseline_source") or "",
        "liquidity": row.get("liquidity"),
        "signal_type": row.get("signal_type"),
        "signal_score": row.get("signal_score"),
        "asset_impact": asset,
        "active": bool(row.get("active", 1)),
        "closed": bool(row.get("closed", 0)),
        "fetched_at": row.get("fetched_at"),
    }
    try:
        dt = datetime.fromisoformat(str(row.get("fetched_at") or "").replace("Z", "+00:00"))
        age = max(0, int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()))
    except Exception:
        age = None
    out["age_seconds"] = age
    out["is_stale"] = age is None or age > settings.prediction_stale_after_minutes * 60
    if include_raw:
        out["raw_json"] = json.loads(row.get("raw_json") or "{}")
    return out


def _fetch_poly_events(page_size: int = 100, max_pages: int = 15) -> Tuple[List[Dict[str, Any]], bool, int]:
    global _LAST_GAMMA_QUERY_MODE, _LAST_GAMMA_VALIDATION_FALLBACKS
    """Fetch active events with offset pagination and API-compatible fallbacks.

    Gamma's public documentation currently advertises ``order=volume_24hr``,
    but deployments have occasionally returned HTTP 422 for that exact query.
    We therefore probe a fixed request mode on page 0 and keep that mode for
    every subsequent offset page:

    1. documented ``volume_24hr`` ordering;
    2. response-field ``volume24hr`` ordering;
    3. minimal active/open query, followed by local 24h-volume sorting.

    Returns ``(events, snapshot_complete, pages_fetched)``. If the configured
    page cap is reached on a full page, the snapshot refreshes seen markets but
    is not considered complete enough to deactivate unseen records.
    """

    def parse_page(response: requests.Response) -> Tuple[List[Dict[str, Any]], Optional[bool]]:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = (getattr(response, "text", "") or "").strip().replace("\n", " ")[:600]
            status = getattr(response, "status_code", "unknown")
            raise RuntimeError(f"Gamma /events HTTP {status}: {body or 'empty response body'}") from exc

        payload = response.json()
        has_more: Optional[bool] = None
        if isinstance(payload, list):
            return payload, has_more
        if isinstance(payload, dict) and isinstance(payload.get("events"), list):
            if payload.get("has_more") is not None:
                has_more = _as_bool(payload.get("has_more"), default=True)
            return payload.get("events") or [], has_more
        raise RuntimeError(f"Unexpected Gamma /events response: {type(payload).__name__}")

    base_params = {
        "active": "true",
        "closed": "false",
        "limit": page_size,
        "offset": 0,
    }
    request_modes = [
        ("documented_volume_24hr", {"order": "volume_24hr", "ascending": "false"}),
        ("json_field_volume24hr", {"order": "volume24hr", "ascending": "false"}),
        ("minimal_local_sort", {}),
    ]

    selected_mode: Optional[str] = None
    selected_extra: Dict[str, Any] = {}
    first_page: Optional[List[Dict[str, Any]]] = None
    first_has_more: Optional[bool] = None
    validation_errors: List[str] = []

    for mode_name, extra in request_modes:
        params = {**base_params, **extra}
        response = _HTTP.get(f"{GAMMA}/events", params=params, timeout=25)
        if getattr(response, "status_code", 200) == 422:
            body = (getattr(response, "text", "") or "").strip().replace("\n", " ")[:300]
            validation_errors.append(f"{mode_name}: {body or 'HTTP 422'}")
            continue
        first_page, first_has_more = parse_page(response)
        selected_mode = mode_name
        selected_extra = extra
        break

    if first_page is None or selected_mode is None:
        details = "; ".join(validation_errors) or "all request modes failed"
        raise RuntimeError(f"Gamma /events rejected all compatible query modes: {details}")

    events: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_signature: Optional[Tuple[str, ...]] = None
    snapshot_complete = False
    pages_fetched = 0

    for page_no in range(max_pages):
        if page_no == 0:
            page = first_page
            has_more = first_has_more
        else:
            params = {
                "active": "true",
                "closed": "false",
                "limit": page_size,
                "offset": page_no * page_size,
                **selected_extra,
            }
            response = _HTTP.get(f"{GAMMA}/events", params=params, timeout=25)
            page, has_more = parse_page(response)

        pages_fetched += 1
        if not page:
            snapshot_complete = True
            break

        signature = tuple(str(x.get("id") or x.get("eventId") or "") for x in page)
        if signature == previous_signature:
            raise RuntimeError("Gamma pagination repeated the same page; refusing a partial/stale sync")
        previous_signature = signature

        before = len(events)
        for event in page:
            event_id = str(event.get("id") or event.get("eventId") or "")
            if event_id and event_id not in seen_ids:
                seen_ids.add(event_id)
                events.append(event)
        if len(events) == before:
            raise RuntimeError("Gamma pagination returned no new event ids; refusing a looping partial sync")

        if has_more is False or len(page) < page_size:
            snapshot_complete = True
            break
        time.sleep(0.08)

    if selected_mode == "minimal_local_sort":
        events.sort(
            key=lambda event: _first_float(event, "volume24hr", "volume24H", "volume_24hr"),
            reverse=True,
        )

    _LAST_GAMMA_QUERY_MODE = selected_mode
    _LAST_GAMMA_VALIDATION_FALLBACKS = list(validation_errors)
    return events, snapshot_complete, pages_fetched


def _fetch_clob_history(token_id: str) -> List[Dict[str, Any]]:
    end_ts = _ts_now()
    start_ts = end_ts - DAYS * 86_400
    r = _HTTP.get(
        f"{CLOB}/prices-history",
        params={"market": token_id, "startTs": start_ts, "endTs": end_ts, "fidelity": 60},
        timeout=20,
    )
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("history", []) if isinstance(payload, dict) else []
    buckets: Dict[int, Dict[str, Any]] = {}
    for row in rows or []:
        try:
            ts = int(row.get("t"))
            bucket = ts - (ts % 3600)
            p = min(1.0, max(0.0, float(row.get("p"))))
            buckets[bucket] = {
                "ts": datetime.fromtimestamp(bucket, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "price": p,
            }
        except Exception:
            continue
    return [buckets[ts] for ts in sorted(buckets)]


def _first_float(mapping: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return _safe_float(value, default)
    return default


def _yes_index(market: Dict[str, Any]) -> Optional[int]:
    outcomes = _parse_json_list(market.get("outcomes"))
    for idx, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            return idx
    # Gamma documents outcomes alongside outcomePrices. Refuse to guess index 0
    # for malformed/non-binary records because that can invert YES and NO.
    return None


def _market_volume_7d(market: Dict[str, Any], volume_24h: float) -> float:
    direct = _first_float(market, "volume1wk", "volume1Week", "volume7d", default=-1.0)
    if direct >= 0:
        return direct
    clob = _first_float(market, "volume1wkClob", default=0.0)
    amm = _first_float(market, "volume1wkAmm", default=0.0)
    if clob > 0 or amm > 0:
        return clob + amm
    # Do not substitute lifetime volume. A one-day value is conservative but
    # temporally valid until Gamma exposes the weekly field for that record.
    return max(0.0, volume_24h)


def _volume_baseline(conn, condition_id: str, today: str, volume_24h: float, volume_7d: float) -> Tuple[Optional[float], Optional[float], int, str]:
    rows = rows_to_dicts(conn.execute(
        "SELECT v24 FROM pm_volume_history WHERE condition_id = ? AND date < ? ORDER BY date DESC LIMIT 10",
        (condition_id, today),
    ).fetchall())
    # Zero is a real quiet day and must be included; only absent dates are absent.
    vals = [max(0.0, _safe_float(r.get("v24"))) for r in rows]
    baseline_days = len(vals)
    avg: Optional[float] = None
    source = "none"
    if vals:
        avg = sum(vals) / len(vals)
        source = "local_10d_snapshots"
    elif volume_7d >= 0:
        avg = volume_7d / 7.0
        source = "polymarket_7d_avg_fallback"
    spike = (volume_24h / avg) if avg is not None and avg >= 1 else None
    return spike, avg, baseline_days, source


def refresh_prediction_history(limit: int = 250) -> Dict[str, Any]:
    """Refresh historical curves without delaying the current quote commit."""
    if not _HISTORY_LOCK.acquire(blocking=False):
        return {"skipped": True, "reason": "history sync already running"}
    started_at = utc_now()
    update_job_status("prediction_history", "running", started_at=started_at, error=None)
    saved_history = 0
    failures: List[str] = []
    try:
        with get_conn() as conn:
            targets = rows_to_dicts(conn.execute(
                """
                SELECT condition_id, token_id FROM pm_markets
                WHERE active = 1 AND closed = 0 AND token_id IS NOT NULL AND token_id <> ''
                ORDER BY COALESCE(volume_24h,0) DESC, COALESCE(volume_7d,0) DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall())
        for target in targets:
            cid = str(target.get("condition_id") or "")
            token_id = str(target.get("token_id") or "")
            if not cid or not token_id:
                continue
            try:
                hist = _fetch_clob_history(token_id)
                fetched_at = utc_now()
                with get_conn() as conn:
                    for h in hist:
                        conn.execute(
                            """
                            INSERT INTO pm_price_history(condition_id, token_id, ts, price, fetched_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(condition_id, ts) DO UPDATE SET
                                token_id=excluded.token_id, price=excluded.price, fetched_at=excluded.fetched_at
                            """,
                            (cid, token_id, h["ts"], h["price"], fetched_at),
                        )
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat().replace("+00:00", "Z")
                    conn.execute("DELETE FROM pm_price_history WHERE condition_id = ? AND ts < ?", (cid, cutoff))
                saved_history += len(hist)
            except Exception as exc:
                failures.append(f"{cid}: {exc}")
            time.sleep(0.025)
        finished_at = utc_now()
        result = {
            "targets": len(targets),
            "saved_history_points": saved_history,
            "failures": failures[:20],
            "fetched_at": finished_at,
        }
        update_job_status(
            "prediction_history",
            "success" if not failures else "partial",
            finished_at=finished_at,
            error="; ".join(failures[:3]) if failures else None,
            details=result,
        )
        return result
    except Exception as exc:
        update_job_status("prediction_history", "failed", finished_at=utc_now(), error=str(exc))
        raise
    finally:
        _HISTORY_LOCK.release()


def sync_prediction_markets(min_prob: float = DEFAULT_MIN_PROB, min_volume: float = DEFAULT_MIN_VOLUME, max_pages: int = 15, fetch_history: bool = True) -> Dict[str, Any]:
    if not _SYNC_LOCK.acquire(blocking=False):
        return {"skipped": True, "reason": "prediction quote sync already running"}
    started_at = utc_now()
    update_job_status("prediction_quotes", "running", started_at=started_at, error=None)
    try:
        events, snapshot_complete, pages_fetched = _fetch_poly_events(max_pages=max_pages)
        if not events:
            raise RuntimeError("Polymarket returned zero events; preserving the last successful snapshot")
        fetched_at = utc_now()
        saved_events = 0
        saved_markets = 0
        skipped_low_macro = 0
        skipped_filters = 0
        skipped_invalid = 0
        seen: set[str] = set()
        today = dashboard_today().isoformat()

        with get_conn() as conn:
            # Only a complete pagination snapshot may deactivate unseen records.
            # A page-cap-truncated response can still refresh the highest-activity markets
            # without incorrectly deleting valid records that were beyond the cap.
            if snapshot_complete:
                conn.execute("UPDATE pm_events SET active = 0")
                conn.execute("UPDATE pm_markets SET active = 0")

            for event in events:
                event_id = str(event.get("id") or event.get("eventId") or "")
                if not event_id:
                    continue
                event_title = str(event.get("title") or "")
                tags = event.get("tags") or []
                slugs = _tag_slugs(tags)
                source_category = _source_category(slugs)
                conn.execute(
                    """
                    INSERT INTO pm_events(event_id, title, source_category, tags_json, active, closed, volume, liquidity, fetched_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO UPDATE SET
                        title=excluded.title, source_category=excluded.source_category,
                        tags_json=excluded.tags_json, active=excluded.active, closed=excluded.closed,
                        volume=excluded.volume, liquidity=excluded.liquidity,
                        fetched_at=excluded.fetched_at, raw_json=excluded.raw_json
                    """,
                    (
                        event_id, event_title, source_category, json.dumps(tags, ensure_ascii=False),
                        1 if _as_bool(event.get("active"), default=True) else 0,
                        1 if _as_bool(event.get("closed"), default=False) else 0,
                        _first_float(event, "volumeNum", "volume"), _safe_float(event.get("liquidity")),
                        fetched_at, json.dumps(event, ensure_ascii=False),
                    ),
                )
                saved_events += 1

                for m in event.get("markets") or []:
                    if _as_bool(m.get("closed"), default=False) or not _as_bool(m.get("active"), default=True):
                        continue
                    condition_id = str(m.get("conditionId") or "")
                    if not condition_id or condition_id in seen:
                        continue
                    question = str(m.get("question") or "")
                    bucket, bucket_reason = classify_bucket(event_title, question, tags)
                    if bucket is None:
                        skipped_low_macro += 1
                        continue

                    idx = _yes_index(m)
                    if idx is None:
                        skipped_invalid += 1
                        continue
                    outcome_prices = _parse_json_list(m.get("outcomePrices"))
                    token_ids = _parse_json_list(m.get("clobTokenIds"))
                    if idx >= len(outcome_prices) or idx >= len(token_ids):
                        skipped_invalid += 1
                        continue
                    price_source = outcome_prices[idx]
                    price_now = min(1.0, max(0.0, _safe_float(price_source)))
                    token_id = str(token_ids[idx])
                    volume_24h = _first_float(m, "volume24hr", "volume24h", "volume24H")
                    volume_7d = _market_volume_7d(m, volume_24h)
                    volume_total = _first_float(m, "volumeNum", "volume")
                    if price_now < min_prob or volume_7d < min_volume:
                        skipped_filters += 1
                        continue
                    seen.add(condition_id)

                    change_7d = _safe_float(m.get("oneWeekPriceChange"))
                    change_1d = _safe_float(m.get("oneDayPriceChange"))
                    change_1mo = _safe_float(m.get("oneMonthPriceChange"))
                    bid_raw, ask_raw = m.get("bestBid"), m.get("bestAsk")
                    bid = _safe_float(bid_raw) if bid_raw not in (None, "") else None
                    ask = _safe_float(ask_raw) if ask_raw not in (None, "") else None
                    spread = max(0.0, ask - bid) if ask is not None and bid is not None else None
                    liquidity = _first_float(m, "liquidityNum", "liquidity", default=_safe_float(event.get("liquidity")))
                    price_7d_ago = min(1.0, max(0.0, price_now - change_7d))
                    sig, sig_score = signal_type(price_now, change_7d, change_1d, volume_7d, liquidity, spread or 0.0)
                    impact = asset_impact(bucket, event_title, question, change_7d)

                    conn.execute(
                        """
                        INSERT INTO pm_volume_history(condition_id, date, v24, question, bucket, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(condition_id, date) DO UPDATE SET
                            v24=excluded.v24, question=excluded.question,
                            bucket=excluded.bucket, fetched_at=excluded.fetched_at
                        """,
                        (condition_id, today, volume_24h, question or event_title, bucket, fetched_at),
                    )
                    spike, avg, baseline_days, baseline_source = _volume_baseline(
                        conn, condition_id, today, volume_24h, volume_7d
                    )
                    conn.execute(
                        """
                        INSERT INTO pm_markets(
                            condition_id, event_id, token_id, bucket, bucket_reason, source_category,
                            event_title, question, price_now, price_7d_ago, change_7d, change_1d, change_1mo,
                            bid, ask, spread, volume_7d, volume_total, volume_24h, volume_spike_ratio,
                            volume_10d_avg, volume_baseline_days, volume_baseline_source, liquidity,
                            signal_type, signal_score, asset_impact_json, active, closed, last_seen_at,
                            fetched_at, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)
                        ON CONFLICT(condition_id) DO UPDATE SET
                            event_id=excluded.event_id, token_id=excluded.token_id, bucket=excluded.bucket,
                            bucket_reason=excluded.bucket_reason, source_category=excluded.source_category,
                            event_title=excluded.event_title, question=excluded.question,
                            price_now=excluded.price_now, price_7d_ago=excluded.price_7d_ago,
                            change_7d=excluded.change_7d, change_1d=excluded.change_1d,
                            change_1mo=excluded.change_1mo, bid=excluded.bid, ask=excluded.ask,
                            spread=excluded.spread, volume_7d=excluded.volume_7d,
                            volume_total=excluded.volume_total, volume_24h=excluded.volume_24h,
                            volume_spike_ratio=excluded.volume_spike_ratio,
                            volume_10d_avg=excluded.volume_10d_avg,
                            volume_baseline_days=excluded.volume_baseline_days,
                            volume_baseline_source=excluded.volume_baseline_source,
                            liquidity=excluded.liquidity, signal_type=excluded.signal_type,
                            signal_score=excluded.signal_score, asset_impact_json=excluded.asset_impact_json,
                            active=1, closed=0, last_seen_at=excluded.last_seen_at,
                            fetched_at=excluded.fetched_at, raw_json=excluded.raw_json
                        """,
                        (
                            condition_id, event_id, token_id, bucket, bucket_reason, source_category,
                            event_title, question, price_now, price_7d_ago, change_7d, change_1d, change_1mo,
                            bid, ask, spread, volume_7d, volume_total, volume_24h, spike, avg,
                            baseline_days, baseline_source, liquidity, sig, sig_score,
                            json.dumps(impact, ensure_ascii=False), fetched_at, fetched_at,
                            json.dumps(m, ensure_ascii=False),
                        ),
                    )
                    saved_markets += 1

            if saved_markets == 0:
                raise RuntimeError(
                    "Polymarket response produced zero eligible markets; rolled back to preserve the last successful snapshot"
                )
            cutoff_date = (dashboard_today() - timedelta(days=35)).isoformat()
            conn.execute("DELETE FROM pm_volume_history WHERE date < ?", (cutoff_date,))

        result: Dict[str, Any] = {
            "fetched_events": len(events),
            "saved_events": saved_events,
            "saved_markets": saved_markets,
            "skipped_low_macro": skipped_low_macro,
            "skipped_filters": skipped_filters,
            "skipped_invalid": skipped_invalid,
            "fetched_at": fetched_at,
            "pagination": "offset",
            "pages_fetched": pages_fetched,
            "snapshot_complete": snapshot_complete,
            "event_order": _LAST_GAMMA_QUERY_MODE,
            "gamma_validation_fallbacks": list(_LAST_GAMMA_VALIDATION_FALLBACKS),
        }
        update_job_status("prediction_quotes", "success", finished_at=fetched_at, error=None, details=result)
    except Exception as exc:
        update_job_status("prediction_quotes", "failed", finished_at=utc_now(), error=str(exc))
        raise
    finally:
        _SYNC_LOCK.release()

    if fetch_history:
        result["history"] = refresh_prediction_history()
    return result

def get_prediction_markets(bucket: str = "all", signal: Optional[str] = None, min_volume: float = 0, limit: int = 1000) -> List[Dict[str, Any]]:
    # `signal` is kept only for backward compatibility with older API calls.
    where = ["bucket IN ('rates_usd','geo_commodities')", "active = 1", "closed = 0"]
    params: List[Any] = []
    macro_clause, macro_params = _macro_sql_filter()
    where.append(macro_clause)
    params.extend(macro_params)
    if bucket and bucket != "all":
        where.append("bucket = ?")
        params.append(bucket)
    if min_volume:
        where.append("volume_7d >= ?")
        params.append(float(min_volume))
    sql = f"""
        SELECT * FROM pm_markets
        WHERE {' AND '.join(where)}
        ORDER BY volume_7d DESC, ABS(change_7d) DESC
        LIMIT ?
    """
    params.append(int(limit))
    with get_conn() as conn:
        return [format_market_row(r) for r in rows_to_dicts(conn.execute(sql, params).fetchall())]

def _top(where: str, order: str, limit: int = 6, bucket: str = "all") -> List[Dict[str, Any]]:
    macro_clause, params = _macro_sql_filter()
    full_where = [where, macro_clause, "bucket IN ('rates_usd','geo_commodities')", "active = 1", "closed = 0"]
    if bucket and bucket != "all":
        full_where.append("bucket = ?")
        params.append(bucket)
    params.append(limit)
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(f"SELECT * FROM pm_markets WHERE {' AND '.join(full_where)} ORDER BY {order} LIMIT ?", params).fetchall())
        return [format_market_row(r) for r in rows]


def get_prediction_overview() -> Dict[str, Any]:
    macro_clause, macro_params = _macro_sql_filter()
    with get_conn() as conn:
        totals = rows_to_dicts(conn.execute(
            f"""
            SELECT bucket, COUNT(*) AS market_count, COALESCE(SUM(volume_7d),0) AS volume_sum,
                   COALESCE(AVG(change_7d),0) AS avg_change,
                   CASE WHEN COALESCE(SUM(volume_7d),0) > 0
                        THEN COALESCE(SUM(change_7d * volume_7d),0) / COALESCE(SUM(volume_7d),1)
                        ELSE COALESCE(AVG(change_7d),0)
                   END AS weighted_change
            FROM pm_markets
            WHERE {macro_clause} AND bucket IN ('rates_usd','geo_commodities') AND active = 1 AND closed = 0
            GROUP BY bucket
            """,
            macro_params,
        ).fetchall())
        row = conn.execute(f"SELECT MAX(fetched_at) AS fetched_at, MIN(fetched_at) AS oldest_fetched_at, COUNT(*) AS cnt FROM pm_markets WHERE {macro_clause} AND bucket IN ('rates_usd','geo_commodities') AND active = 1 AND closed = 0", macro_params).fetchone()
        fetched_at = row["fetched_at"] if row else None
        oldest_fetched_at = row["oldest_fetched_at"] if row else None
        market_count = row["cnt"] if row else 0
        sync_row = conn.execute("SELECT * FROM sync_job_status WHERE job = 'prediction_quotes'").fetchone()

    by_bucket = []
    for r in totals:
        by_bucket.append({
            "bucket": r["bucket"],
            "label": BUCKET_LABELS.get(r["bucket"], r["bucket"]),
            "subtitle": BUCKET_SUBTITLES.get(r["bucket"], ""),
            "market_count": r["market_count"],
            "volume_sum": r["volume_sum"],
            "avg_change_pp": round((r["avg_change"] or 0) * 100, 2),
            "weighted_change_pp": round((r["weighted_change"] or 0) * 100, 2),
        })
    by_bucket.sort(key=lambda x: {"rates_usd": 0, "geo_commodities": 1}.get(x["bucket"], 9))

    rising = _top("change_7d > 0", "change_7d DESC, volume_7d DESC", 2)
    falling = _top("change_7d < 0", "change_7d ASC, volume_7d DESC", 2)
    volume_leaders = _top("COALESCE(volume_spike_ratio,0) >= 1.4", "volume_spike_ratio DESC, volume_24h DESC, volume_7d DESC", 8)

    try:
        fetched_dt = datetime.fromisoformat(str(fetched_at or "").replace("Z", "+00:00"))
        age_seconds = max(0, int((datetime.now(timezone.utc) - fetched_dt.astimezone(timezone.utc)).total_seconds()))
    except Exception:
        age_seconds = None

    return {
        "fetched_at": fetched_at,
        "oldest_fetched_at": oldest_fetched_at,
        "age_seconds": age_seconds,
        "is_stale": age_seconds is None or age_seconds > settings.prediction_stale_after_minutes * 60,
        "sync_status": dict(sync_row) if sync_row else None,
        "market_count": market_count,
        "bucket_summary": by_bucket,
        "top_movers_up": rising,
        "top_movers_down": falling,
        "volume_leaders": volume_leaders,
    }

def get_prediction_market_detail(condition_id: str) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM pm_markets WHERE condition_id = ?", (condition_id,)).fetchone()
        if row is None:
            return {}
        market = format_market_row(dict(row), include_raw=False)
        history = rows_to_dicts(conn.execute(
            "SELECT ts, price FROM pm_price_history WHERE condition_id = ? ORDER BY ts ASC",
            (condition_id,),
        ).fetchall())
    market["history"] = [{"time": h["ts"], "price": h["price"], "prob_pct": round(float(h["price"]) * 100, 2)} for h in history]
    try:
        from .whale_service import get_whale_holders_for_market
        market["whale_holders"] = get_whale_holders_for_market(condition_id)
    except Exception:
        market["whale_holders"] = []
    return market


def get_prediction_history(condition_id: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            "SELECT ts, price FROM pm_price_history WHERE condition_id = ? ORDER BY ts ASC",
            (condition_id,),
        ).fetchall())
    return [{"time": r["ts"], "price": r["price"], "prob_pct": round(float(r["price"]) * 100, 2)} for r in rows]
