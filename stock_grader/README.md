# Deterministic Stock Grading Pipeline

Automates the 10-category rubric that was previously run by hand: download Capital IQ
exports, paste them into an LLM with the grading prompt, then edit the judgment
categories manually.

**The core principle: code does the arithmetic, the LLM only reads text.** Every
threshold in the rubric is a lookup table, so every threshold lives in
`config/rubric.yaml` and is applied by `grader/scoring.py`. No model guesses a score.
The LLM is confined to `grader/tier3.py`, where it extracts three numbers and one
evidence grade from a filing — and even those are discarded unless the quote it cites
is verified to exist in the source text.

---

## Setup

```bash
pip install -r requirements.txt

# Required for the SEC EDGAR fallback -- EDGAR blocks requests without a real contact.
# Edit config/universe.yaml -> settings.sec_user_agent

# Optional, for Tier 3 extraction (run --no-llm to skip entirely)
export ANTHROPIC_API_KEY=sk-ant-...

python run.py --check          # validates config, no network calls
python tests/test_scoring.py       # 41 assertions on the scoring engine
python tests/test_peers.py         # 68 assertions on peer discovery
python tests/test_integration.py   # 43 assertions, full pipeline
```

---

## Commands

| Command | What it does |
|---|---|
| `python run.py --check` | Validate config offline. Weights sum to 1.0, row offsets unique, API keys present. |
| `python run.py --peers AAOI` | Show the discovered peer set, rejections, and resulting sub-metrics. |
| `python run.py --refresh-peers` | Rebuild every peer set and export for review. |
| `python run.py --export-peers` | Dump cached peer sets to `config/peers_auto.yaml`. |
| `python run.py --weekly` | Cheap pass. Logs sentiment, reports which tickers the triggers queue. |
| `python run.py --grade AAOI` | Full grade of one ticker with the audit trail printed. |
| `python run.py --grade-all` | Grades only what the triggers queue. |
| `python run.py --grade-all --force` | Grades everything regardless of triggers. |
| `python run.py --diff AAOI` | Diffs the two most recent snapshots. |
| `python run.py --report` | Writes the spreadsheet-ready updates CSV. |
| `python run.py --write-excel wb.xlsx` | Applies scores into a **copy** of the workbook. |
| `python run.py --fix-workbook wb.xlsx` | Repairs the ABVX/AKAM formula bugs (see below). |
| `--no-llm` | Add to any command to skip Tier 3. |

**Cadence:** `run_weekly.sh` on Mondays, `run_quarterly.sh` after earnings season.

---

## Architecture

```
config/rubric.yaml      every threshold, weight, and red flag -- THE rubric
config/universe.yaml    tickers, peer sets, manual overrides, settings

grader/fetch.py         yfinance -> SEC EDGAR XBRL -> stockanalysis fallbacks
grader/metrics.py       raw statements -> ~50 fields, each with provenance
grader/scoring.py       band evaluator, archetype tree, red flags, composite
grader/tier3.py         the ONLY LLM call, narrowly scoped and verified
grader/peers.py         automatic peer discovery + comps grid construction
grader/state.py         snapshots, diff engine, re-grade triggers
grader/excel.py         workbook write-back and formula repair
run.py                  CLI
```

### Data sources

| Source | Role | Notes |
|---|---|---|
| **yfinance** | Primary | Broad and free. Field names drift between versions, so every accessor tries several candidate labels and degrades to `None`. |
| **SEC EDGAR XBRL** | Fallback | The `companyfacts` API — official, free, no key, and literally the filed data. Used whenever yfinance has a hole. Also supplies the 10-K text for Tier 3. |
| **stockanalysis.com** | Last resort | Light scrape of a few ratios. Best-effort; returns `{}` on any failure. |

### Replacing the Capital IQ comps grid — automatic peer discovery

Three sub-metrics need a peer group: fwd TEV/EBITDA vs peer median, gross margin vs
peers, and peer-median forward growth. There is no free comps grid, so `grader/peers.py`
**builds one automatically**. Manual peer lists remain supported and always win, but
they are now optional.

**Governing principle: a median from a bad peer set is worse than `data missing`,
because it looks authoritative.** The module is built to refuse rather than guess.

#### Four candidate sources, then ranking

| Source | What it gives | Cost |
|---|---|---|
| **Yahoo equity screener** | Every listed name in the industry inside a market-cap band. Often returns `lastclosetevebitda` and `grossprofitmargin` directly. | 1 request |
| **`yf.Industry(key).top_companies`** | The largest names in the exact industry. | 1 request |
| **SEC EDGAR SIC** | Every filer sharing the subject's 4-digit SIC, via one `browse-edgar` call, mapped back to tickers through the SEC's own file. | 1 request |
| **Sector screener** | Last resort when the industry is thin. Always warns. | 1 request |

Using several sources matters because **Yahoo's industry taxonomy and the SEC's SIC
codes are independent**. When both name the same company, that agreement is real
evidence — so corroboration across sources is an input to the similarity score.

Candidates are unioned, then ranked on size proximity (log-scale), taxonomy agreement,
SIC agreement, and source corroboration. Weights are archetype-aware: cyclicals weight
size at 0.15 because they compare across a cycle, compounders at 0.35.

#### Hard gates

Rejected before ranking, each with a recorded reason: the subject itself, ETFs and
non-operating quote types, warrant/unit/preferred lines, sub-$50M microcaps, anything
outside the size band, and any candidate with no usable metric at all.

#### Adaptive size band

Real industries are not uniformly sized — a $1.4B name can sit between a $350M and a
$21B peer. A fixed band rejects the large neighbours and starves the metrics. So the
band **doubles until enough peers survive**, up to four attempts. Enrichment is already
paid for, so retrying costs nothing, and **the widening is always disclosed** as a
warning because a wider band is weaker evidence.

#### Per-metric validation — the important part

Validity is checked **per metric, not per peer**. A peer with negative EBITDA cannot
contribute an EV/EBITDA figure, but its gross margin is perfectly good. Discarding the
whole peer would throw away sound data.

Gates: EV/EBITDA must be in 0.5–100x (negative means negative EBITDA; >100x means a
near-zero denominator, not a rich multiple). Gross margin in −50%–100%. Growth in
−90%–500%. Values beyond 1.5×IQR are trimmed and reported.

**Each metric then needs its own minimum of 3 valid peers or it records `data missing`.**
So one ticker routinely scores gross margin from 5 peers while EV/EBITDA is excluded
for having only 2 — exactly the behaviour Section 1 rule 3 demands.

EV/EBITDA is suppressed entirely for archetypes **E** (negative EBITDA) and **F**
(enterprise value is not coherent for a bank).

#### Inspect, correct, freeze

```bash
python run.py --peers AAOI        # show the discovered set and resulting sub-metrics
python run.py --refresh-peers     # rebuild all, export for review
python run.py --export-peers      # dump cached sets to config/peers_auto.yaml
```

`--peers` prints the accepted peers with similarity scores and sources, every rejection
with its reason, per-metric peer counts and confidence, and the three sub-metrics that
result. Anything you disagree with, paste into `universe.yaml` under `peers:` — manual
sets override discovery, bypass the size band, and never expire.

Sets cache for 90 days (`peer_cache_days`); industries move slowly.

---

## What the audit trail looks like

```
  PROFITABILITY = 8   [confidence: high, source: auto]
    ROIC 3-yr average                          14.2%  -> B (7.5)   band: >= 13.0%
    ROIC persistence (share of yrs >12%)       70.0%  -> B (7.5)   band: >= 60.0%
    Gross margin vs peer set                   62.0%  -> B (7.5)   band: >= 55.0%
    Return on equity                           17.0%  -> B (7.5)   band: >= 15.0%
    median of [7.5, 7.5, 7.5, 7.5]           = 7.50

  COMPOSITE = 0.150x8 + 0.150x8 + ... = 8.35
```

Code proves the score rather than narrating it. Every figure carries a source and a
period, matching the "cite everything" rule from the original prompt.

---

## The diff engine

The pipeline's real output is not 90 fresh scores — it is the handful that moved and
why. `data/reports/updates_YYYYMMDD.csv` has one row per change, carrying the exact
workbook cell:

| ticker | category | cell | old | new | reason_text | action |
|---|---|---|---|---|---|---|
| AAOI | Profitability | C4 | 8 | 7 | ROIC 3-yr average dropped from 14.2% to 12.8%, crossing the B/C threshold at 13.0% | APPLY |
| AAOI | Business Quality | — | 7 | 7 | ROIC persistence dropped from 70.0% to 55.0%, crossing the B/C threshold at 60.0% | NO EDIT - monitor |

### Watch items matter

Categories aggregate by **median**, so one sub-metric crossing a threshold usually
does *not* move the score — three others outvote it. That robustness is intentional,
but it means deterioration can build invisibly until a second metric tips the median
and the score drops two points at once.

So the diff reports sub-metric crossings inside unchanged categories as `WATCH` rows
with no cell edit. Those are your leading indicator.

---

## Tier 3: the narrow LLM slice

The model extracts exactly four things and never sees a threshold:

1. Recurring revenue %
2. RPO / backlog
3. Largest customer concentration
4. Moat evidence grade (A–F, from Item 1/1A language only)

Guardrails, because a hallucinated "85% recurring revenue" would move Income from 4 to 9:

- Every value must come with a **verbatim ≤25-word quote**, and the quote is checked
  against the source text. Not found → **value discarded**, not merely flagged.
- `confidence: low` → discarded and queued for your review.
- A percentage outside 0–1 is either rescaled (if 1–100) or discarded.
- Cross-checks: concentration above recurring revenue, RPO implying >20x revenue.
- A moat graded A/B whose quote can't be located is auto-downgraded to C.
- Results cache for ~400 days (`tier3_max_age_days`) — these facts change annually,
  so you pay for the call once per filing cycle.
- The prompt states that instructions inside filing text are to be ignored.

---

## Manual overrides always win

Your judgment on Business Quality, Income and Market Sentiment outranks the machine.
Put it in `universe.yaml`:

```yaml
overrides:
  AAOI:
    business_quality:
      score: 7
      note: "In-house MBE/MOCVD laser fab. Offset: Microsoft 28% of DC revenue."
      asof: "2026-01-15"
```

The writer **never** overwrites an overridden category, and the diff marks those rows
`REVIEW - manual override in place` rather than `APPLY`.

---

## Workbook repair

`--fix-workbook` corrects three defects found in the existing file:

1. **ABVX and AKAM hardcode base weights** in their total formula instead of
   `=SUM(K..)*10`, so their archetype weights are ignored. ABVX scores 55 where its
   Early Biotech weights give **63** — an 8-point error that also perturbs every
   biotech peer's z-score in the Model sheet.
2. **Column J weights are hand-typed** in all 90 blocks. Replaced with
   `INDEX/MATCH` against the archetype matrix so they can never drift.
3. **MBAI's archetype reads `E: Early Stage`**, which matches no matrix header.
   Left alone, the new `MATCH` would zero all its weights. Normalised to
   `E: Early Biotech`.

Verified: 3,798 formulas recalculate with **zero errors**, only ABVX (+8.00) and
AKAM (+1.75) change, and the Model sheet's price targets still compute.

---

## Limitations — read these

- **Guidance history is not free-sourceable.** The `guidance_net_raises_8q` sub-metric
  is permanently `data missing`, so Growth scores on three sub-metrics instead of four.
- **Only ~4 quarters of surprise history** come from yfinance, not 8. Beat-rate bands
  are applied to what exists and confidence is lowered accordingly.
- **Bank-specific fields** (CET1, NPLs, efficiency ratio) are not in free sources.
  Archetype F names will score Financials and Profitability on fewer sub-metrics —
  override manually.
- **`debt_due_24mo` uses the current portion of debt only**, which understates a true
  maturity wall. The maturity-wall red flag is therefore conservative.
- **The 5-yr median P/E is reconstructed** from fiscal year-end prices and annual EPS,
  not a daily series. Directionally right, not precise.
- **Institutional trend reads only the top holders** visible for free — directional
  evidence, not a full 13F aggregation.
- **Peer discovery leans on Yahoo's industry taxonomy**, which is coarser than a
  Capital IQ comp set built by hand. It will not know that two nominally "Semiconductor"
  companies serve completely different end markets. Review `--peers` output for your
  largest positions and freeze those sets manually.
- **Conglomerates and multi-segment issuers** get a single industry label, so their
  peer sets are the weakest. These are the clearest candidates for a manual list.
- **yfinance is unofficial.** It breaks. That is exactly why EDGAR is wired in as the
  fallback and why every accessor degrades instead of raising. If yfinance breaks
  badly, the run produces low-confidence scores with many `data missing` entries
  rather than wrong ones.

**Missing data is never estimated.** It is excluded from the median, lowers the
category's confidence, and appears in OPEN QUESTIONS. That is the single most
important behaviour in the system, and it is enforced by tests.

---

## Adjusting the rubric

Edit `config/rubric.yaml` — never the Python. To make Valuation stricter:

```yaml
fcf_yield:
  bands: [[0.07, A], [0.05, B], [0.03, C], [0.015, D]]   # was 0.06/0.04/0.025/0.01
```

Re-run `python tests/test_scoring.py` afterwards; the fixture tests will tell you
immediately if a boundary now behaves unexpectedly.
