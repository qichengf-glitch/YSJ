#!/usr/bin/env python3
"""
Polymarket Whale Tracker
========================
Fetches positions for all wallets in Wallets.json, diffs against the previous
snapshot, and generates a single event-centric HTML report:

  1. Markets with ≥40% volume spike above their 10-day rolling average (top section)
  2. All monitored events where tracked traders hold positions (sorted by volume)

Usage:
  python3 track_whales.py
"""

import datetime
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime as dt, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR     = Path(__file__).resolve().parent
WALLETS_FILE   = BASE_DIR / "Wallets.json"
DATA_DIR       = BASE_DIR / "data"
REPORTS_DIR    = BASE_DIR / "reports"
HISTORY_FILE   = DATA_DIR / "volume_history.json"
KNOWN_BAD_FILE = DATA_DIR / "known_bad.json"

POSITIONS_API = "https://data-api.polymarket.com/positions"
ACTIVITY_API  = "https://data-api.polymarket.com/activity"
GAMMA_API     = "https://gamma-api.polymarket.com"

TAG_SLUGS: dict[str, set[str]] = {
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

VOLUME_SPIKE_RATIO    = 1.40   # 40% above 10-day rolling average
HISTORY_WINDOW        = 10
MIN_EVENT_V24         = 1_000  # hide events with <$1k 24h volume (dormant markets)
MIN_SIZE_CHANGE       = 0.5
MIN_SIZE_CHANGE_PCT   = 0.01
REQUEST_TIMEOUT       = 20
PAGE_LIMIT            = 500

MIN_DISCOVERY_POSITION = 500   # min position $ before validating a new trader
MAX_VALIDATE_PER_RUN   = 60    # cap per-run validation API calls on first run

WEBHOOK_URL = os.environ.get("WHALE_WEBHOOK_URL", "").strip()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> any:
    req = urllib.request.Request(url, headers={"User-Agent": "whale-tracker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


def fetch_positions(address: str) -> list:
    positions, offset = [], 0
    while True:
        params = {
            "user": address, "sizeThreshold": 1,
            "limit": PAGE_LIMIT, "offset": offset,
            "sortBy": "CURRENT", "sortDirection": "DESC",
        }
        page = _get(f"{POSITIONS_API}?{urllib.parse.urlencode(params)}")
        if not isinstance(page, list):
            raise RuntimeError(f"Unexpected response: {page}")
        positions.extend(page)
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
    return positions


def fetch_username(address: str) -> str:
    try:
        data = _get(f"{ACTIVITY_API}?user={address}&limit=1")
        if data and isinstance(data, list):
            name = data[0].get("name") or ""
            if not name or name.lower().startswith("0x"):
                name = data[0].get("pseudonym") or ""
            return name
    except Exception:
        pass
    return ""


def fetch_market_meta() -> tuple[set[str], dict[str, dict]]:
    """
    Scans all monitored events.
    Returns:
      tracked_cids: set of conditionIds
      meta:         {conditionId: {title, v24, category}}
    """
    tracked_cids: set[str] = set()
    meta: dict[str, dict]  = {}
    cursor = ""
    fetched = 0

    while fetched < 600:
        params = "active=true&closed=false&archived=false&limit=100&order=volume&ascending=false"
        if cursor:
            params += f"&next_cursor={urllib.parse.quote(str(cursor))}"
        try:
            events = _get(f"{GAMMA_API}/events?{params}")
        except Exception:
            break
        if not events:
            break
        fetched += len(events)

        for ev in events:
            slugs = {t.get("slug", "") for t in (ev.get("tags") or [])}
            cat   = next((c for c, kw in TAG_SLUGS.items() if slugs & kw), None)
            if not cat:
                continue
            for m in ev.get("markets", []):
                if m.get("closed"):
                    continue
                cid = m.get("conditionId", "")
                if not cid:
                    continue
                tracked_cids.add(cid)
                meta[cid] = {
                    "title":    m.get("question") or ev.get("title", ""),
                    "v24":      float(m.get("volume24hr") or 0),
                    "category": cat,
                }

        if len(events) < 100:
            break
        cursor = events[-1].get("id", "")

    return tracked_cids, meta


# ---------------------------------------------------------------------------
# Volume history + spike detection
# ---------------------------------------------------------------------------

def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def record_volume_snapshots(market_meta: dict, history: dict, today: str) -> None:
    """Record today's v24 for every monitored market into the rolling history."""
    for cid, m in market_meta.items():
        entry = history.setdefault(cid, {"question": m["title"], "snapshots": []})
        snaps = entry["snapshots"]
        if snaps and snaps[-1]["ts"] == today:
            snaps[-1]["v24"] = m["v24"]      # refresh same-day entry
        else:
            snaps.append({"ts": today, "v24": m["v24"]})
        entry["snapshots"] = snaps[-30:]     # keep 30 days max


def save_history(history: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def get_spike_ratio(cid: str, history: dict, today: str) -> float | None:
    snaps = history.get(cid, {}).get("snapshots", [])
    past  = [s["v24"] for s in snaps if s["ts"] < today]
    if not past:
        return None
    avg = sum(past[-HISTORY_WINDOW:]) / len(past[-HISTORY_WINDOW:])
    if avg < 1:
        return None
    current = snaps[-1]["v24"] if snaps and snaps[-1]["ts"] == today else 0
    return current / avg


# ---------------------------------------------------------------------------
# Snapshot storage + diff
# ---------------------------------------------------------------------------

def wallet_dir(address: str) -> Path:
    d = DATA_DIR / address.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(address: str, positions: list, when: dt) -> Path:
    path = wallet_dir(address) / (when.strftime("%Y-%m-%dT%H%M%S") + ".json")
    path.write_text(json.dumps({
        "timestamp": when.isoformat(),
        "address":   address,
        "positions": positions,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_previous_snapshot(address: str, exclude: Path):
    files = sorted(
        [p for p in wallet_dir(address).glob("*.json") if p != exclude],
        key=lambda p: p.name,
    )
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def diff_positions(old: list, new: list) -> dict:
    old_idx = {p["asset"]: p for p in old if "asset" in p}
    new_idx = {p["asset"]: p for p in new if "asset" in p}
    opened  = [p for a, p in new_idx.items() if a not in old_idx]
    closed  = [p for a, p in old_idx.items() if a not in new_idx]
    changed = []
    for asset, new_pos in new_idx.items():
        old_pos = old_idx.get(asset)
        if old_pos is None:
            continue
        old_sz = float(old_pos.get("size", 0) or 0)
        new_sz = float(new_pos.get("size", 0) or 0)
        delta  = new_sz - old_sz
        if abs(delta) < MIN_SIZE_CHANGE:
            continue
        if abs(delta) / max(abs(old_sz), 1e-9) < MIN_SIZE_CHANGE_PCT:
            continue
        changed.append({"asset": asset, "delta": delta})
    return {"opened": opened, "closed": closed, "changed": changed}


def load_wallet_history(address: str, days: int = 7) -> dict[str, list[tuple[str, float]]]:
    """
    Load last `days` unique-date snapshots for a wallet.
    Returns {conditionId: [(date, value), ...]} oldest → newest.
    """
    d = DATA_DIR / address.lower()
    if not d.exists():
        return {}
    by_date: dict[str, Path] = {}
    for f in sorted(d.glob("*.json")):
        by_date[f.stem[:10]] = f          # latest file per date wins
    history: dict[str, list[tuple[str, float]]] = {}
    for date in sorted(by_date)[-days:]:
        try:
            snap = json.loads(by_date[date].read_text(encoding="utf-8"))
        except Exception:
            continue
        for p in snap.get("positions", []):
            cid = p.get("conditionId", "")
            val = float(p.get("currentValue") or 0)
            if cid:
                history.setdefault(cid, []).append((date, val))
    return history


def _holder_trend(history: list[tuple[str, float]]) -> str:
    """
    Compact trend cell: days held + largest single-day position change in the window.
    history is [(date, value), ...] oldest → newest.
    """
    held_style = ("background:#f1f5f9;color:#6b7280;padding:2px 7px;"
                  "border-radius:12px;font-size:10px;font-weight:600")

    if not history:
        return '<span style="color:#9ca3af;font-size:11px;font-style:italic">new</span>'

    days_held   = len(history)
    held_badge  = f'<span style="{held_style}">Held {days_held}d</span>'

    if days_held < 2:
        return held_badge

    # Largest single-day change in the window
    max_delta = max(
        (history[i][1] - history[i - 1][1] for i in range(1, days_held)),
        key=abs,
    )

    if abs(max_delta) < 100:          # ignore noise
        return held_badge

    amt   = _fmt_v(abs(max_delta))
    arrow = "▲" if max_delta > 0 else "▼"
    col   = "#16a34a" if max_delta > 0 else "#dc2626"

    return (f'{held_badge}&nbsp;'
            f'<span style="color:{col};font-size:11px;font-weight:600">'
            f'{arrow}&nbsp;{amt}</span>')


# ---------------------------------------------------------------------------
# HTML — single event-centric page
# ---------------------------------------------------------------------------

def _fmt_v(n: float) -> str:
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:.0f}"


def _cat_badge(cat: str) -> str:
    styles = {
        "treasury":      ("rgba(161,98,7,.10)",  "#92400e"),
        "international": ("rgba(29,78,216,.10)", "#1e40af"),
        "index":         ("rgba(6,95,70,.10)",   "#065f46"),
    }
    bg, fg = styles.get(cat, ("rgba(100,116,139,.10)", "#475569"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:4px;'
            f'font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase">{cat}</span>')


def _change_badge(label: str) -> str:
    if not label:
        return ""
    col = "#16a34a" if "▲" in label else "#dc2626" if "▼" in label else "#6b7280"
    return f'<span style="font-size:10px;color:{col}">{label}</span>'


def _holder_rows(holders: list) -> str:
    if not holders:
        return ('<tr><td colspan="4" style="color:#9ca3af;font-style:italic;'
                'padding:8px 12px">No tracked traders currently holding</td></tr>')
    rows = []
    for h in holders:
        no     = h["outcome"].upper() == "NO"
        oc_col = "#dc2626" if no else "#16a34a"
        rows.append(
            f'<tr style="border-bottom:1px solid #f1f5f9">'
            f'<td style="padding:8px 12px;font-weight:600;color:#111827">{h["name"]}</td>'
            f'<td style="padding:8px 12px"><span style="color:{oc_col};font-weight:700;font-size:12px">{h["outcome"].upper()}</span></td>'
            f'<td style="padding:8px 12px;text-align:right;font-variant-numeric:tabular-nums;color:#111827">${h["value"]:,.0f}</td>'
            f'<td style="padding:8px 12px">{_holder_trend(h.get("history", []))}</td>'
            f'</tr>'
        )
    return "".join(rows)


def _event_block(ev: dict) -> str:
    sr        = ev.get("spike_ratio")
    spike_tag = (f'<span style="background:rgba(234,88,12,.10);color:#c2410c;padding:2px 8px;'
                 f'border-radius:4px;font-size:11px;font-weight:700">🔥 {sr:.1f}× avg</span>') if sr else ""
    border    = "#ea580c" if sr else "#e5e7eb"
    vol_label = f'24h trading volume: {_fmt_v(ev["v24"])}'
    return (
        f'<div style="background:#fff;border-radius:8px;border:1px solid {border};'
        f'border-left:3px solid {border};margin-bottom:14px;overflow:hidden">'
        f'<div style="padding:12px 16px 10px;border-bottom:1px solid #f1f5f9;'
        f'display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        f'{_cat_badge(ev["category"])}'
        f'<span style="font-weight:600;color:#111827;flex:1">{ev["title"]}</span>'
        f'<span style="color:#6b7280;font-size:12px" title="Total dollars traded in this market in the last 24 hours">{vol_label}</span>'
        f'{spike_tag}'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="background:#f9fafb">'
        f'<th style="padding:6px 12px;text-align:left;font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Trader</th>'
        f'<th style="padding:6px 12px;text-align:left;font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Side</th>'
        f'<th style="padding:6px 12px;text-align:right;font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Position</th>'
        f'<th style="padding:6px 12px;font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Hold / 7d Change</th>'
        f'</tr></thead>'
        f'<tbody>{_holder_rows(ev["holders"])}</tbody>'
        f'</table></div>'
    )


def build_html(now: dt, all_events: list, baseline_days: int) -> str:
    ts          = now.strftime("%Y-%m-%d %H:%M UTC")
    spike_count = sum(1 for e in all_events if e.get("spike_ratio"))

    if baseline_days < HISTORY_WINDOW and not spike_count:
        baseline_banner = (
            f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:20px;color:#92400e;font-size:13px">'
            f'📊 Building volume baseline — Day {baseline_days} of {HISTORY_WINDOW}. '
            f'Spike detection activates once {HISTORY_WINDOW} days of data are recorded.</div>'
        )
    else:
        baseline_banner = ""

    spike_note = (f'<span style="color:#c2410c;font-weight:600"> · {spike_count} spike(s) detected</span>'
                  if spike_count else "")

    blocks = "".join(_event_block(ev) for ev in all_events)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Market Intelligence — {ts}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f9fafb;color:#111827;min-height:100vh}}
  .wrap{{max-width:960px;margin:0 auto;padding:32px 24px 80px}}
</style>
</head>
<body>
<div class="wrap">
  <div style="margin-bottom:24px;border-bottom:1px solid #e5e7eb;padding-bottom:18px">
    <div style="font-size:22px;font-weight:700;color:#111827">Market Intelligence</div>
    <div style="font-size:12px;color:#6b7280;margin-top:4px">
      {ts} · {len(all_events)} event(s) with tracked positions{spike_note}
    </div>
  </div>
  {baseline_banner}
  <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;
              color:#9ca3af;margin-bottom:12px">Sorted by 24h trading volume — high to low</div>
  {blocks}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Discovery — event-first: fetch top holders for a market, validate new ones
# ---------------------------------------------------------------------------

def _fetch_market_holders(cid: str, top_n: int = 10) -> list[dict]:
    """
    Find top traders in a market using recent trade activity.
    Returns list of {proxyWallet, name, currentValue} sorted by total $ traded.
    """
    try:
        trades = _get(
            f"https://data-api.polymarket.com/trades?market={cid}"
            f"&limit=200&sortBy=TIMESTAMP&sortDirection=DESC"
        )
        if not isinstance(trades, list):
            return []
    except Exception:
        return []

    agg: dict[str, dict] = {}
    for t in trades:
        addr = t.get("proxyWallet", "")
        if not addr:
            continue
        usd = float(t.get("size") or 0) * float(t.get("price") or 0)
        if addr not in agg:
            raw = t.get("name") or ""
            name = raw if raw and not raw.lower().startswith("0x") else (t.get("pseudonym") or "")
            agg[addr] = {"proxyWallet": addr, "name": name, "currentValue": 0.0}
        agg[addr]["currentValue"] += usd

    return sorted(agg.values(), key=lambda w: w["currentValue"], reverse=True)[:top_n]


def qualify_candidate(address: str, qualifying_cids: set[str]) -> dict | None:
    """
    Validate a candidate wallet: must have a position in a qualifying event
    and overall win rate > 50%.
    Returns {name, win_rate, wins, losses, positions} or None if disqualified.
    """
    try:
        positions, offset = [], 0
        while True:
            page = _get(
                f"{POSITIONS_API}?user={address}&sizeThreshold=1"
                f"&limit={PAGE_LIMIT}&offset={offset}&sortBy=CURRENT&sortDirection=DESC"
            )
            if not isinstance(page, list):
                return None
            positions.extend(page)
            if len(page) < PAGE_LIMIT:
                break
            offset += PAGE_LIMIT
    except Exception:
        return None

    qualifying_positions = [p for p in positions if p.get("conditionId") in qualifying_cids]
    if not qualifying_positions:
        return None

    wins   = sum(1 for p in positions if float(p.get("cashPnl") or 0) > 0)
    losses = sum(1 for p in positions if float(p.get("cashPnl") or 0) < 0)
    total  = wins + losses
    wr     = wins / total if total > 0 else 0.0
    if wr <= 0.50:
        return None

    name = ""
    try:
        act = _get(f"{ACTIVITY_API}?user={address}&limit=1")
        if act and isinstance(act, list):
            raw  = act[0].get("name") or ""
            name = raw if raw and not raw.lower().startswith("0x") else (act[0].get("pseudonym") or "")
    except Exception:
        pass

    return {
        "name":      name or address[:8] + "…",
        "win_rate":  wr,
        "wins":      wins,
        "losses":    losses,
        "positions": qualifying_positions,
    }


# ---------------------------------------------------------------------------
# Wallet loader
# ---------------------------------------------------------------------------

def load_wallets() -> list:
    if not WALLETS_FILE.exists():
        print(f"[error] Config not found: {WALLETS_FILE}", file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
    wallets = cfg.get("wallets", [])
    if not wallets:
        print("[error] No wallets in Wallets.json.", file=sys.stderr)
        sys.exit(1)
    return wallets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today().isoformat()
    now   = dt.now(timezone.utc)

    print("[scan] Fetching tracked market metadata …")
    tracked_cids, market_meta = fetch_market_meta()
    print(f"[scan] {len(tracked_cids)} tracked markets loaded")

    if len(tracked_cids) < 10:
        print("[abort] Fewer than 10 markets returned — likely a network issue. "
              "Wallets.json unchanged.", file=sys.stderr)
        sys.exit(1)

    history = load_history()
    record_volume_snapshots(market_meta, history, today)
    save_history(history)

    # Events that qualify for display: in our categories AND sufficient 24h volume
    qualifying_cids = {cid for cid, m in market_meta.items() if m["v24"] >= MIN_EVENT_V24}
    print(f"[scan] {len(qualifying_cids)} qualifying markets (v24 ≥ ${MIN_EVENT_V24:,})")

    # Estimate baseline age from history
    sample = next((v["snapshots"] for v in history.values() if v.get("snapshots")), [])
    baseline_days = len({s["ts"] for s in sample if s["ts"] < today})

    wallets = load_wallets()

    # -------------------------------------------------------------------
    # Fetch positions + auto-audit every wallet
    # -------------------------------------------------------------------
    wallet_data: dict[str, dict] = {}
    remove_addrs: set[str]       = set()

    for w in wallets:
        address = w["address"]
        name    = w.get("name", "")

        if not name or name.lower().startswith(("trader_", "whale_", "0x")):
            fetched = fetch_username(address)
            if fetched:
                name = fetched
        if not name:
            name = address[:6] + "…" + address[-4:]

        print(f"[fetch] {name} ({address}) ...")

        try:
            positions = fetch_positions(address)
        except Exception as e:
            print(f"  [error] {e}", file=sys.stderr)
            continue

        # Audit: does this wallet hold ANY position in our monitored categories?
        any_monitored = any(p.get("conditionId") in tracked_cids for p in positions)
        if not any_monitored:
            print(f"  [remove] no open positions in monitored markets")
            remove_addrs.add(address.lower())
            continue

        wins   = sum(1 for p in positions if float(p.get("cashPnl") or 0) > 0)
        losses = sum(1 for p in positions if float(p.get("cashPnl") or 0) < 0)
        total  = wins + losses
        wr     = wins / total if total > 0 else 0.0

        if wr <= 0.50:
            print(f"  [remove] win rate {wr:.0%} dropped below 50%")
            remove_addrs.add(address.lower())
            continue

        # Display: only positions in qualifying events (category + v24 threshold)
        qualifying_positions = [p for p in positions if p.get("conditionId") in qualifying_cids]

        snap_path = save_snapshot(address, positions, now)
        prev      = load_previous_snapshot(address, snap_path)

        diffs = None if prev is None else diff_positions(
            [p for p in prev["positions"] if p.get("conditionId") in qualifying_cids],
            qualifying_positions,
        )

        wallet_data[address] = {
            "name":      name,
            "positions": qualifying_positions,
            "win_rate":  wr,
            "wins":      wins,
            "losses":    losses,
            "diffs":     diffs,
        }
        print(f"  → {len(qualifying_positions)} qualifying positions  win:{wr:.0%}")

    # Apply audit removals
    if remove_addrs:
        cfg    = json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
        before = len(cfg["wallets"])
        cfg["wallets"] = [w for w in cfg["wallets"]
                          if w["address"].lower() not in remove_addrs]
        WALLETS_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[audit] Removed {len(remove_addrs)} wallet(s) — "
              f"{before} → {len(cfg['wallets'])} remaining")

    # -------------------------------------------------------------------
    # Load 7-day position history per tracked wallet
    # -------------------------------------------------------------------
    wallet_histories: dict[str, dict[str, list[float]]] = {}
    for address in wallet_data:
        wallet_histories[address] = load_wallet_history(address)

    # -------------------------------------------------------------------
    # Group by conditionId (event), attach holder info + diff labels
    # -------------------------------------------------------------------
    event_holders: dict[str, list] = {}

    for address, wd in wallet_data.items():
        d = wd["diffs"] or {"opened": [], "closed": [], "changed": []}
        opened_assets  = {p["asset"] for p in d.get("opened", [])}
        changed_assets = {c["asset"]: c["delta"] for c in d.get("changed", [])}
        hist_by_cid    = wallet_histories.get(address, {})

        for p in wd["positions"]:
            val = float(p.get("currentValue") or 0)
            if val < 1_000:          # skip trivial positions
                continue
            cid   = p.get("conditionId", "")
            asset = p.get("asset", "")

            if wd["diffs"] is None:
                lbl = "new"
            elif asset in opened_assets:
                lbl = "▲ opened"
            elif asset in changed_assets:
                delta = changed_assets[asset]
                lbl   = f"{'▲' if delta > 0 else '▼'} {delta:+,.0f}"
            else:
                lbl = ""

            event_holders.setdefault(cid, []).append({
                "name":         wd["name"],
                "outcome":      p.get("outcome", "?"),
                "value":        val,
                "win_rate":     wd["win_rate"],
                "wins":         wd["wins"],
                "losses":       wd["losses"],
                "change_label": lbl,
                "history":      hist_by_cid.get(cid, []),
            })

    for cid in event_holders:
        event_holders[cid].sort(key=lambda h: h["value"], reverse=True)

    # -------------------------------------------------------------------
    # Separate spike vs regular events, collect spiking conditionIds
    # -------------------------------------------------------------------
    spike_events: list[dict]   = []
    regular_events: list[dict] = []
    spiking_cids: set[str]     = set()

    for cid, holders in event_holders.items():
        m   = market_meta.get(cid, {})
        v24 = m.get("v24", 0)
        ev = {
            "title":    m.get("title", cid),
            "category": m.get("category", "index"),
            "v24":      v24,
            "holders":  holders,
        }
        sr = get_spike_ratio(cid, history, today)
        if sr is not None and sr >= VOLUME_SPIKE_RATIO:
            ev["spike_ratio"] = sr
            spike_events.append(ev)
            spiking_cids.add(cid)
        else:
            regular_events.append(ev)

    # Merge into one list, sorted by 24h volume high to low
    all_events = spike_events + regular_events
    all_events.sort(key=lambda e: e["v24"], reverse=True)

    # -------------------------------------------------------------------
    # HTML output (single page)
    # -------------------------------------------------------------------
    html_path = BASE_DIR / "index.html"
    html_path.write_text(build_html(now, all_events, baseline_days), encoding="utf-8")

    # -------------------------------------------------------------------
    # Text report
    # -------------------------------------------------------------------
    spike_count = sum(1 for e in all_events if e.get("spike_ratio"))
    lines = [
        f"Polymarket Whale Report — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 50,
        f"{len(all_events)} events  ·  {spike_count} spike(s)  ·  sorted by 24h volume",
    ]
    for ev in all_events:
        spike_str = f"  🔥 {ev['spike_ratio']:.1f}×" if ev.get("spike_ratio") else ""
        lines.append(f"\n  [{ev['category'].upper()}] {ev['title']}  {_fmt_v(ev['v24'])}/24h{spike_str}")
        for h in ev["holders"]:
            lines.append(f"    {h['name']:22}  {h['outcome']:3}  ${h['value']:>10,.0f}  "
                         f"win:{h['win_rate']:.0%}  {h.get('change_label','')}")

    report = "\n".join(lines)
    print("\n" + report)

    report_path = REPORTS_DIR / f"{now.strftime('%Y-%m-%dT%H%M%S')}.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n[saved] {report_path}")
    print(f"[html]  {html_path}  "
          f"({len(spike_events)} spike event(s), {len(regular_events)} regular event(s))")

    if spike_events:
        send_webhook(report)

    # -------------------------------------------------------------------
    # Event-first discovery — scan ALL qualifying events for top holders,
    # validate new ones, add to Wallets.json, show them this run
    # -------------------------------------------------------------------
    known_bad: set[str] = set()
    if KNOWN_BAD_FILE.exists():
        try:
            known_bad = set(json.loads(KNOWN_BAD_FILE.read_text())["addresses"])
        except Exception:
            pass

    # Addresses already processed (tracked + audited this run)
    checked_this_run: set[str] = {k.lower() for k in wallet_data}
    new_wallet_entries: list[dict] = []
    validated_count = 0

    print(f"\n[discover] Scanning {len(qualifying_cids)} qualifying events for top holders …")
    for cid in sorted(qualifying_cids):
        if validated_count >= MAX_VALIDATE_PER_RUN:
            break
        holders_raw = _fetch_market_holders(cid, top_n=10)
        for h in holders_raw:
            if validated_count >= MAX_VALIDATE_PER_RUN:
                break
            addr = (h.get("proxyWallet") or "").strip()
            if not addr:
                continue
            addr_lo = addr.lower()
            if addr_lo in checked_this_run or addr_lo in known_bad:
                continue
            val = float(h.get("currentValue") or 0)
            if val < MIN_DISCOVERY_POSITION:
                continue

            checked_this_run.add(addr_lo)
            stats = qualify_candidate(addr, qualifying_cids)
            validated_count += 1

            if stats is None:
                known_bad.add(addr_lo)
                continue

            display_name = stats["name"] or addr[:8] + "…"
            print(f"  [new] {display_name}  win:{stats['win_rate']:.0%} "
                  f"({stats['wins']}W/{stats['losses']}L)  {len(stats['positions'])} qualifying pos")

            # Add to wallet_data so they appear in the report immediately
            wallet_data[addr] = {
                "name":      display_name,
                "positions": stats["positions"],
                "win_rate":  stats["win_rate"],
                "wins":      stats["wins"],
                "losses":    stats["losses"],
                "diffs":     None,
            }
            new_wallet_entries.append({"name": display_name, "address": addr})

    # Persist known_bad cache
    KNOWN_BAD_FILE.write_text(
        json.dumps({"addresses": sorted(known_bad)}, indent=2), encoding="utf-8"
    )

    # Save new traders to Wallets.json
    if new_wallet_entries:
        cfg = json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
        cfg["wallets"].extend(new_wallet_entries)
        WALLETS_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[discover] Added {len(new_wallet_entries)} new trader(s) to Wallets.json")
    elif validated_count == 0:
        print("[discover] All market holders already tracked or disqualified")
    else:
        print(f"[discover] {validated_count} candidate(s) checked — none passed win rate filter")

    # -------------------------------------------------------------------
    # Re-generate HTML now that wallet_data may have new traders
    # -------------------------------------------------------------------
    if new_wallet_entries:
        # Rebuild event_holders with newly discovered traders included
        new_addrs = {nw["address"] for nw in new_wallet_entries}
        for address, wd in wallet_data.items():
            if address not in new_addrs:
                continue
            for p in wd["positions"]:
                val = float(p.get("currentValue") or 0)
                if val < 1_000:
                    continue
                cid = p.get("conditionId", "")
                event_holders.setdefault(cid, []).append({
                    "name":         wd["name"],
                    "outcome":      p.get("outcome", "?"),
                    "value":        val,
                    "win_rate":     wd["win_rate"],
                    "wins":         wd["wins"],
                    "losses":       wd["losses"],
                    "change_label": "new",
                    "history":      [],   # no snapshot history yet
                })
        for cid in event_holders:
            event_holders[cid].sort(key=lambda h: h["value"], reverse=True)

        # Rebuild full event list with new holders
        spike_events2:   list[dict] = []
        regular_events2: list[dict] = []
        for cid, holders in event_holders.items():
            m   = market_meta.get(cid, {})
            v24 = m.get("v24", 0)
            ev  = {"title": m.get("title", cid), "category": m.get("category", "index"),
                   "v24": v24, "holders": holders}
            sr  = get_spike_ratio(cid, history, today)
            if sr is not None and sr >= VOLUME_SPIKE_RATIO:
                ev["spike_ratio"] = sr
                spike_events2.append(ev)
            else:
                regular_events2.append(ev)
        all_events = spike_events2 + regular_events2
        all_events.sort(key=lambda e: e["v24"], reverse=True)
        html_path.write_text(build_html(now, all_events, baseline_days), encoding="utf-8")
        print(f"[html]  regenerated with {len(new_wallet_entries)} new trader(s)")


def send_webhook(text: str):
    if not WEBHOOK_URL:
        return
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
    except Exception as e:
        print(f"[warning] webhook failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
