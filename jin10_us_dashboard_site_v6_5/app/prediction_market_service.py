import json
import math
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from .database import get_conn, rows_to_dicts, utc_now

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DAYS = 7
DEFAULT_MIN_PROB = 0.10
DEFAULT_MIN_VOLUME = 10_000

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
    if price_now >= 0.80 and volume >= 100_000 and (spread <= 0.03 or spread == 0):
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
        "volume_24h": row.get("volume_24h"),
        "volume_spike_ratio": row.get("volume_spike_ratio"),
        "volume_10d_avg": row.get("volume_10d_avg"),
        "volume_baseline_days": row.get("volume_baseline_days"),
        "volume_baseline_source": row.get("volume_baseline_source") or "",
        "liquidity": row.get("liquidity"),
        "signal_type": row.get("signal_type"),
        "signal_score": row.get("signal_score"),
        "asset_impact": asset,
        "fetched_at": row.get("fetched_at"),
    }
    if include_raw:
        out["raw_json"] = json.loads(row.get("raw_json") or "{}")
    return out


def _fetch_poly_events(page_size: int = 100, max_pages: int = 15) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    cursor = ""
    for _ in range(max_pages):
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": page_size,
            "order": "volume",
            "ascending": "false",
        }
        if cursor:
            params["next_cursor"] = cursor
        r = requests.get(f"{GAMMA}/events", params=params, timeout=20)
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        if not isinstance(page, list):
            break
        events.extend(page)
        cursor = str(page[-1].get("id") or "")
        time.sleep(0.12)
    return events


def _fetch_clob_history(token_id: str) -> List[Dict[str, Any]]:
    end_ts = _ts_now()
    start_ts = end_ts - DAYS * 86_400
    r = requests.get(
        f"{CLOB}/prices-history",
        params={"market": token_id, "startTs": start_ts, "endTs": end_ts, "fidelity": 60},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json().get("history", [])
    out = []
    # Hourly resample by taking the latest tick in each hour bucket.
    buckets: Dict[int, Dict[str, Any]] = {}
    for row in rows or []:
        try:
            ts = int(row.get("t"))
            bucket = ts - (ts % 3600)
            p = float(row.get("p"))
            buckets[bucket] = {"ts": datetime.fromtimestamp(bucket, tz=timezone.utc).isoformat().replace("+00:00", "Z"), "price": p}
        except Exception:
            continue
    for ts in sorted(buckets):
        out.append(buckets[ts])
    return out


def sync_prediction_markets(min_prob: float = DEFAULT_MIN_PROB, min_volume: float = DEFAULT_MIN_VOLUME, max_pages: int = 15, fetch_history: bool = True) -> Dict[str, Any]:
    fetched_at = utc_now()
    events = _fetch_poly_events(max_pages=max_pages)
    saved_events = 0
    saved_markets = 0
    saved_history = 0
    skipped_low_macro = 0
    skipped_filters = 0
    seen: set[str] = set()
    today = datetime.now(timezone.utc).date().isoformat()
    current_v24: Dict[str, Tuple[float, float, str, str]] = {}

    with get_conn() as conn:
        for event in events:
            event_id = str(event.get("id") or event.get("eventId") or "")
            event_title = str(event.get("title") or "")
            tags = event.get("tags") or []
            slugs = _tag_slugs(tags)
            source_category = _source_category(slugs)
            conn.execute(
                """
                INSERT INTO pm_events(event_id, title, source_category, tags_json, active, closed, volume, liquidity, fetched_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    title=excluded.title,
                    source_category=excluded.source_category,
                    tags_json=excluded.tags_json,
                    active=excluded.active,
                    closed=excluded.closed,
                    volume=excluded.volume,
                    liquidity=excluded.liquidity,
                    fetched_at=excluded.fetched_at,
                    raw_json=excluded.raw_json
                """,
                (
                    event_id,
                    event_title,
                    source_category,
                    json.dumps(tags, ensure_ascii=False),
                    1 if event.get("active", True) else 0,
                    1 if event.get("closed") else 0,
                    _safe_float(event.get("volume") or event.get("volumeNum")),
                    _safe_float(event.get("liquidity")),
                    fetched_at,
                    json.dumps(event, ensure_ascii=False),
                ),
            )
            saved_events += 1

            for m in event.get("markets") or []:
                if m.get("closed"):
                    continue
                condition_id = str(m.get("conditionId") or "")
                if not condition_id or condition_id in seen:
                    continue
                seen.add(condition_id)
                question = str(m.get("question") or "")
                bucket, bucket_reason = classify_bucket(event_title, question, tags)
                if bucket is None:
                    skipped_low_macro += 1
                    continue

                outcome_prices = _parse_json_list(m.get("outcomePrices"))
                price_now = _safe_float(outcome_prices[0] if outcome_prices else m.get("lastTradePrice"))
                volume_7d = _safe_float(m.get("volumeNum") or m.get("volume"))
                volume_24h = _safe_float(m.get("volume24hr") or m.get("volume24h") or m.get("volume24H"))
                if price_now <= min_prob or volume_7d <= min_volume:
                    skipped_filters += 1
                    continue
                change_7d = _safe_float(m.get("oneWeekPriceChange"))
                change_1d = _safe_float(m.get("oneDayPriceChange"))
                change_1mo = _safe_float(m.get("oneMonthPriceChange"))
                bid = _safe_float(m.get("bestBid"))
                ask = _safe_float(m.get("bestAsk"))
                spread = max(0.0, ask - bid) if ask and bid else 0.0
                liquidity = _safe_float(event.get("liquidity") or m.get("liquidity"))
                price_7d_ago = round(price_now - change_7d, 6) if price_now else None
                sig, sig_score = signal_type(price_now, change_7d, change_1d, volume_7d, liquidity, spread)
                impact = asset_impact(bucket, event_title, question, change_7d)
                token_ids = _parse_json_list(m.get("clobTokenIds"))
                token_id = str(token_ids[0]) if token_ids else ""

                conn.execute(
                    """
                    INSERT INTO pm_markets(
                        condition_id, event_id, token_id, bucket, bucket_reason, source_category,
                        event_title, question, price_now, price_7d_ago, change_7d, change_1d, change_1mo,
                        bid, ask, spread, volume_7d, volume_24h, volume_spike_ratio, liquidity, signal_type, signal_score,
                        asset_impact_json, fetched_at, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(condition_id) DO UPDATE SET
                        event_id=excluded.event_id,
                        token_id=excluded.token_id,
                        bucket=excluded.bucket,
                        bucket_reason=excluded.bucket_reason,
                        source_category=excluded.source_category,
                        event_title=excluded.event_title,
                        question=excluded.question,
                        price_now=excluded.price_now,
                        price_7d_ago=excluded.price_7d_ago,
                        change_7d=excluded.change_7d,
                        change_1d=excluded.change_1d,
                        change_1mo=excluded.change_1mo,
                        bid=excluded.bid,
                        ask=excluded.ask,
                        spread=excluded.spread,
                        volume_7d=excluded.volume_7d,
                        volume_24h=excluded.volume_24h,
                        volume_spike_ratio=excluded.volume_spike_ratio,
                        liquidity=excluded.liquidity,
                        signal_type=excluded.signal_type,
                        signal_score=excluded.signal_score,
                        asset_impact_json=excluded.asset_impact_json,
                        fetched_at=excluded.fetched_at,
                        raw_json=excluded.raw_json
                    """,
                    (
                        condition_id, event_id, token_id, bucket, bucket_reason, source_category,
                        event_title, question, price_now, price_7d_ago, change_7d, change_1d, change_1mo,
                        bid, ask, spread, volume_7d, volume_24h, None, liquidity, sig, sig_score,
                        json.dumps(impact, ensure_ascii=False), fetched_at, json.dumps(m, ensure_ascii=False),
                    ),
                )
                saved_markets += 1
                current_v24[condition_id] = (volume_24h, volume_7d, question or event_title, bucket)

                if fetch_history and token_id:
                    try:
                        hist = _fetch_clob_history(token_id)
                        for h in hist:
                            conn.execute(
                                """
                                INSERT INTO pm_price_history(condition_id, token_id, ts, price, fetched_at)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(condition_id, ts) DO UPDATE SET
                                    token_id=excluded.token_id,
                                    price=excluded.price,
                                    fetched_at=excluded.fetched_at
                                """,
                                (condition_id, token_id, h["ts"], h["price"], fetched_at),
                            )
                        saved_history += len(hist)
                    except Exception:
                        # History failures should not block summary refresh.
                        pass
                time.sleep(0.035)

    # Record 24h volume snapshots and compute spike ratio = current 24h volume / last-10-day average.
    with get_conn() as conn:
        for cid, (v24, v7d, q, bucket) in current_v24.items():
            conn.execute(
                """
                INSERT INTO pm_volume_history(condition_id, date, v24, question, bucket, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(condition_id, date) DO UPDATE SET
                    v24=excluded.v24, question=excluded.question, bucket=excluded.bucket, fetched_at=excluded.fetched_at
                """,
                (cid, today, v24, q, bucket, fetched_at),
            )
            rows = rows_to_dicts(conn.execute(
                "SELECT v24 FROM pm_volume_history WHERE condition_id = ? AND date < ? ORDER BY date DESC LIMIT 10",
                (cid, today),
            ).fetchall())
            vals = [float(r["v24"] or 0) for r in rows if float(r["v24"] or 0) >= 1]
            baseline_days = len(vals)
            avg = None
            spike = None
            source = "none"
            if vals:
                avg = sum(vals) / len(vals)
                source = "local_10d_snapshots"
            elif v7d and float(v7d) >= 7:
                # Polymarket does not expose 10-day average volume in the event payload.
                # Until local daily snapshots accumulate, use its reported 7D volume / 7
                # as the best available rolling average proxy, and mark the source.
                avg = float(v7d) / 7.0
                source = "polymarket_7d_avg_fallback"
            if avg is not None and avg >= 1:
                spike = float(v24 or 0) / avg
            conn.execute(
                "UPDATE pm_markets SET volume_spike_ratio = ?, volume_10d_avg = ?, volume_baseline_days = ?, volume_baseline_source = ? WHERE condition_id = ?",
                (spike, avg, baseline_days, source, cid),
            )

    return {
        "fetched_events": len(events),
        "saved_events": saved_events,
        "saved_markets": saved_markets,
        "saved_history_points": saved_history,
        "skipped_low_macro": skipped_low_macro,
        "skipped_filters": skipped_filters,
        "fetched_at": fetched_at,
    }


def get_prediction_markets(bucket: str = "all", signal: Optional[str] = None, min_volume: float = 0, limit: int = 1000) -> List[Dict[str, Any]]:
    # `signal` is kept only for backward compatibility with older API calls.
    where = ["bucket IN ('rates_usd','geo_commodities')"]
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
    full_where = [where, macro_clause, "bucket IN ('rates_usd','geo_commodities')"]
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
            WHERE {macro_clause} AND bucket IN ('rates_usd','geo_commodities')
            GROUP BY bucket
            """,
            macro_params,
        ).fetchall())
        row = conn.execute(f"SELECT MAX(fetched_at) AS fetched_at, COUNT(*) AS cnt FROM pm_markets WHERE {macro_clause} AND bucket IN ('rates_usd','geo_commodities')", macro_params).fetchone()
        fetched_at = row["fetched_at"] if row else None
        market_count = row["cnt"] if row else 0

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

    return {
        "fetched_at": fetched_at,
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
