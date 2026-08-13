import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .database import get_conn, rows_to_dicts, utc_now, set_state

BASE_DIR = Path(__file__).resolve().parent.parent
WALLETS_FILE = BASE_DIR / "Wallets.json"
POSITIONS_API = "https://data-api.polymarket.com/positions"
ACTIVITY_API = "https://data-api.polymarket.com/activity"
TRADES_API = "https://data-api.polymarket.com/trades"

REQUEST_TIMEOUT = 25
PAGE_LIMIT = 500
MIN_POSITION_VALUE = 1.0
MIN_DISPLAY_POSITION_VALUE = 1_000.0
MIN_WIN_RATE = 0.50


def _get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "pm-whale-tracker/1.0"})
    r.raise_for_status()
    return r.json()


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace(",", ""))
    except Exception:
        return default


def _wallet_short(addr: str) -> str:
    return (addr[:6] + "…" + addr[-4:]) if len(addr) > 12 else addr


def _parse_dt(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_wallets() -> List[Dict[str, str]]:
    if not WALLETS_FILE.exists():
        return []
    try:
        cfg = json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
        wallets = cfg.get("wallets") or []
        return [w for w in wallets if w.get("address")]
    except Exception:
        return []


def fetch_positions(address: str) -> List[Dict[str, Any]]:
    """Fetch the current Polymarket positions for one wallet.

    This intentionally mirrors reference_track_whales.py for the terminal
    value: page through the /positions endpoint with sizeThreshold=1 and save
    this run as a local snapshot. This endpoint is the source of truth for
    currentValue/size at the latest timestamp.
    """
    positions: List[Dict[str, Any]] = []
    offset = 0
    while True:
        page = _get_json(POSITIONS_API, {
            "user": address,
            "sizeThreshold": 1,
            "limit": PAGE_LIMIT,
            "offset": offset,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        if not isinstance(page, list):
            raise RuntimeError(f"Unexpected positions response for {address}: {page}")
        positions.extend(page)
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
        time.sleep(0.03)
    return positions


def _chunks(items: List[str], n: int) -> List[List[str]]:
    return [items[i:i + n] for i in range(0, len(items), n)]


def fetch_trades_for_wallet_markets(address: str, condition_ids: List[str], days: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent trades for one wallet in the monitored markets.

    data-api /trades supports user, market, side, limit and offset. It does not
    return historical currentValue, so these fills are used only to reconstruct
    the 10-day shape between the latest /positions terminal point and the prior
    days. We request takerOnly=false to avoid dropping maker fills.
    """
    if not condition_ids:
        return []
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    all_rows: List[Dict[str, Any]] = []
    # Keep URLs sane; docs say market is a comma-separated list of condition IDs.
    for chunk in _chunks(list(dict.fromkeys(condition_ids)), 25):
        offset = 0
        while True:
            params = {
                "user": address,
                "market": ",".join(chunk),
                "limit": PAGE_LIMIT,
                "offset": offset,
                "takerOnly": "false",
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC",
            }
            try:
                page = _get_json(TRADES_API, params)
            except Exception:
                # Some deployments reject market as CSV; fall back one market at a time.
                if len(chunk) == 1:
                    raise
                for cid in chunk:
                    all_rows.extend(fetch_trades_for_wallet_markets(address, [cid], days=days))
                break
            if not isinstance(page, list):
                raise RuntimeError(f"Unexpected trades response for {address}: {page}")
            if not page:
                break
            too_old = 0
            for row in page:
                ts = _parse_trade_ts(row.get("timestamp") or row.get("trade_ts") or row.get("time"))
                if ts is None:
                    continue
                if int(ts.timestamp()) < start_ts:
                    too_old += 1
                    continue
                all_rows.append(row)
            if len(page) < PAGE_LIMIT or too_old >= len(page):
                break
            offset += PAGE_LIMIT
            if offset > 9500:
                break
            time.sleep(0.03)
        time.sleep(0.04)
    return all_rows


def save_trade_rows(conn, address: str, name: str, trades: List[Dict[str, Any]], fetched_at: str) -> int:
    saved = 0
    for t in trades:
        cid = str(t.get("conditionId") or "")
        if not cid:
            continue
        ts = _parse_trade_ts(t.get("timestamp") or t.get("trade_ts") or t.get("time"))
        if ts is None:
            continue
        trade_ts = ts.isoformat().replace("+00:00", "Z")
        side = str(t.get("side") or "BUY").upper()
        outcome = str(t.get("outcome") or "?")
        size = _safe_float(t.get("size"))
        price = _safe_float(t.get("price"))
        usd = size * price
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO pm_whale_trades(
                    condition_id, address, name, outcome, side, size, price, usd,
                    trade_ts, raw_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    address.lower(),
                    name,
                    outcome,
                    side,
                    size,
                    price,
                    usd,
                    trade_ts,
                    json.dumps(t, ensure_ascii=False),
                    fetched_at,
                ),
            )
            saved += 1
        except Exception:
            pass
    return saved


def fetch_username(address: str) -> str:
    try:
        data = _get_json(ACTIVITY_API, {"user": address, "limit": 1})
        if data and isinstance(data, list):
            raw = data[0].get("name") or ""
            if raw and not raw.lower().startswith("0x"):
                return raw
            pseudo = data[0].get("pseudonym") or ""
            return pseudo if pseudo and not pseudo.lower().startswith("0x") else ""
    except Exception:
        pass
    return ""


def wallet_stats(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    wins = sum(1 for p in positions if _safe_float(p.get("cashPnl")) > 0)
    losses = sum(1 for p in positions if _safe_float(p.get("cashPnl")) < 0)
    total = wins + losses
    win_rate = wins / total if total else 0.0
    return {"wins": wins, "losses": losses, "win_rate": win_rate}


def qualifying_markets() -> Dict[str, Dict[str, Any]]:
    try:
        from .prediction_market_service import _macro_sql_filter
        macro_clause, macro_params = _macro_sql_filter()
    except Exception:
        macro_clause, macro_params = "1=1", []
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            f"""
            SELECT condition_id, bucket, question, event_title, volume_24h, volume_7d, volume_spike_ratio
            FROM pm_markets
            WHERE bucket IN ('rates_usd','geo_commodities') AND {macro_clause}
            """,
            macro_params,
        ).fetchall())
    return {str(r["condition_id"]): r for r in rows}



def _snapshot_cutoff(days: int = 10) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _window_dates(days: int = 10) -> List[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _day_end_utc(date_str: str) -> datetime:
    d = datetime.fromisoformat(date_str).date()
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)


def _latest_snapshot_time(conn) -> Optional[str]:
    row = conn.execute("SELECT MAX(fetched_at) AS ts FROM pm_whale_positions").fetchone()
    return row["ts"] if row and row["ts"] else None


def _sync_times(conn, days: int = 10) -> List[str]:
    cutoff = _snapshot_cutoff(days)
    rows = rows_to_dicts(conn.execute(
        "SELECT fetched_at FROM pm_whale_sync_runs WHERE fetched_at >= ? ORDER BY fetched_at ASC",
        (cutoff,),
    ).fetchall())
    times = [str(r["fetched_at"]) for r in rows if r.get("fetched_at")]
    if not times:
        rows = rows_to_dicts(conn.execute(
            "SELECT DISTINCT fetched_at FROM pm_whale_positions WHERE fetched_at >= ? ORDER BY fetched_at ASC",
            (cutoff,),
        ).fetchall())
        times = [str(r["fetched_at"]) for r in rows if r.get("fetched_at")]
    return times


def _parse_trade_ts(v: Any) -> Optional[datetime]:
    if v is None or v == "":
        return None
    try:
        # data-api /trades returns integer seconds in documented response.
        if isinstance(v, (int, float)) or str(v).isdigit():
            return datetime.fromtimestamp(int(float(v)), tz=timezone.utc)
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _safe_json_loads(s: Any) -> Dict[str, Any]:
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


def _current_position_by_outcome(conn, address: str, condition_id: str) -> Dict[str, Dict[str, Any]]:
    latest = _latest_snapshot_time(conn)
    result = {
        "yes": {"size": 0.0, "value": 0.0, "cur_price": None, "assets": set()},
        "no": {"size": 0.0, "value": 0.0, "cur_price": None, "assets": set()},
    }
    if not latest:
        return result
    rows = rows_to_dicts(conn.execute(
        """
        SELECT outcome, asset, size, value, raw_json
        FROM pm_whale_positions
        WHERE address = ? AND condition_id = ? AND fetched_at = ?
        """,
        (address.lower(), condition_id, latest),
    ).fetchall())
    for r in rows:
        key = "no" if str(r.get("outcome") or "").strip().lower() == "no" else "yes"
        raw = _safe_json_loads(r.get("raw_json"))
        result[key]["size"] += _safe_float(r.get("size"))
        result[key]["value"] += _safe_float(r.get("value"))
        asset = str(r.get("asset") or raw.get("asset") or "")
        if asset:
            result[key]["assets"].add(asset)
        cp = _safe_float(raw.get("curPrice"), None) if raw.get("curPrice") is not None else None
        if cp is not None and cp > 0:
            result[key]["cur_price"] = cp
    for key in ("yes", "no"):
        result[key]["assets"] = list(result[key]["assets"])
        if result[key]["cur_price"] is None and result[key]["size"] > 0:
            result[key]["cur_price"] = result[key]["value"] / result[key]["size"] if result[key]["size"] else None
    return result


def _price_history_by_day(conn, condition_id: str, days: int = 10) -> Dict[str, float]:
    """Return YES price by day, carrying forward the latest known price."""
    dates = _window_dates(days)
    if not dates:
        return {}
    start = dates[0] + "T00:00:00Z"
    rows = rows_to_dicts(conn.execute(
        "SELECT ts, price FROM pm_price_history WHERE condition_id = ? AND ts >= ? ORDER BY ts ASC",
        (condition_id, start),
    ).fetchall())
    by_day: Dict[str, float] = {}
    last: Optional[float] = None
    i = 0
    for d in dates:
        end_dt = _day_end_utc(d)
        while i < len(rows):
            ts = _parse_dt(str(rows[i].get("ts") or ""))
            if ts is None or ts <= end_dt:
                if rows[i].get("price") is not None:
                    last = _safe_float(rows[i].get("price"))
                i += 1
            else:
                break
        if last is not None:
            by_day[d] = max(0.0, min(1.0, last))
    return by_day


def _trade_rows(conn, address: str, condition_id: str, days: int = 10) -> List[Dict[str, Any]]:
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)
    rows = rows_to_dicts(conn.execute(
        """
        SELECT * FROM pm_whale_trades
        WHERE address = ? AND condition_id = ? AND trade_ts >= ?
        ORDER BY trade_ts ASC
        """,
        (address.lower(), condition_id, start_dt.isoformat().replace("+00:00", "Z")),
    ).fetchall())
    return rows


def _local_snapshot_points_by_latest_daily(conn, address: str, condition_id: str, dates: List[str]) -> Dict[str, Dict[str, Any]]:
    """Return one exact /positions point per UTC date, using the latest run on that date.

    Important: multiple manual syncs on the same day must NOT be summed. The
    previous implementation switched to local-snapshot mode after the second
    same-day sync and collapsed the 10-day backfill into a one-day chart. This
    helper intentionally keeps only the latest snapshot within each date.
    """
    cutoff = _snapshot_cutoff(10)
    rows = rows_to_dicts(conn.execute(
        """
        SELECT fetched_at, outcome, value
        FROM pm_whale_positions
        WHERE address = ? AND condition_id = ? AND fetched_at >= ?
        ORDER BY fetched_at ASC
        """,
        (address.lower(), condition_id, cutoff),
    ).fetchall())
    by_run: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in rows:
        dt_obj = _parse_dt(str(r.get("fetched_at") or ""))
        if not dt_obj:
            continue
        d = dt_obj.date().isoformat()
        if d not in dates:
            continue
        key_run = (d, str(r.get("fetched_at") or ""))
        item = by_run.setdefault(key_run, {"date": d, "time": key_run[1], "yes": 0.0, "no": 0.0, "observed": True})
        side = "no" if str(r.get("outcome") or "").strip().lower() == "no" else "yes"
        item[side] += _safe_float(r.get("value"))

    latest_by_date: Dict[str, Dict[str, Any]] = {}
    for (d, ts), item in by_run.items():
        prev = latest_by_date.get(d)
        if prev is None or ts > str(prev.get("time") or ""):
            item["total"] = item["yes"] + item["no"]
            latest_by_date[d] = item
    return latest_by_date


def _history_points_from_snapshots(conn, address: str, condition_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """Build a fixed 10-day YES/NO currentValue series.

    v6.5 rule:
      - Current value always comes from the latest /positions snapshot.
      - The 10-day shape is always available from /trades backfill on first-day
        installs.
      - Local /positions snapshots are overlaid by date when available, but a
        second same-day sync no longer disables the /trades curve.
      - Unknown dates before an entry remain 0. Zero exposure does not count as
        held days.
    """
    dates = _window_dates(10)
    current = _current_position_by_outcome(conn, address, condition_id)
    price_by_day = _price_history_by_day(conn, condition_id, 10)

    # 1) Build the requested immediate 10D curve from trade flow, anchored to
    # latest /positions. This remains the base even after repeated same-day syncs.
    trades = _trade_rows(conn, address, condition_id, 10)
    trade_events: List[Tuple[datetime, str, float]] = []
    for tr in trades:
        ts = _parse_trade_ts(tr.get("trade_ts"))
        if not ts:
            continue
        key = "no" if str(tr.get("outcome") or "").strip().lower() == "no" else "yes"
        side = str(tr.get("side") or "BUY").upper()
        size = _safe_float(tr.get("size"))
        signed = size if side == "BUY" else -size
        trade_events.append((ts, key, signed))

    base_points: List[Dict[str, Any]] = []
    for d in dates:
        end_dt = _day_end_utc(d)
        yes_size = current["yes"]["size"]
        no_size = current["no"]["size"]
        # Rewind from current size by removing all trades after this date end.
        for ts, key, signed in trade_events:
            if ts > end_dt:
                if key == "yes":
                    yes_size -= signed
                else:
                    no_size -= signed
        yes_size = 0.0 if abs(yes_size) < 1e-6 else max(0.0, yes_size)
        no_size = 0.0 if abs(no_size) < 1e-6 else max(0.0, no_size)
        yes_price = price_by_day.get(d)
        if yes_price is None:
            yes_price = current["yes"].get("cur_price") or (1.0 - (current["no"].get("cur_price") or 0.5))
        yes_price = max(0.0, min(1.0, yes_price))
        no_price = max(0.0, min(1.0, 1.0 - yes_price))
        yes_val = yes_size * yes_price
        no_val = no_size * no_price
        base_points.append({
            "time": d,
            "date": d,
            "yes": yes_val,
            "no": no_val,
            "total": yes_val + no_val,
            "observed": True,
            "source": "trades_backfill",
        })

    # If no 10D trades but current position exists, this is an old position. Show
    # a flat 10D line rather than a fake one-day entry, and label it separately.
    no_recent_trades_old_position = (not trade_events) and ((current["yes"]["value"] + current["no"]["value"]) > 0)
    if no_recent_trades_old_position:
        for p in base_points:
            p["yes"] = current["yes"]["value"]
            p["no"] = current["no"]["value"]
            p["total"] = p["yes"] + p["no"]
            p["source"] = "held_before_window"

    # Terminal point must match /positions exactly.
    if base_points:
        base_points[-1]["yes"] = current["yes"]["value"]
        base_points[-1]["no"] = current["no"]["value"]
        base_points[-1]["total"] = base_points[-1]["yes"] + base_points[-1]["no"]
        base_points[-1]["source"] = "latest_positions"

    # 2) Overlay exact daily /positions snapshots when present. This makes the
    # curve become more exact over time without breaking first-day/backfilled
    # visualization. Multiple same-day syncs collapse to the latest same-day run.
    local_by_date = _local_snapshot_points_by_latest_daily(conn, address, condition_id, dates)
    overlay_count = 0
    points: List[Dict[str, Any]] = []
    for p in base_points:
        d = str(p.get("date"))
        local = local_by_date.get(d)
        if local is not None:
            q = dict(p)
            q["yes"] = local["yes"]
            q["no"] = local["no"]
            q["total"] = local["total"]
            q["observed"] = True
            q["source"] = "local_positions"
            points.append(q)
            overlay_count += 1
        else:
            points.append(p)

    # Ensure terminal point is still exact after overlay.
    if points:
        points[-1]["yes"] = current["yes"]["value"]
        points[-1]["no"] = current["no"]["value"]
        points[-1]["total"] = points[-1]["yes"] + points[-1]["no"]
        points[-1]["observed"] = True
        points[-1]["source"] = "latest_positions"

    if no_recent_trades_old_position:
        source = "held_before_window_no_10d_trades"
    elif overlay_count >= 2:
        source = "trade_backfill_plus_local_snapshots"
    else:
        source = "trade_history_backfill"
    return points, points, source

def _max_consecutive_delta(points: List[Dict[str, Any]], field: str = "total") -> Optional[float]:
    vals = [_safe_float(p.get(field)) for p in points if p.get("observed", True)]
    if len(vals) < 2:
        return None
    deltas = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    return max(deltas, key=lambda x: abs(x)) if deltas else None


def _max_delta_window(points: List[Dict[str, Any]], hours: int = 24) -> Optional[float]:
    observed = [p for p in points if p.get("observed", True)]
    if len(observed) < 2:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    selected = []
    prior = None
    for p in observed:
        ts = _parse_dt(str(p.get("time") or "")) or _parse_dt(str(p.get("date") or ""))
        if ts is None:
            try:
                d = datetime.fromisoformat(str(p.get("date"))).date()
                ts = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
            except Exception:
                continue
        if ts < cutoff:
            prior = p
        else:
            selected.append(p)
    if prior is not None:
        selected = [prior] + selected
    if len(selected) < 2:
        return None
    return _max_consecutive_delta(selected, "total")


def _latest_points_for_condition(conn, condition_id: str) -> List[Dict[str, Any]]:
    latest = _latest_snapshot_time(conn)
    if not latest:
        return []
    return rows_to_dicts(conn.execute(
        """
        SELECT * FROM pm_whale_positions
        WHERE condition_id = ? AND fetched_at = ? AND COALESCE(value,0) > 0
        ORDER BY value DESC
        """,
        (condition_id, latest),
    ).fetchall())


def sync_tracked_whales(discover: bool = False, max_wallets: int = 0) -> Dict[str, Any]:
    """Fetch and save a full current-position snapshot for every tracked wallet.

    Every run pulls each wallet's current positions directly from
    data-api.polymarket.com and saves the raw rows locally. To satisfy first-day
    10D visualization, it also pulls the prior 10 days of /trades for the same
    wallet/markets and anchors the displayed curve to the latest /positions
    currentValue. Once multiple local snapshots exist, they take priority.
    """
    markets = qualifying_markets()
    if not markets:
        return {"wallets_checked": 0, "positions_saved": 0, "reason": "no qualifying prediction markets; sync Polymarket first"}

    wallets = load_wallets()
    if max_wallets and max_wallets > 0:
        wallets = wallets[:max_wallets]

    fetched_at = utc_now()
    positions_saved = 0
    trades_saved = 0
    wallets_checked = 0
    disqualified = 0
    errors: List[str] = []

    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pm_whale_sync_runs(fetched_at, wallet_count, positions_saved, errors_json) VALUES (?, ?, ?, ?)",
            (fetched_at, len(wallets), 0, "[]"),
        )
        for w in wallets:
            address = (w.get("address") or "").strip().lower()
            if not address:
                continue
            name = (w.get("name") or "").strip()
            if not name or name.lower().startswith(("0x", "trader_", "whale_")):
                name = fetch_username(address) or _wallet_short(address)
            try:
                positions = fetch_positions(address)
            except Exception as e:
                errors.append(f"{address}: {e}")
                continue
            wallets_checked += 1
            stats = wallet_stats(positions)
            if stats["win_rate"] <= MIN_WIN_RATE:
                disqualified += 1
                continue

            for p in positions:
                cid = str(p.get("conditionId") or "")
                if cid not in markets:
                    continue
                val = _safe_float(p.get("currentValue"))
                if val < MIN_POSITION_VALUE:
                    continue
                conn.execute(
                    """
                    INSERT INTO pm_whale_positions(
                        condition_id, address, name, outcome, asset, value,
                        size, avg_price, cash_pnl, win_rate, wins, losses,
                        fetched_at, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid,
                        address,
                        name,
                        str(p.get("outcome") or "?"),
                        str(p.get("asset") or ""),
                        val,
                        _safe_float(p.get("size")),
                        _safe_float(p.get("avgPrice") or p.get("averagePrice") or p.get("avg_price")),
                        _safe_float(p.get("cashPnl")),
                        stats["win_rate"],
                        stats["wins"],
                        stats["losses"],
                        fetched_at,
                        json.dumps(p, ensure_ascii=False),
                    ),
                )
                positions_saved += 1

            # Pull the prior 10 days of user/market trades immediately, so a
            # first-day install can render the 10-day YES/NO shape without
            # waiting ten days for local snapshots. Terminal currentValue still
            # comes from /positions above.
            try:
                trades = fetch_trades_for_wallet_markets(address, list(markets.keys()), days=10)
                trades_saved += save_trade_rows(conn, address, name, trades, fetched_at)
            except Exception as e:
                errors.append(f"{address} trades: {e}")
            time.sleep(0.04)

        conn.execute(
            "UPDATE pm_whale_sync_runs SET wallet_count = ?, positions_saved = ?, errors_json = ? WHERE fetched_at = ?",
            (wallets_checked, positions_saved, json.dumps(errors[:50], ensure_ascii=False), fetched_at),
        )
        cutoff = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat().replace("+00:00", "Z")
        conn.execute("DELETE FROM pm_whale_positions WHERE fetched_at < ?", (cutoff,))
        conn.execute("DELETE FROM pm_whale_sync_runs WHERE fetched_at < ?", (cutoff,))

    set_state("pm_whales_last_sync", fetched_at)
    return {
        "wallets_checked": wallets_checked,
        "positions_saved": positions_saved,
        "trades_saved": trades_saved,
        "disqualified": disqualified,
        "errors": errors[:10],
        "fetched_at": fetched_at,
        "wallet_file_count": len(load_wallets()),
        "method": "positions_terminal_plus_10d_trade_backfill",
    }


def get_whale_holders_for_market(condition_id: str, limit: int = 4) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        latest_rows = _latest_points_for_condition(conn, condition_id)
        if not latest_rows:
            return []
        by_wallet: Dict[str, Dict[str, Any]] = {}
        for r in latest_rows:
            addr = (r.get("address") or "").lower()
            if not addr:
                continue
            item = by_wallet.setdefault(addr, {
                "address": addr,
                "name": r.get("name") or _wallet_short(addr),
                "yes": 0.0,
                "no": 0.0,
                "value": 0.0,
                "win_rate": _safe_float(r.get("win_rate")) * 100,
                "wins": r.get("wins"),
                "losses": r.get("losses"),
            })
            val = _safe_float(r.get("value"))
            if str(r.get("outcome") or "").lower() == "no":
                item["no"] += val
            else:
                item["yes"] += val
            item["value"] += val

        out: List[Dict[str, Any]] = []
        for addr, item in by_wallet.items():
            display_points, observed_points, history_source = _history_points_from_snapshots(conn, addr, condition_id)
            max_10d = _max_consecutive_delta(observed_points, "total")
            max_24h = _max_delta_window(observed_points, 24)
            held_dates = {(p.get("date") or (p.get("time") or "")[:10]) for p in observed_points if _safe_float(p.get("total")) > 1}
            days_held = len(held_dates)
            if days_held == 0 and item["value"] > 0:
                days_held = 1
            first_day_positive = bool(observed_points and _safe_float(observed_points[0].get("total")) > 1)
            if first_day_positive and days_held >= 10:
                held_label = "≥10d"
            else:
                held_label = f"{days_held}d"
            side = "YES" if item["yes"] >= item["no"] else "NO"
            out.append({
                "name": item["name"],
                "address": addr,
                "outcome": side,
                "yes_value": round(item["yes"], 2),
                "no_value": round(item["no"], 2),
                "value": round(item["value"], 2),
                "win_rate": round(item["win_rate"], 1),
                "wins": item.get("wins"),
                "losses": item.get("losses"),
                "days_held": days_held,
                "days_held_label": held_label,
                "history_source": history_source,
                "history_note": "当前值来自 /positions；首次安装时用近10日 /trades 回补曲线形状，后续优先使用本地多次快照。",
                "max_delta_10d": max_10d,
                "max_delta_24h": max_24h,
                "history": [{
                    "time": p["time"],
                    "date": p.get("date") or str(p["time"])[:10],
                    "yes": round(_safe_float(p.get("yes")), 2),
                    "no": round(_safe_float(p.get("no")), 2),
                    "total": round(_safe_float(p.get("total")), 2),
                    "observed": bool(p.get("observed", True)),
                } for p in display_points],
            })
        out.sort(key=lambda h: (h.get("value") or 0, abs(h.get("max_delta_10d") or 0)), reverse=True)
        return out[:limit]


def get_whale_daily_overview(bucket: str = "all") -> Dict[str, Any]:
    try:
        from .prediction_market_service import _macro_sql_filter
        macro_clause, macro_params = _macro_sql_filter()
    except Exception:
        macro_clause, macro_params = "1=1", []
    where = ["bucket IN ('rates_usd','geo_commodities')", macro_clause]
    params: List[Any] = list(macro_params)
    if bucket and bucket != "all":
        where.append("bucket = ?")
        params.append(bucket)
    where_sql = " AND ".join(where)
    with get_conn() as conn:
        event_rows = rows_to_dicts(conn.execute(
            f"""
            SELECT condition_id, bucket, event_title, question, volume_24h, volume_spike_ratio, volume_10d_avg, volume_baseline_source
            FROM pm_markets
            WHERE {where_sql}
            ORDER BY COALESCE(volume_24h,0) DESC, COALESCE(volume_7d,0) DESC
            LIMIT 6
            """,
            params,
        ).fetchall())

        latest = _latest_snapshot_time(conn)
        if not latest:
            return {"events_traded_24h": event_rows, "top_traders_24h": []}

        join_where = where_sql.replace('bucket', 'm.bucket').replace("COALESCE(event_title", "COALESCE(m.event_title").replace("COALESCE(question", "COALESCE(m.question")
        latest_rows = rows_to_dicts(conn.execute(
            f"""
            SELECT p.*, m.question, m.event_title, m.bucket
            FROM pm_whale_positions p
            JOIN pm_markets m ON m.condition_id = p.condition_id
            WHERE p.fetched_at = ? AND COALESCE(p.value,0) >= ? AND {join_where}
            """,
            [latest, MIN_DISPLAY_POSITION_VALUE] + params,
        ).fetchall())

        by_key: Dict[tuple, Dict[str, Any]] = {}
        for r in latest_rows:
            addr = (r.get("address") or "").lower()
            cid = r.get("condition_id") or ""
            if not addr or not cid:
                continue
            key = (addr, cid)
            item = by_key.setdefault(key, {
                "address": addr,
                "name": r.get("name") or _wallet_short(addr),
                "condition_id": cid,
                "question": r.get("question") or r.get("event_title") or cid,
                "event_title": r.get("event_title"),
                "bucket": r.get("bucket"),
                "yes": 0.0,
                "no": 0.0,
                "value": 0.0,
                "win_rate": _safe_float(r.get("win_rate")) * 100,
            })
            val = _safe_float(r.get("value"))
            if str(r.get("outcome") or "").lower() == "no":
                item["no"] += val
            else:
                item["yes"] += val
            item["value"] += val

        out = []
        for (addr, cid), item in by_key.items():
            display_points, observed_points, history_source = _history_points_from_snapshots(conn, addr, cid)
            delta_24h = _max_delta_window(observed_points, 24)
            max_10d = _max_consecutive_delta(observed_points, "total")
            side = "YES" if item["yes"] >= item["no"] else "NO"
            sort_value = abs(delta_24h) if delta_24h is not None else item["value"]
            out.append({
                **item,
                "outcome": side,
                "delta_24h": delta_24h,
                "max_delta_10d": max_10d,
                "history_source": history_source,
                "sort_value": sort_value,
            })
        out.sort(key=lambda x: (x.get("sort_value") or 0, x.get("value") or 0), reverse=True)
        return {"events_traded_24h": event_rows, "top_traders_24h": out[:3]}


def get_whale_summary() -> Dict[str, Any]:
    return get_whale_daily_overview(bucket="all")
