"""
state.py -- snapshots, the diff engine, and the smart re-grade triggers.

SNAPSHOTS   data/snapshots/TICKER_YYYYMMDD.json holds the raw metrics, every
            sub-metric band decision, and the final scores. That is what makes
            the diff engine able to name the exact threshold that was crossed
            rather than just reporting that a number moved.

DIFF        Produces two artefacts:
              1. human-readable lines for the console/email
              2. a CSV whose every row carries the exact workbook cell to edit
            The workbook lays out 90 blocks of 13 rows: block n starts at
            row 1 + 13*(n-1); the 10 category rows follow the header; scores
            live in column C and reasons in column D.

TRIGGERS    Full re-grades are expensive and noisy. A ticker is queued only on
            earnings, a >10% FY2 consensus move, a red flag, a price/volume
            anomaly, or snapshot staleness. Otherwise the run just logs the
            weekly sentiment fields and moves on.
"""

from __future__ import annotations

import csv
import glob
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from .util import (LOG, REPORT_DIR, SNAPSHOT_DIR, fmt_unit, parse_date,
                   pct_change, today_str)

# Workbook geometry -- must match 'Individual grading'
BLOCK_HEIGHT = 13
FIRST_BLOCK_HEADER_ROW = 1
SCORE_COL = "C"
REASON_COL = "D"

_GRADE_ORDER = {"F": 1, "D": 2, "C": 3, "B": 4, "A": 5}


# =========================================================================== #
# Snapshots
# =========================================================================== #
def snapshot_path(ticker: str, datestr: Optional[str] = None) -> str:
    return os.path.join(SNAPSHOT_DIR, f"{ticker.upper()}_{datestr or today_str()}.json")


def save_snapshot(ticker: str, result, metrics, tier3: Optional[dict] = None) -> str:
    """Persist everything needed to reconstruct and diff this run."""
    payload = {
        "ticker": ticker.upper(),
        "run_date": datetime.now().isoformat(timespec="seconds"),
        "grade": result.to_dict(),
        "metrics": metrics.to_dict(),
        "tier3": tier3 or {},
        "schema_version": 2,
    }
    path = snapshot_path(ticker)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    LOG.info("[%s] snapshot saved -> %s", ticker, os.path.basename(path))
    return path


def list_snapshots(ticker: str) -> list:
    """All snapshot paths for a ticker, oldest first."""
    return sorted(glob.glob(os.path.join(SNAPSHOT_DIR, f"{ticker.upper()}_*.json")))


def load_snapshot(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        LOG.warning("could not read snapshot %s: %s", path, e)
        return None


def load_latest_snapshot(ticker: str, before_today: bool = True) -> Optional[dict]:
    """Most recent snapshot, optionally excluding one written today."""
    snaps = list_snapshots(ticker)
    if before_today:
        today = today_str()
        snaps = [s for s in snaps if not s.endswith(f"_{today}.json")]
    return load_snapshot(snaps[-1]) if snaps else None


def snapshot_age_days(ticker: str) -> Optional[int]:
    snaps = list_snapshots(ticker)
    if not snaps:
        return None
    d = parse_date(os.path.basename(snaps[-1]).split("_")[-1].replace(".json", ""))
    return (datetime.now().date() - d).days if d else None


def result_from_snapshot(snap: dict):
    """
    Rebuild a GradeResult from a stored snapshot.

    This matters for correctness, not just speed. Writing to the workbook must
    use the EXACT scores that were reviewed in the update CSV. Re-grading at
    write time would re-fetch live data, so a price or estimate that moved
    overnight could put a different number in the cell than the one signed off.
    """
    from .scoring import CategoryScore, GradeResult, SubScore

    g = snap.get("grade", {})
    categories = {}
    for ckey, cd in (g.get("categories") or {}).items():
        subs = [SubScore(**{k: v for k, v in s.items()
                            if k in SubScore.__dataclass_fields__})
                for s in cd.get("subscores", [])]
        categories[ckey] = CategoryScore(
            key=cd.get("key", ckey),
            display=cd.get("display", ckey),
            score=cd.get("score"),
            raw_median=cd.get("raw_median"),
            subscores=subs,
            caps_applied=cd.get("caps_applied", []),
            confidence=cd.get("confidence", "medium"),
            sheet_row_offset=cd.get("sheet_row_offset", 0),
            source=cd.get("source", "auto"),
            note=cd.get("note", ""),
        )

    return GradeResult(
        ticker=g.get("ticker", snap.get("ticker", "")),
        archetype=g.get("archetype", "B"),
        archetype_name=g.get("archetype_name", ""),
        archetype_evidence=g.get("archetype_evidence", []),
        categories=categories,
        composite=g.get("composite"),
        composite_arithmetic=g.get("composite_arithmetic", ""),
        red_flags=g.get("red_flags", []),
        not_checkable=g.get("not_checkable", []),
        uninvestable=g.get("uninvestable", False),
        confidence_overall=g.get("confidence_overall", "medium"),
        open_questions=g.get("open_questions", []),
        warnings=g.get("warnings", []),
    )


# =========================================================================== #
# Workbook cell mapping
# =========================================================================== #
def block_header_row(block_index: int) -> int:
    """1-based block index -> header row of that block in 'Individual grading'."""
    return FIRST_BLOCK_HEADER_ROW + BLOCK_HEIGHT * (block_index - 1)


def category_cell(block_index: int, row_offset: int, col: str = SCORE_COL) -> str:
    """Cell address for one category of one stock. row_offset is 1..10."""
    return f"{col}{block_header_row(block_index) + row_offset}"


def build_block_index(ticker_order: list) -> dict:
    """Map ticker -> 1-based block index, following the workbook's own order."""
    return {t.upper(): i + 1 for i, t in enumerate(ticker_order)}


# =========================================================================== #
# Diff engine
# =========================================================================== #
def _sub_lookup(cat_dict: dict) -> dict:
    return {s["key"]: s for s in cat_dict.get("subscores", [])}


def _describe_crossing(old_sub: dict, new_sub: dict) -> Optional[str]:
    """
    Explain a single sub-metric move in the form the user asked for:
    'ROIC 3yr avg dropped from 14.2% to 12.8%, crossing the B/C threshold'.
    """
    if not old_sub or not new_sub:
        return None
    ov, nv = old_sub.get("value"), new_sub.get("value")
    og, ng = old_sub.get("grade"), new_sub.get("grade")
    unit = new_sub.get("unit", "ratio")
    label = new_sub.get("label", new_sub.get("key", "?"))

    if og == ng:
        return None
    if ov is None or nv is None:
        if ov is None and nv is not None:
            return f"{label} became available ({fmt_unit(nv, unit)}) -> {ng}"
        if nv is None and ov is not None:
            return f"{label} became unavailable (was {fmt_unit(ov, unit)}, {og}) -> excluded"
        return None

    verb = "rose" if nv > ov else "dropped"

    # Name the boundary that was actually crossed, not the band landed in.
    # `next_boundary` on a subscore is the threshold for one grade ABOVE the
    # grade awarded -- so on a downgrade it is exactly the line just breached,
    # and on an upgrade it is the next line still ahead.
    if _GRADE_ORDER.get(ng, 0) < _GRADE_ORDER.get(og, 0):
        crossed = new_sub.get("next_boundary")
        edge = (f"crossing the {og}/{ng} threshold at {fmt_unit(crossed, unit)}"
                if crossed is not None
                else f"crossing the {og}/{ng} threshold")
    else:
        crossed = old_sub.get("next_boundary")
        edge = (f"clearing the {og}/{ng} threshold at {fmt_unit(crossed, unit)}"
                if crossed is not None
                else f"clearing the {og}/{ng} threshold")

    return (f"{label} {verb} from {fmt_unit(ov, unit)} to {fmt_unit(nv, unit)}, {edge}")


def diff_snapshots(old: dict, new: dict, block_index: Optional[int] = None) -> dict:
    """
    Compare two snapshots. Returns
      {ticker, composite_change, category_changes[], flag_changes[], lines[]}
    Each category change carries the workbook cell so it is directly actionable.
    """
    ticker = new["ticker"]
    og, ng = old.get("grade", {}), new.get("grade", {})
    out = {
        "ticker": ticker,
        "old_date": old.get("run_date", "")[:10],
        "new_date": new.get("run_date", "")[:10],
        "composite_change": None,
        "archetype_change": None,
        "category_changes": [],
        "watch_items": [],          # sub-metric moves that did NOT shift the score
        "flag_changes": [],
        "lines": [],
    }

    # ---- archetype
    if og.get("archetype") != ng.get("archetype"):
        out["archetype_change"] = {"old": og.get("archetype"), "new": ng.get("archetype")}
        out["lines"].append(
            f"{ticker} ARCHETYPE {og.get('archetype')} -> {ng.get('archetype')}: "
            f"weights change, composite is not comparable to the prior run")

    # ---- composite
    oc, nc = og.get("composite"), ng.get("composite")
    if oc is not None and nc is not None and abs(oc - nc) >= 0.01:
        out["composite_change"] = {"old": oc, "new": nc, "delta": round(nc - oc, 2)}

    # ---- per-category, with the driving sub-metric named
    for ckey, ncat in ng.get("categories", {}).items():
        ocat = og.get("categories", {}).get(ckey)
        if not ocat:
            continue
        os_, ns_ = ocat.get("score"), ncat.get("score")
        old_subs, new_subs = _sub_lookup(ocat), _sub_lookup(ncat)

        if os_ == ns_:
            # The category held, but a sub-metric may still have crossed a band.
            # Median aggregation is deliberately robust to one metric moving, so
            # these crossings are the leading indicator -- surface them or the
            # deterioration stays invisible until the second one tips the median.
            for sk, nsub in new_subs.items():
                d = _describe_crossing(old_subs.get(sk), nsub)
                if not d:
                    continue
                osub = old_subs.get(sk, {})
                worse = _GRADE_ORDER.get(nsub.get("grade"), 9) < \
                    _GRADE_ORDER.get(osub.get("grade"), 9)
                item = {
                    "category": ncat.get("display"),
                    "category_key": ckey,
                    "submetric": nsub.get("label"),
                    "old_grade": osub.get("grade"),
                    "new_grade": nsub.get("grade"),
                    "direction": "worse" if worse else "better",
                    "detail": d,
                    "score_held_at": ns_,
                }
                out["watch_items"].append(item)
                out["lines"].append(
                    f"{ticker} WATCH {ncat.get('display')} (score held at {ns_}): {d}")
            continue

        drivers = []
        for sk, nsub in new_subs.items():
            d = _describe_crossing(old_subs.get(sk), nsub)
            if d:
                drivers.append(d)

        # A cap or an override can move a score with no sub-metric moving at all.
        new_caps = [c for c in ncat.get("caps_applied", [])
                    if c not in ocat.get("caps_applied", [])]
        drivers.extend(f"NEW CAP: {c}" for c in new_caps)
        if ocat.get("source") != ncat.get("source"):
            drivers.append(f"source changed {ocat.get('source')} -> {ncat.get('source')}")
        if not drivers:
            drivers.append("median of available sub-metrics shifted without a "
                           "single band crossing")

        cell = category_cell(block_index, ncat.get("sheet_row_offset", 0)) if block_index else ""
        rcell = (category_cell(block_index, ncat.get("sheet_row_offset", 0), REASON_COL)
                 if block_index else "")

        change = {
            "category": ncat.get("display"),
            "category_key": ckey,
            "old_score": os_,
            "new_score": ns_,
            "direction": "up" if (ns_ or 0) > (os_ or 0) else "down",
            "drivers": drivers,
            "cell": cell,
            "reason_cell": rcell,
            "confidence": ncat.get("confidence"),
            "source": ncat.get("source"),
        }
        out["category_changes"].append(change)
        out["lines"].append(
            f"{ticker} {ncat.get('display')} {os_} -> {ns_}"
            + (f"  [cell {cell}]" if cell else "")
            + ": " + "; ".join(drivers))

    # ---- red flags
    old_ids = {f["id"] for f in og.get("red_flags", [])}
    for f in ng.get("red_flags", []):
        if f["id"] not in old_ids:
            out["flag_changes"].append({"status": "NEW", **f})
            out["lines"].append(f"{ticker} NEW {f['severity']} FLAG "
                                f"[{f['category']}]: {f['message']}")
    new_ids = {f["id"] for f in ng.get("red_flags", [])}
    for f in og.get("red_flags", []):
        if f["id"] not in new_ids:
            out["flag_changes"].append({"status": "CLEARED", **f})
            out["lines"].append(f"{ticker} CLEARED {f['severity']} flag "
                                f"[{f['category']}]: {f['message']}")

    if ng.get("uninvestable") and not og.get("uninvestable"):
        out["lines"].append(f"{ticker} *** NOW UNINVESTABLE *** (2+ RED flags)")

    return out


# =========================================================================== #
# Spreadsheet-ready output
# =========================================================================== #
def write_update_csv(diffs: list, path: Optional[str] = None) -> str:
    """
    One row per changed category, with the exact cell to edit. Open this next to
    the workbook and work down it -- or feed it to excel.py to apply directly.
    """
    path = path or os.path.join(REPORT_DIR, f"updates_{today_str()}.csv")
    cols = ["ticker", "block_row", "category", "cell", "old_score", "new_score",
            "delta", "reason_cell", "reason_text", "confidence", "source", "action"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in diffs:
            for ch in d["category_changes"]:
                reason = "; ".join(ch["drivers"])
                w.writerow({
                    "ticker": d["ticker"],
                    "block_row": ch["cell"][1:] if ch["cell"] else "",
                    "category": ch["category"],
                    "cell": ch["cell"],
                    "old_score": ch["old_score"],
                    "new_score": ch["new_score"],
                    "delta": (ch["new_score"] or 0) - (ch["old_score"] or 0),
                    "reason_cell": ch["reason_cell"],
                    "reason_text": reason[:900],
                    "confidence": ch["confidence"],
                    "source": ch["source"],
                    "action": ("REVIEW - manual override in place"
                               if ch["source"] == "manual"
                               else "APPLY"),
                })
            # Watch items carry no cell edit -- the score did not move -- but
            # they belong in the same sheet so nothing gets lost.
            for wi in d.get("watch_items", []):
                w.writerow({
                    "ticker": d["ticker"],
                    "block_row": "",
                    "category": wi["category"],
                    "cell": "",
                    "old_score": wi["score_held_at"],
                    "new_score": wi["score_held_at"],
                    "delta": 0,
                    "reason_cell": "",
                    "reason_text": wi["detail"][:900],
                    "confidence": "",
                    "source": "watch",
                    "action": ("NO EDIT - monitor (sub-metric deteriorating)"
                               if wi["direction"] == "worse"
                               else "NO EDIT - monitor (sub-metric improving)"),
                })
    LOG.info("update sheet written -> %s", path)
    return path


def write_full_score_csv(results: dict, block_index: dict,
                         path: Optional[str] = None) -> str:
    """Every current score with its cell -- a full paste-in refresh of the workbook."""
    path = path or os.path.join(REPORT_DIR, f"full_scores_{today_str()}.csv")
    cols = ["ticker", "block_index", "archetype", "category", "cell", "score",
            "reason_cell", "reason_text", "confidence", "source",
            "composite_0_10", "composite_0_100"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for tk, res in results.items():
            bi = block_index.get(tk.upper())
            for ckey, cat in res.categories.items():
                reason_bits = [s.audit().strip() for s in cat.subscores
                               if s.status == "scored"]
                reason = cat.note or " | ".join(reason_bits)
                w.writerow({
                    "ticker": tk,
                    "block_index": bi or "",
                    "archetype": res.archetype_name,
                    "category": cat.display,
                    "cell": category_cell(bi, cat.sheet_row_offset) if bi else "",
                    "score": cat.score,
                    "reason_cell": (category_cell(bi, cat.sheet_row_offset, REASON_COL)
                                    if bi else ""),
                    "reason_text": reason[:900],
                    "confidence": cat.confidence,
                    "source": cat.source,
                    "composite_0_10": res.composite,
                    "composite_0_100": (res.composite * 10) if res.composite else "",
                })
    LOG.info("full score sheet written -> %s", path)
    return path


# =========================================================================== #
# Re-grade triggers
# =========================================================================== #
def evaluate_triggers(ticker: str, metrics, settings: dict,
                      prev: Optional[dict] = None) -> dict:
    """
    Decide whether this ticker needs a full re-grade. Returns
    {regrade: bool, reasons: [...], sentiment_only: bool}.
    """
    reasons: list = []

    # (a) earnings released, or about to be
    ed = parse_date(metrics.get("next_earnings_date").note)
    if ed:
        delta = (ed - datetime.now().date()).days
        if abs(delta) <= settings.get("earnings_window_days", 5):
            reasons.append(f"earnings date {ed} is {abs(delta)}d "
                           f"{'away' if delta >= 0 else 'past'}")

    # (b) FY2 consensus moved materially
    fy2 = metrics.val("fy2_eps_change_3mo")
    thr = settings.get("fy2_move_trigger", 0.10)
    if fy2 is not None and abs(fy2) > thr:
        reasons.append(f"FY2 consensus moved {fy2:+.1%} (trigger {thr:.0%})")

    # (c) price / volume anomaly
    p30 = metrics.val("price_change_30d")
    if p30 is not None and p30 <= settings.get("price_drawdown_trigger", -0.20):
        reasons.append(f"30-session drawdown {p30:.1%}")
    vs = metrics.val("volume_spike")
    if vs is not None and vs >= settings.get("volume_spike_trigger", 3.0):
        reasons.append(f"volume {vs:.1f}x its 30-session median")

    # (d) fundamentals moved vs the last snapshot
    if prev:
        prev_metrics = prev.get("metrics", {})
        for field, tol, label in (("revenue_ltm", 0.05, "LTM revenue"),
                                  ("net_debt_to_ebitda", 0.20, "net debt/EBITDA"),
                                  ("fcf", 0.15, "LTM FCF")):
            old = (prev_metrics.get(field) or {}).get("value")
            new = metrics.val(field)
            ch = pct_change(new, old)
            if ch is not None and abs(ch) > tol:
                reasons.append(f"{label} moved {ch:+.1%} since last snapshot")

    # (e) staleness
    age = snapshot_age_days(ticker)
    max_age = settings.get("max_snapshot_age_days", 100)
    if age is None:
        reasons.append("no prior snapshot -- first full grade")
    elif age > max_age:
        reasons.append(f"last grade is {age}d old (max {max_age}d)")

    return {"regrade": bool(reasons), "reasons": reasons,
            "sentiment_only": not bool(reasons)}


def log_sentiment_only(ticker: str, metrics) -> dict:
    """Cheap weekly row when no re-grade trigger fired."""
    row = {
        "ticker": ticker,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "price": metrics.val("price"),
        "short_pct_float": metrics.val("short_pct_float"),
        "short_ratio_days": metrics.val("short_ratio_days"),
        "held_pct_institutions": metrics.val("held_pct_institutions"),
        "institutional_trend": metrics.val("institutional_trend_score"),
        "insider_net_score": metrics.val("insider_net_score"),
        "median_price_target": metrics.val("median_price_target"),
        "analyst_count": metrics.val("analyst_count"),
        "fy2_eps_change_3mo": metrics.val("fy2_eps_change_3mo"),
    }
    path = os.path.join(REPORT_DIR, "sentiment_log.csv")
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)
    return row
