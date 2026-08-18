#!/usr/bin/env python3
"""
run.py -- pipeline entry point.

USAGE
  python run.py --check                       validate config, no network
  python run.py --weekly                      sentiment log + trigger scan only
  python run.py --grade AAOI                  full grade of one ticker
  python run.py --grade-all                   grade everything the triggers queue
  python run.py --grade-all --force           grade everything regardless
  python run.py --grade-all --resume-today    reuse today's completed snapshots
  python run.py --diff AAOI                   diff the two most recent snapshots
  python run.py --report                      write updates CSV for all tickers
  python run.py --write-excel path/to.xlsx    apply scores into a copy
  python run.py --fix-workbook path/to.xlsx   repair the ABVX/AKAM formulas
  python run.py --no-llm                      skip Tier 3 on any of the above

TYPICAL CADENCE
  weekly     python run.py --weekly
  quarterly  python run.py --grade-all && python run.py --report
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grader import excel, peers as peers_mod, state, tier3 as t3    # noqa: E402
from grader.fetch import fetch_all, fetch_sec_latest_filing_text    # noqa: E402
from grader.metrics import build_metrics, peer_snapshot             # noqa: E402
from grader.scoring import grade, render_audit                      # noqa: E402
from grader.util import (LOG, REPORT_DIR, load_rubric, load_universe,  # noqa: E402
                         today_str)

_PEER_CACHE: dict = {}


# =========================================================================== #
def get_peer_row(peer_ticker: str, sec_ua: str) -> dict:
    """Fetch a peer's three comps fields once per run and cache it."""
    key = peer_ticker.upper()
    if key in _PEER_CACHE:
        return _PEER_CACHE[key]
    try:
        b = fetch_all(peer_ticker, sec_ua, use_sec=False, use_scrape_fallback=False)
        row = peer_snapshot(b)
    except Exception as e:                                     # noqa: BLE001
        LOG.warning("peer %s fetch failed: %s", peer_ticker, e)
        row = {"ticker": key, "ev_ebitda": None, "gross_margin": None,
               "fwd_revenue_growth": None}
    _PEER_CACHE[key] = row
    time.sleep(0.3)                                            # be polite to Yahoo
    return row


def grade_ticker(ticker: str, rubric: dict, universe: dict,
                 use_llm: bool = True, save: bool = True,
                 refresh_peers: bool = False):
    """Fetch -> metrics -> peers -> Tier 3 -> score -> snapshot. Returns
    (GradeResult, MetricSet, tier3_dict) or (None, None, None) on failure."""
    settings = universe.get("settings", {})
    cfg = (universe.get("tickers") or {}).get(ticker.upper(), {}) or {}
    sec_ua = settings.get("sec_user_agent", "Research research@example.com")

    LOG.info("=" * 60)
    LOG.info("GRADING %s", ticker)

    try:
        bundle = fetch_all(ticker, sec_ua)
    except Exception as e:                                     # noqa: BLE001
        LOG.error("[%s] fetch failed entirely: %s", ticker, e)
        return None, None, None

    ms = build_metrics(bundle)
    if bundle.errors:
        for err in bundle.errors:
            ms.warn(f"fetch: {err}")

    # ---- peer comps grid (the Capital IQ comps replacement)
    # The archetype drives peer selection (size bands, minimum count, which
    # multiples apply), so classify first using only non-peer metrics.
    from grader.scoring import classify_archetype
    provisional_arch, _ = classify_archetype(ms, cfg.get("archetype"))
    peer_set = peers_mod.build_peer_set(ticker, bundle, provisional_arch, universe,
                                        force_refresh=refresh_peers)
    print(peer_set.audit())
    peers_mod.apply_peer_set(ms, peer_snapshot(bundle), peer_set,
                             min_peers=int(settings.get("min_peers_to_score", 3)))

    # ---- Tier 3 (narrow LLM extraction), cached for a filing cycle
    tier3_data = {}
    if use_llm and settings.get("llm_enabled", True):
        cached = t3.load_cached_tier3(ticker, settings.get("tier3_max_age_days", 400))
        if cached:
            LOG.info("[%s] using cached Tier 3 from %s", ticker,
                     cached.get("extracted_at", "")[:10])
            tier3_data = cached
        else:
            LOG.info("[%s] fetching latest filing for Tier 3 extraction", ticker)
            text, form, filed, url = fetch_sec_latest_filing_text(ticker, sec_ua)
            if text:
                tier3_data = t3.extract_tier3(ticker, text, form, filed,
                                              model=settings.get("llm_model",
                                                                 "claude-sonnet-4-6"))
                tier3_data["source_url"] = url
                t3.save_tier3(ticker, tier3_data)
            else:
                ms.warn("no SEC filing text retrieved -- Tier 3 fields unsourced")
        if tier3_data:
            t3.apply_tier3_to_metrics(ms, tier3_data)
            for f in tier3_data.get("review_flags", []):
                ms.warn(f"tier3: {f}")

    # ---- score
    result = grade(ms, rubric,
                   pinned_archetype=cfg.get("archetype"),
                   manual_overrides=(universe.get("overrides") or {}).get(ticker.upper()))

    print(render_audit(result))

    if save:
        state.save_snapshot(ticker, result, ms, tier3_data)
    return result, ms, tier3_data


# =========================================================================== #

def cmd_peers(ticker: str, universe: dict, rubric: dict, refresh: bool) -> int:
    """Show the discovered peer set for one ticker without grading it."""
    settings = universe.get("settings", {})
    sec_ua = settings.get("sec_user_agent", "Research research@example.com")
    cfg = (universe.get("tickers") or {}).get(ticker.upper(), {}) or {}

    bundle = fetch_all(ticker, sec_ua, use_sec=False, use_scrape_fallback=False)
    ms = build_metrics(bundle)
    from grader.scoring import classify_archetype
    arch, _ = classify_archetype(ms, cfg.get("archetype"))

    ps = peers_mod.build_peer_set(ticker, bundle, arch, universe, force_refresh=refresh)
    print()
    print(ps.audit())

    own = peer_snapshot(bundle)
    print(f"\n    subject metrics: EV/EBITDA "
          f"{own.get('ev_ebitda') if own.get('ev_ebitda') is None else round(own['ev_ebitda'],1)}x"
          f" | GM {'n/a' if own.get('gross_margin') is None else format(own['gross_margin'],'.1%')}"
          f" | fwd growth "
          f"{'n/a' if own.get('fwd_revenue_growth') is None else format(own['fwd_revenue_growth'],'.1%')}")

    probe = build_metrics(bundle)
    peers_mod.apply_peer_set(probe, own, ps,
                             min_peers=int(settings.get("min_peers_to_score", 3)))
    print("\n    resulting sub-metrics:")
    for f in ("tev_ebitda_discount_vs_peers", "gm_percentile_vs_peers",
              "peer_median_fwd_growth"):
        m = probe.get(f)
        print(f"      {f:<34} {m.cite()}")
        if m.note:
            print(f"        {m.note}")
    print()
    return 0


def cmd_refresh_peers(universe: dict, rubric: dict) -> int:
    """Rebuild every peer set, then export them all for review."""
    settings = universe.get("settings", {})
    sec_ua = settings.get("sec_user_agent", "Research research@example.com")
    from grader.scoring import classify_archetype

    for ticker in (universe.get("tickers") or {}):
        cfg = (universe["tickers"].get(ticker) or {})
        try:
            bundle = fetch_all(ticker, sec_ua, use_sec=False, use_scrape_fallback=False)
            ms = build_metrics(bundle)
            arch, _ = classify_archetype(ms, cfg.get("archetype"))
            ps = peers_mod.build_peer_set(ticker, bundle, arch, universe,
                                          force_refresh=True)
            LOG.info("[%s] %d peers: %s", ticker, len(ps.peers),
                     ", ".join(ps.tickers))
        except Exception as e:                                 # noqa: BLE001
            LOG.error("[%s] peer discovery failed: %s", ticker, e)
        time.sleep(0.5)

    path = peers_mod.export_peers_yaml()
    print(f"\n  Peer sets rebuilt. Review: {path}")
    print("  Move any set you want to freeze into universe.yaml under `peers:`.\n")
    return 0


def cmd_check(universe: dict, rubric: dict) -> int:
    """Validate configuration without touching the network."""
    ok = True
    print("\nCONFIG CHECK")
    print("-" * 60)

    for letter, cfg in rubric["archetypes"].items():
        tot = sum(cfg["weights"].values())
        good = abs(tot - 1.0) < 1e-9
        ok &= good
        print(f"  archetype {letter} weights sum to {tot:.3f}  "
              f"{'OK' if good else '*** MUST EQUAL 1.000 ***'}")

    cat_keys = set(rubric["categories"])
    for letter, cfg in rubric["archetypes"].items():
        missing = cat_keys - set(cfg["weights"])
        if missing:
            ok = False
            print(f"  archetype {letter} missing weights for: {sorted(missing)}")

    offsets = [c["sheet_row_offset"] for c in rubric["categories"].values()]
    good = sorted(offsets) == list(range(1, 11))
    ok &= good
    print(f"  sheet row offsets 1-10 unique: {'OK' if good else '*** BROKEN ***'}")

    ua = universe.get("settings", {}).get("sec_user_agent", "")
    good = "@" in ua and "yourfirm" not in ua.lower()
    print(f"  SEC user agent set: {'OK' if good else '*** SET A REAL CONTACT EMAIL ***'}")

    tickers = universe.get("tickers", {}) or {}
    print(f"  tickers configured: {len(tickers)}")
    manual = [t for t, c in tickers.items() if (c or {}).get("peers")]
    auto = [t for t in tickers if t not in manual]
    print(f"  peer sets: {len(manual)} manual, {len(auto)} auto-discovered")
    cached = 0
    for t in tickers:
        if peers_mod.load_cached_peers(t, 100000):
            cached += 1
    print(f"  peer sets cached on disk: {cached}/{len(tickers)}"
          + ("" if cached else "  (run --refresh-peers to build them)"))

    print(f"  ANTHROPIC_API_KEY: "
          f"{'set' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET -- Tier 3 disabled'}")
    print("-" * 60)
    print("PASS\n" if ok else "FAIL -- fix the items marked above\n")
    return 0 if ok else 1


def cmd_weekly(universe: dict, rubric: dict) -> int:
    """Cheap pass: log sentiment, report which tickers the triggers queue."""
    settings = universe.get("settings", {})
    sec_ua = settings.get("sec_user_agent", "Research research@example.com")
    queued = []

    for ticker in (universe.get("tickers") or {}):
        try:
            bundle = fetch_all(ticker, sec_ua, use_sec=False)
            ms = build_metrics(bundle)
        except Exception as e:                                 # noqa: BLE001
            LOG.error("[%s] weekly pass failed: %s", ticker, e)
            continue

        prev = state.load_latest_snapshot(ticker, before_today=False)
        trig = state.evaluate_triggers(ticker, ms, settings, prev)

        if trig["regrade"]:
            queued.append((ticker, trig["reasons"]))
            LOG.info("[%s] QUEUED for re-grade: %s", ticker, "; ".join(trig["reasons"]))
        else:
            state.log_sentiment_only(ticker, ms)
            LOG.info("[%s] no trigger -- sentiment logged only", ticker)
        time.sleep(0.4)

    print("\n" + "=" * 60)
    print(f"  WEEKLY SCAN {datetime.now():%Y-%m-%d}")
    print("=" * 60)
    if queued:
        print(f"  {len(queued)} ticker(s) queued for full re-grade:\n")
        for tk, reasons in queued:
            print(f"    {tk}")
            for r in reasons:
                print(f"      - {r}")
        print(f"\n  Run: python run.py --grade-all")
    else:
        print("  No re-grade triggers fired. Sentiment logged to "
              "data/reports/sentiment_log.csv")
    print("=" * 60 + "\n")
    return 0


def cmd_grade_all(universe: dict, rubric: dict, force: bool, use_llm: bool,
                  resume_today: bool = False) -> int:
    settings = universe.get("settings", {})
    sec_ua = settings.get("sec_user_agent", "Research research@example.com")
    tickers = list((universe.get("tickers") or {}).keys())

    results, diffs = {}, []
    block_index = state.build_block_index(tickers)

    for ticker in tickers:
        if resume_today:
            snap = state.load_snapshot(state.snapshot_path(ticker, today_str()))
            if snap:
                LOG.info("[%s] using today's saved snapshot", ticker)
                results[ticker] = state.result_from_snapshot(snap)
                continue

        if not force:
            try:
                b = fetch_all(ticker, sec_ua, use_sec=False, use_scrape_fallback=False)
                ms_pre = build_metrics(b)
                prev = state.load_latest_snapshot(ticker, before_today=False)
                trig = state.evaluate_triggers(ticker, ms_pre, settings, prev)
                if not trig["regrade"]:
                    LOG.info("[%s] no trigger -- skipping full grade", ticker)
                    state.log_sentiment_only(ticker, ms_pre)
                    continue
                LOG.info("[%s] trigger: %s", ticker, "; ".join(trig["reasons"]))
            except Exception as e:                             # noqa: BLE001
                LOG.warning("[%s] trigger check failed (%s) -- grading anyway", ticker, e)

        prev_snap = state.load_latest_snapshot(ticker, before_today=True)
        res, ms, tier3_data = grade_ticker(ticker, rubric, universe, use_llm=use_llm)
        if res is None:
            continue
        results[ticker] = res

        if prev_snap:
            new_snap = state.load_snapshot(state.snapshot_path(ticker))
            if new_snap:
                d = state.diff_snapshots(prev_snap, new_snap,
                                         block_index.get(ticker.upper()))
                if d["lines"]:
                    diffs.append(d)
        time.sleep(0.5)

    if results:
        state.write_full_score_csv(results, block_index)
    if diffs:
        path = state.write_update_csv(diffs)
        print("\n" + "=" * 78)
        print("  CHANGES SINCE LAST RUN")
        print("=" * 78)
        for d in diffs:
            for line in d["lines"]:
                print("  " + line)
        print(f"\n  Spreadsheet-ready update sheet: {path}")
        print("=" * 78 + "\n")
    else:
        print("\n  No score changes versus the previous snapshots.\n")
    return 0


def cmd_diff(ticker: str, universe: dict) -> int:
    snaps = state.list_snapshots(ticker)
    if len(snaps) < 2:
        print(f"  Need at least 2 snapshots for {ticker}; found {len(snaps)}.")
        return 1
    old, new = state.load_snapshot(snaps[-2]), state.load_snapshot(snaps[-1])
    bi = state.build_block_index(list((universe.get("tickers") or {}).keys()))
    d = state.diff_snapshots(old, new, bi.get(ticker.upper()))

    print("\n" + "=" * 78)
    print(f"  {ticker}   {d['old_date']}  ->  {d['new_date']}")
    print("=" * 78)
    if d["composite_change"]:
        c = d["composite_change"]
        print(f"  COMPOSITE {c['old']} -> {c['new']}  ({c['delta']:+.2f})")
    if not d["lines"]:
        print("  No changes.")
    for line in d["lines"]:
        print("  " + line)
    print("=" * 78 + "\n")
    if d["category_changes"]:
        state.write_update_csv([d])
    return 0


def cmd_report(universe: dict) -> int:
    """Rebuild the updates CSV from the two most recent snapshots of each ticker."""
    bi = state.build_block_index(list((universe.get("tickers") or {}).keys()))
    diffs = []
    for ticker in (universe.get("tickers") or {}):
        snaps = state.list_snapshots(ticker)
        if len(snaps) < 2:
            continue
        d = state.diff_snapshots(state.load_snapshot(snaps[-2]),
                                 state.load_snapshot(snaps[-1]),
                                 bi.get(ticker.upper()))
        if d["lines"]:
            diffs.append(d)
    if not diffs:
        print("  Nothing changed across the stored snapshots.")
        return 0
    path = state.write_update_csv(diffs)
    for d in diffs:
        for line in d["lines"]:
            print("  " + line)
    print(f"\n  Written: {path}")
    return 0


# =========================================================================== #
def main() -> int:
    p = argparse.ArgumentParser(description="Deterministic stock grading pipeline")
    p.add_argument("--check", action="store_true", help="validate config, no network")
    p.add_argument("--weekly", action="store_true", help="sentiment log + trigger scan")
    p.add_argument("--grade", metavar="TICKER", help="full grade of one ticker")
    p.add_argument("--grade-all", action="store_true", help="grade the queued universe")
    p.add_argument("--force", action="store_true", help="ignore triggers")
    p.add_argument("--resume-today", action="store_true",
                   help="reuse any full snapshots already written today")
    p.add_argument("--diff", metavar="TICKER", help="diff two most recent snapshots")
    p.add_argument("--report", action="store_true", help="write the updates CSV")
    p.add_argument("--write-excel", metavar="XLSX", help="apply scores into a copy")
    p.add_argument("--fix-workbook", metavar="XLSX", help="repair ABVX/AKAM formulas")
    p.add_argument("--dry-run", action="store_true", help="with --write-excel, do not save")
    p.add_argument("--no-llm", action="store_true", help="skip Tier 3 extraction")
    p.add_argument("--peers", metavar="TICKER", help="show the discovered peer set")
    p.add_argument("--refresh-peers", action="store_true",
                   help="rebuild every peer set and export for review")
    p.add_argument("--export-peers", action="store_true",
                   help="dump cached peer sets to config/peers_auto.yaml")
    args = p.parse_args()

    rubric, universe = load_rubric(), load_universe()
    use_llm = not args.no_llm

    if args.check:
        return cmd_check(universe, rubric)
    if args.peers:
        return cmd_peers(args.peers, universe, rubric, args.refresh_peers)
    if args.refresh_peers:
        return cmd_refresh_peers(universe, rubric)
    if args.export_peers:
        path = peers_mod.export_peers_yaml()
        print(f"  Exported: {path}")
        return 0
    if args.weekly:
        return cmd_weekly(universe, rubric)
    if args.grade:
        res, _, _ = grade_ticker(args.grade, rubric, universe, use_llm=use_llm,
                                 refresh_peers=args.refresh_peers)
        return 0 if res else 1
    if args.grade_all:
        resume_today = args.resume_today or os.environ.get(
            "STOCK_GRADER_RESUME_TODAY", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        return cmd_grade_all(universe, rubric, args.force, use_llm, resume_today)
    if args.diff:
        return cmd_diff(args.diff, universe)
    if args.report:
        return cmd_report(universe)

    if args.fix_workbook:
        out = excel.fix_workbook_formulas(args.fix_workbook)
        print(f"  Repaired workbook written to: {out}")
        return 0

    if args.write_excel:
        blocks = excel.discover_blocks(args.write_excel)
        results, missing, stale = {}, [], []
        for ticker in (universe.get("tickers") or {}):
            snap = state.load_latest_snapshot(ticker, before_today=False)
            if not snap:
                missing.append(ticker)
                continue
            # Use the stored scores, not a fresh grade: the workbook must get
            # exactly the numbers that appeared in the update CSV you reviewed.
            results[ticker] = state.result_from_snapshot(snap)
            age = state.snapshot_age_days(ticker)
            if age is not None and age > 120:
                stale.append((ticker, age))

        if not results:
            print("  No snapshots found. Run --grade-all --force first.")
            return 1

        print(f"\n  Writing {len(results)} ticker(s) from stored snapshots.")
        if missing:
            print(f"  {len(missing)} never graded, left untouched: "
                  f"{', '.join(missing[:12])}"
                  + (f" ... +{len(missing)-12} more" if len(missing) > 12 else ""))
        if stale:
            print(f"  {len(stale)} snapshot(s) over 120 days old: "
                  + ", ".join(f"{t} ({a}d)" for t, a in stale[:8]))

        out = excel.write_scores(args.write_excel, results, blocks,
                                 overrides=universe.get("overrides"),
                                 dry_run=args.dry_run)
        if args.dry_run:
            print("\n  DRY RUN -- nothing was saved.\n")
        else:
            print(f"\n  Workbook written to: {out}")
            print("  Your original file was not modified.\n")
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
