# cn_option_vix

A CBOE-style, model-free 30-day implied-volatility index family for China's 12 listed financial options — 3 CFFEX stock-index options plus 9 SSE/SZSE ETF options — reconstructed daily and organized into 6 published, tradable-signal series.

## What it is

`cn_option_vix` rebuilds a "China VIX" family from the ground up using the CBOE model-free variance method (the same algorithm behind the S&P 500 VIX and the official 中国波指). For every instrument on every trading day it takes the near- and next-term option chains, computes a single-expiry model-free variance for each, and interpolates to a constant 30-day maturity. Individual instruments are then aggregated — in **variance space**, open-interest weighted — into economically meaningful groups and one overall index.

The output is a clean daily panel of volatility levels and cross-group spreads intended as an **input to trading signals**, not just a monitoring dashboard. The reconstruction is validated against the official 中国波指 iVIX (`000188.XSHG`) with 0.980 correlation over the 70-day window RiceQuant publishes.

Design and implementation notes:

- [`docs/plans/2026-07-09-cn-option-vix-design.md`](docs/plans/2026-07-09-cn-option-vix-design.md) — goals, locked decisions, grouping rationale, validation plan, risks.
- [`docs/plans/2026-07-09-cn-option-vix-implementation.md`](docs/plans/2026-07-09-cn-option-vix-implementation.md) — the TDD task-by-task build (Tasks 0–15).

## Published series

Six series are published each day: one **overall** index plus five groups. The five ETF groups were chosen by **measured volatility co-movement** — correlations of 21-day realized-vol *changes* over 2021–2026 — not by sector convention:

- 沪深300 ↔ 深证100 = 0.94
- 深证100 ↔ 创业板 = 0.94
- 上证50 ↔ 沪深300 = 0.91
- 科创50 is a standalone outlier (0.48–0.77 vs. everything), so it gets its own group.

| Series | 中文 | English | Members (roster symbols) |
|---|---|---|---|
| `overall` | 综合 | Overall | OI-weighted mean over **all 12** instruments |
| `index_vix` | 指数VIX | Index VIX | `IO` (沪深300), `HO` (上证50), `MO` (中证1000) — CFFEX index options |
| `blue_chip` | 大盘蓝筹 | Large-cap Blue-chip | `510050.XSHG`, `510300.XSHG`, `159919.XSHE` (上证50 + 沪深300) |
| `sz_growth` | 深市成长 | Shenzhen Growth | `159901.XSHE`, `159915.XSHE` (深证100 + 创业板) |
| `mid_small` | 中小盘 | Mid-Small Cap | `510500.XSHG`, `159922.XSHE` (中证500) |
| `hard_tech` | 硬科技 | Hard-tech / STAR | `588000.XSHG`, `588080.XSHG` (科创50) |

`overall` is a **flat OI-weighted mean across all 12 instruments**, not a mean-of-groups.

### Also emitted (per day)

- `iv_<symbol>` — the individual 30-day VIX for each instrument (e.g. `iv_IO`, `iv_510300.XSHG`). Column names embed the raw roster symbol including dots.
- `spread_index_bluechip` = `index_vix − blue_chip`
- `spread_bluechip_szgrowth` = `blue_chip − sz_growth`
- `n_instruments` — count of instruments that computed a valid VIX that day
- `dq_flags` — count of instruments that computed but failed the validity check

Only these two spreads exist; there is no spread series for `mid_small` or `hard_tech`.

## Method

The reconstruction follows the CBOE model-free VIX recipe per instrument, then aggregates.

**1. Forward and K0 (`core/forward.py`).** For each expiry, the forward index level is implied from put-call parity at the strike with the smallest `|C − P|`:

```
F  = kstar + exp(r·T)·(C[kstar] − P[kstar])
K0 = max(strike ≤ F)
```

Only strikes present in **both** the call and put chains are used. The carry factor is `exp(r·T)` (compounding upward), matching CBOE's `e^{rT}` convention.

**2. OTM series + tail trim (`core/variance.py`).** An out-of-the-money price series is built (puts below `K0`, calls above, the average of the two at `K0`). The CBOE two-consecutive-zero rule trims each tail: walking outward from `K0`, a tail stops after two consecutive non-positive-price strikes. `K0` itself is always retained.

**3. Single-expiry variance (`core/variance.py`).** The model-free variance rate for one expiry is

```
σ² = (2/T)·Σ (ΔK / K²)·exp(r·T)·Q(K)  −  (1/T)·(F/K0 − 1)²
```

with central-difference `ΔK` (one-sided at the ends). A thin or broken chain can yield a negative σ²; this is not clamped here — it is handled downstream.

**4. Constant-30-day interpolation (`core/vix_chain.py`).** The near- and next-term variance *rates* are combined into a constant 30-day maturity via CBOE's linear interpolation of total variance, reannualized to 30 days (actual/365). If 30 days is not bracketed by the two terms, the nearer/farther term's annualized vol is held flat (with a `UserWarning`). Negative interpolated variance returns `nan` (also warned). The result is a VIX in vol points (`100·√·`).

**5. Per-instrument driver (`core/instrument_vix.py`).** `instrument_vix(symbol, date)` wires chains → forward → variance → interpolation for one instrument on one date, requiring ≥2 expiries and ≥3 common call/put strikes per expiry. Its `oi` field is the **summed open interest across both** the near and next expiries — this is the aggregation weight.

**6. OI-weighted variance-space aggregation (`aggregate/composite.py`).** Group and overall indices are **open-interest-weighted means of the 30-day variance rates** (`var30`), converted to vol points only at the end (`vix = 100·√var`). Aggregating in variance space — not by averaging VIX levels — is the statistically correct way to pool model-free variances. Instruments are usable only if they passed the validity check, carry positive OI, and have a non-NaN variance; groups whose weighted variance is negative are dropped rather than clamped.

**European exercise.** All 12 instruments are European-style options (CFFEX index options and SSE/SZSE ETF options), so the CBOE model-free formula applies directly with no early-exercise adjustment.

**Dynamic membership.** The roster has staggered inception dates (50ETF options from 2015, the 300-family from 2019, the rest 2022–2023). The pipeline is point-in-time correct: on any given day it uses only contracts that were actually listed and not yet delisted, and an instrument with no valid chain simply produces no `iv_` column for that day. The set of `iv_*` columns therefore varies across the history, which is expected.

## Repo layout

```
cn_option_vix/
├── config.py                 # single source of truth: RQDATAC_URI, ROSTER (12), GROUPS (5), VIX_PARAMS, iVIX constants
├── core/
│   ├── forward.py            # compute_forward -> (F, K0, kstar)   (CBOE step 1)
│   ├── variance.py           # build_otm_series, single_expiry_variance   (steps 2-3)
│   ├── vix_chain.py          # select_near_next, interpolate_to_target   (constant-30d step)
│   └── instrument_vix.py     # instrument_vix(symbol, date) -> dict|None  (atomic per-instrument driver)
├── aggregate/
│   └── composite.py          # aggregate_variances(per_inst) -> groups + overall (OI-weighted, variance space)
├── data/
│   ├── chains.py             # get_chain_snapshot: near+next chains, settlement/close/OI, disk cache
│   ├── rates.py              # risk_free_rate: term-matched, connection-free (0.02 fallback)
│   └── cache/                # read-first parquet cache: per-date chains + _universe_options.parquet
├── pipeline/
│   ├── one_day.py            # compute_day(date) -> flat dict row (6 series + diagnostics)
│   ├── build_history.py      # build_history(start, end) -> full panel; writes parquet/csv/json
│   ├── update_daily.py       # update_daily(asof=None) -> idempotent one-day append
│   └── quality.py            # summarize_quality(df) -> data-quality summary
├── validate/
│   └── ivix_compare.py       # compare_to_ivix() -> corr/rmse/bias vs official 000188.XSHG
├── notebooks/
│   └── vix_dashboard.ipynb   # dashboard / exploration notebook
├── tests/                    # 14 test_*.py files, 24 tests; conftest.py skips live-RQ tests gracefully
├── outputs/                  # vix_series.parquet, vix_series.csv, quality_report.json, plots/
├── docs/plans/               # design + implementation plans
├── requirements.txt
└── pytest.ini
```

Note: the design doc mentions `data/prices.py` and `aggregate/groups.py`; those were never separate modules — price/OI handling lives in `data/chains.py` and group membership lives in `config.py`. An ATM-IV cross-check sketched in the plan (`atm_flag_threshold`) was intentionally left unimplemented because the available IV feed is unreliable.

## Requirements / Install

Python 3, plus (`requirements.txt`, unpinned):

```
rqdatac
pandas
numpy
pyarrow
pytest
matplotlib
fastapi
uvicorn
httpx2
```

```bash
cd /Users/qichengfu/Desktop/YSJ
python3 -m venv cn_option_vix_runtime/.venv
source cn_option_vix_runtime/.venv/bin/activate
python -m pip install -r cn_option_vix/requirements.txt
```

Live RiceQuant (`rqdatac`) access is needed only for pulling new option chains / building fresh history. Any computation that runs entirely off the on-disk cache needs no RQ login (see [Data source & caching](#data-source--caching)).

## Usage

Run everything from the **workspace root** (the parent directory of `cn_option_vix/`). The `python -m` form is load-bearing — it puts the workspace root on `sys.path` so `import cn_option_vix` (and `import container`) resolve.

Set the RiceQuant credential only in your shell, not in source code:

```bash
export RQDATA_URI='tcp://...'
```

**Run the tests** (24 pass offline; 3 live-RQ tests skip gracefully when RQ is unavailable):

```bash
python -m pytest cn_option_vix/tests -v
```

**Build the full history** (needs live RQ; writes parquet + csv + quality JSON):

```bash
python -c "from cn_option_vix.pipeline.build_history import build_history; build_history('2015-02-09', '2026-07-13')"
```

**Idempotent daily update** (appends/overwrites one day; with an explicit `asof` and cached chains it runs fully offline):

```bash
python -c "from cn_option_vix.pipeline.update_daily import update_daily; update_daily()"
python -c "from cn_option_vix.pipeline.update_daily import update_daily; update_daily(asof='2024-06-04')"
```

**Re-validate against official iVIX** (needs live RQ for the iVIX pull; prints corr/rmse/bias and writes an overlay plot):

```bash
python -c "from cn_option_vix.validate.ivix_compare import compare_to_ivix; print(compare_to_ivix())"
```

**Open the dashboard notebook:**

```bash
jupyter lab cn_option_vix/notebooks/vix_dashboard.ipynb
```

## Outputs

Written under `cn_option_vix/outputs/`:

| File | Written by | Contents |
|---|---|---|
| `vix_series.parquet` | `build_history`, `update_daily` | Full panel: `date` index + 6 published series + all `iv_<symbol>` + both spreads + `n_instruments` + `dq_flags` |
| `vix_series.csv` | `build_history`, `update_daily` | The 6 published series only (`overall`, `index_vix`, `blue_chip`, `sz_growth`, `mid_small`, `hard_tech`) + `date` index |
| `quality_report.json` | `build_history` only | `n_days`, `days_with_flags`, `mean_instruments`, `min_instruments` |
| `plots/ivix_validation.png` | `compare_to_ivix` | Overlay of reconstructed 50ETF VIX vs. official iVIX |

`update_daily` does **not** rewrite `quality_report.json` (only `build_history` does). The CSV always lands in `outputs/` even if the parquet path is redirected via `out_path`. A 5-day offline **sample** `vix_series.parquet` (built from cached days) currently ships in the repo; the full multi-year backfill is the remaining step (see below).

## Data source & caching

Data comes from **RiceQuant `rqdatac`**. The connection URI is read from `RQDATA_URI` or `RQDATAC_URI` in the shell environment; credentials must not be stored in source code.

The pipeline is built to be **read-first and connection-free wherever possible**:

- The full option universe (`rq.all_instruments(type="Option")`, ~220k rows) is cached once to `data/cache/_universe_options.parquet`. Delete that file to force a refresh.
- Per-date chains are cached to `data/cache/<symbol-with-dots→underscores>_<YYYY-MM-DD>.parquet`. These are treated as **immutable** (settlement is final once the day closes) and are read before any network call.
- **A fully-cached run performs zero RQ logins.** `data/rates.py` never calls `rq.init` (it returns a constant rate), and the cached chain path in `data/chains.py` also never inits RQ. `rq.init` fires lazily *only* on a cache/universe miss, or when resolving the trading calendar / latest trading date in `build_history` / `update_daily(asof=None)`.

This is why the cached-data tests (`chains`, `instrument_vix`, `one_day`, quality spreads) and an explicit-`asof` daily update run offline, while backfill and re-validation need a live license.

## Validation

The reconstructed **50ETF (510050) VIX** was compared to the official 中国波指 **iVIX (`000188.XSHG`)** over RiceQuant's published window **2017-09-12 → 2017-12-25** (70 trading days, `n = 70`):

| Metric | Result | Acceptance gate |
|---|---|---|
| Pearson correlation | **0.980** | ≥ 0.90 |
| RMSE | **0.80 vol points** | < 3.0 |
| Bias (ours − iVIX) | **+0.40 vol points** | (not gated) |
| Overlap days | **70** | ≥ 50 |

The acceptance gate **passed**. Reproduce with `compare_to_ivix()` (writes `outputs/plots/ivix_validation.png`).

## Current status & remaining work

**Status (2026-07-13):** all 16 implementation tasks are committed to the project's isolated git repo (18 commits on `master`). Of the 27 total tests, **24 pass offline** and **3 network-dependent tests skip gracefully** under the login/traffic cap. Validation passed at corr 0.980. A 5-day offline sample panel exists at `outputs/vix_series.parquet`.

**The one remaining step is the full multi-year history backfill.** It is blocked purely on live RiceQuant access — the primary license is traffic-quota-exhausted and the trial license is limited by its login-machine cap (and expires ~2026-07-25).

**To unblock and finish:**

1. Restore live RQ access by either (a) freeing a trial-license machine slot or renewing the trial before ~2026-07-25, or (b) resetting/renewing the primary license's traffic quota and swapping `RQDATAC_URI` in `config.py` back to it.
2. Then run the full backfill:
   ```bash
   python -c "from cn_option_vix.pipeline.build_history import build_history; build_history('2015-02-09', '2026-07-13')"
   ```
3. Thereafter keep it current with `update_daily()` (or a scheduled daily job); with warm chain caches this stays largely offline.

## Caveats

- **Risk-free rate is a flat 0.02.** `data/rates.py` is deliberately connection-free; the current `rqdatac` build exposes no `get_shibor` accessor, so the term-matched SHIBOR path is dormant and the constant fallback (2%) is used in practice. Model-free VIX is only weakly rate-sensitive, so this is an acceptable approximation. `get_interbank_offered_rate` is a possible future refinement.
- **Network tests skip, they don't fail.** The `rq_online` fixture (`tests/conftest.py`) checks the RQ connection once per session and skips the 3 live-RQ tests when login/traffic is unavailable, so the suite stays green offline.
- **`test_update_daily` has no skip guard** — it relies on the pre-populated chain cache for 2024-06-03/04. If that cache is deleted, the test needs live RQ.
- **Single-expiry variance is not clamped;** negative values can occur on thin chains and are handled (NaN with a warning) only at the interpolation stage.
- **Cache filenames do not encode `min_near_days`.** Calling `get_chain_snapshot` with a non-default `min_near_days` can overwrite the default cache file for that symbol/date; stick to the default (7) unless you clear the cache.
- **`config.py` contains a live trial RQ credential** with a ~2026-07-25 expiry. Treat it as temporary and do not leak it further.
