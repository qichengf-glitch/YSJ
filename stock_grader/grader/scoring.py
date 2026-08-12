"""
scoring.py -- the deterministic engine. No LLM touches anything in this file.

Design: a generic band evaluator driven entirely by rubric.yaml. The engine
knows how to apply a threshold ladder, take a median, and apply caps. It knows
nothing about finance. That keeps the rubric editable without code changes and
makes the whole thing unit-testable against fixtures.

Every scored sub-metric emits an audit line naming the value, the band it fell
into, and the boundary it sits nearest -- which is what makes the diff engine
able to say "crossed the B/C threshold at 13%".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .metrics import MetricSet
from .util import LOG, fmt_unit, median


# =========================================================================== #
# Result containers
# =========================================================================== #
@dataclass
class SubScore:
    key: str
    label: str
    value: Optional[float]
    unit: str
    grade: Optional[str]          # A/B/C/D/F, or None when skipped/missing
    points: Optional[float]
    band_desc: str = ""           # e.g. "band: >=13.0%"
    next_boundary: Optional[float] = None   # nearest threshold, for diff messages
    next_grade: Optional[str] = None
    status: str = "scored"        # scored | missing | skipped
    source: str = ""
    period: str = ""
    adjustments: list = field(default_factory=list)

    def audit(self) -> str:
        if self.status == "missing":
            return f"    {self.label:<42} data missing  -> excluded"
        if self.status == "skipped":
            return f"    {self.label:<42} skipped ({self.band_desc})"
        adj = ("  [" + "; ".join(self.adjustments) + "]") if self.adjustments else ""
        return (f"    {self.label:<42} {fmt_unit(self.value, self.unit):>14}"
                f"  -> {self.grade} ({self.points:.1f})   {self.band_desc}{adj}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CategoryScore:
    key: str
    display: str
    score: Optional[int]
    raw_median: Optional[float]
    subscores: list = field(default_factory=list)
    caps_applied: list = field(default_factory=list)
    confidence: str = "medium"
    sheet_row_offset: int = 0
    source: str = "auto"          # auto | manual | tier3
    note: str = ""

    def audit(self) -> str:
        head = (f"  {self.display.upper()} = "
                f"{self.score if self.score is not None else 'n/a'}"
                f"   [confidence: {self.confidence}, source: {self.source}]")
        lines = [head] + [s.audit() for s in self.subscores]
        scored = [s.points for s in self.subscores if s.status == "scored"]
        if scored:
            lines.append(f"    {'median of ' + str([round(p,1) for p in scored]):<42} "
                         f"= {self.raw_median:.2f}")
        for c in self.caps_applied:
            lines.append(f"    CAP -> {c}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["subscores"] = [s.to_dict() for s in self.subscores]
        return d


@dataclass
class GradeResult:
    ticker: str
    archetype: str
    archetype_name: str
    archetype_evidence: list
    categories: dict                      # key -> CategoryScore
    composite: Optional[float]
    composite_arithmetic: str
    red_flags: list
    not_checkable: list
    uninvestable: bool
    confidence_overall: str
    open_questions: list
    warnings: list

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "archetype": self.archetype,
            "archetype_name": self.archetype_name,
            "archetype_evidence": self.archetype_evidence,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "composite": self.composite,
            "composite_arithmetic": self.composite_arithmetic,
            "red_flags": self.red_flags,
            "not_checkable": self.not_checkable,
            "uninvestable": self.uninvestable,
            "confidence_overall": self.confidence_overall,
            "open_questions": self.open_questions,
            "warnings": self.warnings,
        }


# =========================================================================== #
# Expression evaluation for rubric `when:` / `skip_if:` clauses
# =========================================================================== #
_SAFE_BUILTINS = {"abs": abs, "min": min, "max": max, "round": round,
                  "len": len, "True": True, "False": False, "None": None}


def eval_expr(expr: str, ns: dict) -> bool:
    """Evaluate a rubric condition against the metric namespace.

    A missing name resolves to None rather than raising, so a condition that
    depends on absent data is simply False instead of blowing up the run.
    """
    if not expr:
        return False
    try:
        return bool(eval(expr, {"__builtins__": _SAFE_BUILTINS}, dict(ns)))  # noqa: S307
    except (NameError, TypeError, AttributeError, ZeroDivisionError):
        return False
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("rubric expression failed (%s): %s", expr, e)
        return False


def fmt_message(template: str, ns: dict) -> str:
    """Render a red-flag message, tolerating any missing field."""
    try:
        return template.format(**{k: (v if v is not None else "n/a") for k, v in ns.items()})
    except (KeyError, ValueError, TypeError):
        return template


# =========================================================================== #
# Band evaluation
# =========================================================================== #
def evaluate_band(value: float, bands: list, else_grade: str,
                  direction: str, unit: str) -> tuple:
    """
    Walk the ladder best-grade-first and return
    (grade, band_desc, next_boundary, next_grade).

    `next_boundary` is the threshold immediately above the grade awarded --
    i.e. what the value would have to reach for the next grade up. The diff
    engine uses it to say which boundary a metric crossed.
    """
    cmp_ = (lambda v, t: v >= t) if direction == "higher_better" else (lambda v, t: v <= t)
    op = ">=" if direction == "higher_better" else "<="

    for i, (threshold, grade) in enumerate(bands):
        if cmp_(value, threshold):
            nxt_b, nxt_g = (bands[i - 1][0], bands[i - 1][1]) if i > 0 else (None, None)
            return grade, f"band: {op} {fmt_unit(threshold, unit)}", nxt_b, nxt_g

    last_t, last_g = bands[-1]
    fail_op = "<" if direction == "higher_better" else ">"
    return (else_grade, f"band: {fail_op} {fmt_unit(last_t, unit)}", last_t, last_g)


def notch(grade: str, direction: int) -> str:
    """Move a letter grade one notch. direction=-1 down, +1 up."""
    order = ["F", "D", "C", "B", "A"]
    i = order.index(grade)
    return order[max(0, min(len(order) - 1, i + direction))]


# =========================================================================== #
# Category scoring
# =========================================================================== #
def score_category(cat_key: str, cat_cfg: dict, ms: MetricSet, rubric: dict,
                   archetype: str) -> CategoryScore:
    gp = rubric["grade_points"]
    ns = ms.namespace()

    # Archetype override swaps the entire sub-metric set for this category.
    submetrics = cat_cfg.get("submetrics", {})
    overrides = cat_cfg.get("archetype_overrides", {})
    if archetype in overrides:
        submetrics = overrides[archetype]

    subs: list = []
    for sk, scfg in submetrics.items():
        field_name = scfg["field"]
        metric = ms.get(field_name)
        unit = scfg.get("unit", "ratio")

        # -- skip_if (e.g. no P/E when EPS <= 0)
        if scfg.get("skip_if") and eval_expr(scfg["skip_if"], ns):
            subs.append(SubScore(sk, scfg["label"], metric.value, unit, None, None,
                                 band_desc=f"skip_if: {scfg['skip_if']}",
                                 status="skipped", source=metric.source,
                                 period=metric.period))
            continue

        # -- genuinely absent data is excluded, never estimated
        if metric.missing:
            subs.append(SubScore(sk, scfg["label"], None, unit, None, None,
                                 status="missing", source=metric.source,
                                 period=metric.period,
                                 band_desc=metric.note))
            continue

        grade, desc, nb, ng = evaluate_band(metric.value, scfg["bands"],
                                            scfg.get("else", "F"),
                                            scfg.get("direction", "higher_better"), unit)
        adjustments: list = []

        # -- demote_if: condition that blocks a specific top grade
        if scfg.get("demote_if") and grade == scfg.get("demote_from") \
                and eval_expr(scfg["demote_if"], ns):
            grade = scfg.get("demote_to", notch(grade, -1))
            adjustments.append(f"demoted to {grade}: {scfg['demote_if']}")

        # -- notch_down_if: unconditional one-notch penalty
        if scfg.get("notch_down_if") and eval_expr(scfg["notch_down_if"], ns):
            old = grade
            grade = notch(grade, -1)
            adjustments.append(f"notched {old}->{grade}: {scfg['notch_down_if']}")

        subs.append(SubScore(sk, scfg["label"], metric.value, unit, grade, gp[grade],
                             band_desc=desc, next_boundary=nb, next_grade=ng,
                             status="scored", source=metric.source,
                             period=metric.period, adjustments=adjustments))

    # ---- aggregate: MEDIAN of available sub-metric points
    pts = [s.points for s in subs if s.status == "scored"]
    raw = median(pts)

    # ---- category-level notch-down (e.g. any customer >10% in Business Quality)
    caps: list = []
    if cat_cfg.get("notch_down_if") and raw is not None and eval_expr(cat_cfg["notch_down_if"], ns):
        raw = max(1.0, raw - 2.0)                 # one notch == 2 points on this scale
        caps.append(f"one notch down: {cat_cfg['notch_down_if']}")

    # ---- category caps from rubric.yaml
    for cap in cat_cfg.get("caps", []):
        if raw is not None and eval_expr(cap["when"], ns) and raw > cap["cap_at"]:
            caps.append(f"capped at {cap['cap_at']} ({cap['reason']})")
            raw = float(cap["cap_at"])

    score = None
    if raw is not None:
        score = int(max(rubric["score_min"],
                        min(rubric["score_max"], math.floor(raw + 0.5))))

    # ---- confidence from how much of the rubric we could actually evaluate
    n_possible = len(submetrics)
    n_scored = len(pts)
    if n_scored == 0:
        conf = "none"
    elif n_scored >= max(3, n_possible - 1):
        conf = "high"
    elif n_scored >= 2:
        conf = "medium"
    else:
        conf = "low"

    disp = ms.val("estimate_dispersion")
    if cat_key == "eps_revisions" and disp is not None and disp > 0.40 and conf != "none":
        conf = {"high": "medium", "medium": "low", "low": "low"}[conf]

    return CategoryScore(cat_key, cat_cfg["display"], score, raw, subs, caps, conf,
                         cat_cfg.get("sheet_row_offset", 0),
                         source="auto" if cat_cfg.get("tier") != 3 else "tier3")


# =========================================================================== #
# Archetype classification (Section 2 decision tree)
# =========================================================================== #
def classify_archetype(ms: MetricSet, pinned: Optional[str] = None) -> tuple:
    """Return (letter, evidence_lines). A pinned archetype short-circuits."""
    if pinned:
        return pinned, [f"archetype pinned to {pinned} in universe.yaml"]

    ev: list = []
    sector = ms.get("sector").note or ""
    industry = ms.get("industry").note or ""
    rev = ms.val("revenue_ltm")
    fcf = ms.val("fcf")
    growth = ms.val("fwd_revenue_growth")
    worst = ms.val("worst_year_revenue_change")
    gm = ms.val("gross_margin")
    mcap = ms.val("market_cap")

    fin_words = ("bank", "insur", "financial", "capital markets", "credit",
                 "mortgage", "asset management", "lending")
    if any(w in (sector + " " + industry).lower() for w in fin_words):
        ev.append(f"sector/industry = '{sector} / {industry}' (yfinance.info)")
        return "F", ev

    bio_words = ("biotechnology", "pharmaceutical", "drug manufacturers")
    is_bio_sector = any(w in industry.lower() for w in bio_words)
    tiny_revenue = (rev is not None and mcap is not None and mcap > 0 and
                    (rev / mcap) < 0.02)
    if is_bio_sector and (rev is None or rev < 5e7 or tiny_revenue):
        ev.append(f"industry = '{industry}', LTM revenue = "
                  f"{rev if rev is not None else 'n/a'} (immaterial vs market cap)")
        return "E", ev

    if growth is not None and growth > 0.20:
        ev.append(f"fwd revenue growth = {growth:.1%} (>20%)")
        if fcf is None or fcf <= 0 or (rev and fcf / rev < 0.05):
            ev.append(f"FCF = {fcf if fcf is not None else 'n/a'} "
                      "(negative or barely positive)")
            return "C", ev
        ev.append(f"FCF = {fcf:,.0f} (solidly positive)")
        return "B", ev

    if worst is not None and worst < -0.20:
        ev.append(f"revenue fell {worst:.1%} in the weakest year shown (>20% drawdown)")
        return "D", ev

    if growth is not None and growth < 0.08:
        if (gm is not None and gm > 0.35) and (fcf is not None and fcf > 0):
            ev.append(f"fwd growth = {growth:.1%} (<8%), gross margin = {gm:.1%}, "
                      f"FCF positive = {fcf:,.0f}")
            return "A", ev

    ev.append(f"no other branch matched (fwd growth = "
              f"{growth if growth is not None else 'n/a'}) -> default")
    return "B", ev


# =========================================================================== #
# Red flags
# =========================================================================== #
def check_red_flags(ms: MetricSet, rubric: dict) -> tuple:
    ns = ms.namespace()
    triggered: list = []
    for flag in rubric.get("red_flags", []):
        if eval_expr(flag["when"], ns):
            triggered.append({
                "id": flag["id"],
                "severity": flag["severity"],
                "category": flag["category"],
                "message": fmt_message(flag["message"], ns),
            })

    not_checkable = list(rubric.get("not_checkable_flags", []))
    # A flag whose input metric is missing is unverified, not clean.
    for flag in rubric.get("red_flags", []):
        if any(f["id"] == flag["id"] for f in triggered):
            continue
        needed = [w for w in ns.keys() if w in flag["when"]]
        if needed and all(ns.get(n) is None for n in needed):
            not_checkable.append(f"{flag['id']} (inputs missing: {', '.join(needed)})")
    return triggered, not_checkable


def apply_red_flag_caps(categories: dict, flags: list) -> tuple:
    """YELLOW caps its category at 6, RED at 2 and the composite at 6.0.

    The RED count is taken from the flags themselves, NOT from whichever caps
    happened to land. A RED flag on a category that could not be scored is
    still a RED flag -- it must count toward UNINVESTABLE, or a name with
    missing data could dodge the rule by being unscoreable.
    """
    reds = sum(1 for f in flags if f["severity"] == "RED")
    composite_cap = 6.0 if reds else None

    for f in flags:
        cat = categories.get(f["category"])
        if cat is None or cat.score is None:
            continue
        if f["severity"] == "YELLOW" and cat.score > 6:
            cat.caps_applied.append(f"YELLOW flag '{f['id']}' caps category at 6")
            cat.score = 6
        elif f["severity"] == "RED" and cat.score > 2:
            cat.caps_applied.append(f"RED flag '{f['id']}' caps category at 2")
            cat.score = 2
    return composite_cap, reds


# =========================================================================== #
# Composite
# =========================================================================== #
def compute_composite(categories: dict, archetype: str, rubric: dict,
                      composite_cap: Optional[float] = None) -> tuple:
    """
    Weighted sum on a 0-10 scale (the workbook multiplies by 10 for 0-100).

    If a category could not be scored at all, its weight is redistributed
    pro-rata across the categories that were scored, so a single missing
    category does not silently drag the composite toward zero.
    """
    weights = dict(rubric["archetypes"][archetype]["weights"])

    usable = {k: w for k, w in weights.items()
              if categories.get(k) and categories[k].score is not None and w > 0}
    if not usable:
        return None, "no scoreable categories"

    total_w = sum(usable.values())
    parts, terms = [], []
    for k, w in usable.items():
        norm = w / total_w
        s = categories[k].score
        parts.append(norm * s)
        terms.append(f"{norm:.3f}x{s}")

    composite = sum(parts)
    arithmetic = " + ".join(terms) + f" = {composite:.2f}"
    if total_w < 0.999:
        dropped = [k for k, w in weights.items() if w > 0 and k not in usable]
        arithmetic += (f"   [weights renormalised from {total_w:.2f}; "
                       f"unscored: {', '.join(dropped)}]")

    if composite_cap is not None and composite > composite_cap:
        arithmetic += f"   [RED-flag cap applied at {composite_cap}]"
        composite = composite_cap
    return round(composite, 2), arithmetic


# =========================================================================== #
# Orchestrator
# =========================================================================== #
def grade(ms: MetricSet, rubric: dict, pinned_archetype: Optional[str] = None,
          manual_overrides: Optional[dict] = None) -> GradeResult:
    archetype, evidence = classify_archetype(ms, pinned_archetype)
    arch_name = rubric["archetypes"][archetype]["name"]

    categories: dict = {}
    for ckey, ccfg in rubric["categories"].items():
        categories[ckey] = score_category(ckey, ccfg, ms, rubric, archetype)

    # Manual overrides win over anything computed -- your judgment is authoritative.
    manual_overrides = manual_overrides or {}
    for ckey, ov in manual_overrides.items():
        if ckey in categories and ov.get("score") is not None:
            c = categories[ckey]
            c.score = int(ov["score"])
            c.source = "manual"
            c.confidence = "high"
            c.note = f"{ov.get('note', '')} [manual override, asof {ov.get('asof', 'n/a')}]"

    flags, not_checkable = check_red_flags(ms, rubric)
    composite_cap, n_red = apply_red_flag_caps(categories, flags)
    composite, arithmetic = compute_composite(categories, archetype, rubric, composite_cap)

    # ---- open questions: what a human should verify before approving
    oq: list = []
    for ckey, c in categories.items():
        missing = [s.label for s in c.subscores if s.status == "missing"]
        if missing:
            oq.append(f"{c.display}: unsourced sub-metrics -- {', '.join(missing)}")
        if c.confidence in ("low", "none"):
            oq.append(f"{c.display}: confidence {c.confidence} "
                      f"({len([s for s in c.subscores if s.status=='scored'])} of "
                      f"{len(c.subscores)} sub-metrics scored)")
    disp = ms.val("estimate_dispersion")
    if disp is not None and disp > 0.40:
        oq.append(f"Analyst estimate dispersion is {disp:.0%} -- the earnings "
                  "picture is poorly understood; widen position sizing.")
    ac = ms.val("analyst_count")
    if ac is not None and ac <= 2:
        oq.append(f"Only {ac:.0f} analyst estimate(s) -- consensus figures are "
                  "one or two people's models, not a consensus.")
    oq.extend(ms.warnings)

    conf_rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
    scored = [c for c in categories.values() if c.score is not None]
    avg_conf = (sum(conf_rank[c.confidence] for c in scored) / len(scored)) if scored else 0
    overall = "high" if avg_conf >= 2.5 else ("medium" if avg_conf >= 1.5 else "low")

    return GradeResult(
        ticker=ms.ticker, archetype=archetype, archetype_name=arch_name,
        archetype_evidence=evidence, categories=categories, composite=composite,
        composite_arithmetic=arithmetic, red_flags=flags, not_checkable=not_checkable,
        uninvestable=(n_red >= 2), confidence_overall=overall,
        open_questions=oq, warnings=ms.warnings,
    )


def render_audit(res: GradeResult) -> str:
    """The full 'explain why' trail. Code proves the score; it does not narrate it."""
    L = [
        "=" * 78,
        f"  {res.ticker}   composite {res.composite}/10  "
        f"({(res.composite or 0) * 10:.1f}/100)"
        + ("   ** UNINVESTABLE **" if res.uninvestable else ""),
        f"  archetype: {res.archetype_name}",
    ]
    for e in res.archetype_evidence:
        L.append(f"      evidence: {e}")
    L.append("=" * 78)
    for c in res.categories.values():
        L.append(c.audit())
        if c.note:
            L.append(f"    note: {c.note}")
        L.append("")
    L.append(f"  COMPOSITE = {res.composite_arithmetic}")
    L.append("")
    if res.red_flags:
        L.append("  RED FLAGS TRIGGERED:")
        for f in res.red_flags:
            L.append(f"    [{f['severity']}] {f['category']}: {f['message']}")
    else:
        L.append("  RED FLAGS: none triggered on checkable inputs")
    if res.not_checkable:
        L.append("  NOT CHECKABLE:")
        for n in res.not_checkable[:12]:
            L.append(f"    - {n}")
    L.append("")
    if res.open_questions:
        L.append("  OPEN QUESTIONS:")
        for q in res.open_questions[:20]:
            L.append(f"    - {q}")
    L.append(f"\n  CONFIDENCE OVERALL: {res.confidence_overall}")
    L.append("=" * 78)
    return "\n".join(L)
