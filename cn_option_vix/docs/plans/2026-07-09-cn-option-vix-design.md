# CN Option VIX — Design

**Date:** 2026-07-09
**Owner:** JM
**Status:** Design approved, pending implementation plan

## 1. Goal

Build a VIX-style, model-free 30-day implied-volatility index family for China's
**financial** options (12 currently-listed underlyings: 3 CFFEX stock-index options
+ 9 exchange ETF options). Deliver one overall VIX plus a small set of sub-VIXs so
the series can be used as a **tradable signal** (vol timing, dispersion, hedging),
backtested on a clean point-in-time daily history.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Primary use | **Tradable signal** (needs point-in-time correctness; backtest on daily history first) |
| Methodology | **Full CBOE model-free VIX** (all OTM strikes, forward via put-call parity, 30d interpolation) |
| Overall weighting | **Open-interest (OI) weighted**, aggregated in variance space |
| Sub-VIX division | **Index VIX** (IO/HO/MO) as one group + **4 ETF similarity groups** (see §3) |
| Cadence | **Daily EOD first**; intraday 1-min is a phase-2 hook |
| Price input | **Settlement price** per strike (close as fallback on zero-volume strikes) |
| History roster | **Dynamic membership** — each series starts at its own option inception; composites renormalize weights |

Aggregation approach: **hierarchical variance aggregation** (per-instrument 30d
variance is the atomic unit; OI-weight-average variances up each level). Rejected
alternatives: pooled synthetic chain (rescaling index vs ETF strikes contaminates
the tail integral) and vol-space blending (averaging vols is biased low vs the true
variance aggregate).

## 3. Grouping / hierarchy (final)

Sub-VIX groups were chosen by **measured similarity** — correlation of 21-day
realized-vol *changes* across the 7 benchmark indices, 2021-01 to 2026-07
(n=1334). Key evidence: 沪深300↔深证100 = 0.94, 深证100↔创业板 = 0.94,
上证50↔沪深300 = 0.91, 中证500↔broad ≈ 0.82-0.84, 科创50↔all = 0.48-0.77
(a genuine standalone vol regime).

```
总体 Overall VIX                      OI-weighted across all 12 instruments
│
├── 指数VIX Index VIX                 IO 沪深300 · HO 上证50 · MO 中证1000   (CFFEX index options)
│
└── ETF 相似性分组 (4 groups)
    ├── ① 大盘蓝筹 Large-cap Blue-chip   上证50 · 沪深300
    │        510050 华夏上证50ETF · 510300 华泰柏瑞沪深300ETF · 159919 嘉实沪深300ETF
    ├── ② 深市成长 Shenzhen Growth      深证100 · 创业板
    │        159901 易方达深证100ETF · 159915 易方达创业板ETF
    ├── ③ 中小盘 Mid-Small Cap          中证500
    │        510500 南方中证500ETF · 159922 嘉实中证500ETF
    └── ④ 硬科技 Hard-tech / STAR        科创50
             588000 华夏科创50ETF · 588080 易方达科创50ETF
```

Atomic layer: a per-instrument 30-day variance for each of the 12 instruments, also
exposed individually for diagnostics.

**Published series (6):** Overall, Index VIX, 大盘蓝筹, 深市成长, 中小盘, 硬科技.

**Note (composite semantics):** each group VIX is an OI-weighted *composite* vol
across its member underlyings — not a single index's vol. Group weights follow where
OI concentrates (e.g. Index VIX is OI-dominated by IO 沪深300). This is intended
behavior for a tradable group signal.

**Later refinement (phase 2):** re-validate these hand+data-assigned buckets by
re-clustering on the *realized VIX* series once built (rather than on underlying
realized vol), and confirm/revise membership.

## 4. Core algorithm (per option chain, per expiry T)

Standard CBOE model-free variance:

1. Forward: `F = K* + e^{rT}·(C(K*) − P(K*))`, where `K*` = strike with smallest |C−P|.
2. `K₀` = first strike below F. Use OTM options: puts for K < K₀, calls for K > K₀,
   average of call & put at K₀.
3. Variance:
   `σ² = (2·e^{rT}/T)·Σᵢ (ΔKᵢ / Kᵢ²)·Q(Kᵢ)  −  (1/T)·(F/K₀ − 1)²`
   with `ΔKᵢ = (K_{i+1} − K_{i-1})/2` (one-sided at the ends), `Q(K)` = settlement
   price (close fallback).
4. **30-day interpolation** between the **near** term (T₁ = first expiry ≥ 7 calendar
   days; roll when < 7 days) and **next** term (T₂). VIX = `100·√(interp σ² to 30d)`.

Inputs: `r` = term-matched SHIBOR; `T` = fraction to 15:00 on maturity_date,
actual/365. All CN stock/ETF/index options are **European exercise** → no
early-exercise adjustment needed.

**Data-quality gate:** compute ATM implied vol from `rq.options.get_greeks` and flag
any chain where model-free VIX and ATM-IV diverge beyond a threshold (stale/bad chain).

## 5. Aggregation

- Per-instrument 30d variance `σ²ᵢ` (i = 1..12).
- Group variance = OI-weighted average of member `σ²ᵢ` (singleton members pass
  through). Weight = instrument total OI (evaluate $-OI as an option).
- Index VIX variance = OI-weighted average of {IO, HO, MO}.
- Overall variance = OI-weighted average across all 12.
- `VIX = 100·√σ²` at every node.
- **Dynamic membership:** on each date, include only instruments listed & trading
  that day; renormalize weights. Membership start dates documented (§7).

## 6. Point-in-time correctness

`VIX_t` is computed from day-t **settlement** (published after close). It is known at
EOD t and actionable at t+1 (or same-day close in the intraday phase). Only
instruments actually listed on t enter the composite. No look-ahead.

## 7. History / roster (staggered inceptions)

| Underlying | First option | Instruments |
|---|---|---|
| 上证50 | 2015-02 (510050) / 2022-12 (HO) | 510050, HO |
| 沪深300 | 2019-12 | IO, 510300, 159919 |
| 中证1000 | 2022-07 | MO |
| 中证500 | 2022-09 | 510500, 159922 |
| 创业板 | 2022-09 | 159915 |
| 深证100 | 2022-12 | 159901 |
| 科创50 | 2023-06 | 588000, 588080 |

So 大盘蓝筹 has usable history from 2015 (via 510050) / 2019 (300); 深市成长 from
2022-09; 中小盘 from 2022-09; 硬科技 from 2023-06. Overall composite membership
grows over time.

## 8. Repo layout

```
cn_option_vix/
  config.py         # ROSTER: 12 instruments → {group, underlying}; VIX params (N=30, min=7); weight=OI
  data/
    chains.py       # live chain (all strikes, 2 expiries bracketing 30d) for an underlying on a date
    prices.py       # settlement per strike (close fallback), instrument OI
    rates.py        # term-matched SHIBOR
    cache/          # parquet cache of daily chains & settlements
  core/
    forward.py      # F, K₀ via put-call parity
    variance.py     # single-expiry σ² integral (strike selection, OTM, ΔK/K²)
    vix_chain.py    # per-instrument 30d VIX: near/next select + interpolate
  aggregate/
    groups.py       # group membership map (Index + 4 ETF groups)
    composite.py    # OI-weighted variance aggregation → group & overall VIX
  pipeline/
    build_history.py  # backfill loop over trading calendar
    update_daily.py    # cron append latest day
  validate/
    ivix_compare.py    # 510050-VIX vs official 中国波指 iVIX 2015-2018
  outputs/          # parquet series + CSV export + plots
    vix_series.parquet   # tidy: date × {overall, index_vix, blue_chip, sz_growth, mid_small, hard_tech} + 12 per-instrument + membership flags + ATM-diagnostic
    vix_series.csv       # human-readable mirror of the published 6 series
    plots/               # PNG snapshots for reports
  notebooks/
    vix_dashboard.ipynb  # plotting notebook: 6 series overlay, term structure, group spreads, event annotations
  tests/
  docs/plans/
```

Reuses `container/config.py::RQDATAC_URI` for the RiceQuant connection.

### Outputs (per §2 = parquet + notebook + extras)

- **`vix_series.parquet`** — the canonical store; one row per trading date, columns:
  the 6 published series, the 12 per-instrument diagnostics, per-instrument OI weights,
  membership flags, and the ATM-IV cross-check.
- **`vix_series.csv`** — the 6 published series only, for quick reading / Excel.
- **`vix_dashboard.ipynb`** — matplotlib notebook: overlay of the 6 series, per-group
  term structure (near/next/30d), the cross-venue / cross-group spreads, and event
  annotations (2015/2016/2018/2020…).
- **Extras I recommend:** a **data-quality report** (chains dropped, strikes with
  close-fallback, ATM-vs-model-free divergence flags per day) written alongside the
  parquet; and the **cross-venue spread series** (Index−大盘蓝筹 on the 300 component,
  大盘蓝筹−深市成长) as first-class columns since they're the most actionable signal.

## 9. Validation (acceptance test)

**iVIX availability in RiceQuant (checked 2026-07-09):** RQ carries the official
**中国波指 iVIX** as `000188.XSHG` (type INDX, genuine VIX-% units) but stored only a
**70-trading-day window, 2017-09-12 → 2017-12-25**. The `000803` "300波动" / `000804`
"500波动" indices are *low-volatility strategy* indices (price-level in the thousands),
**not** implied-vol — do not use. RQ provides **no ready-made option-VIX**; we build
our own. Ground-truth validation therefore leans on the 70-day iVIX overlap plus
methodology tests.

1. **iVIX anchor:** compute the 510050 (50ETF) VIX over 2017-09-12 → 2017-12-25 and
   compare against `000188.XSHG`. Target correlation ≥ 0.95 and small level RMSE on
   the overlap → proves the CBOE implementation matches the SSE-published method.
2. **Methodology unit tests:** synthetic chains with closed-form answers (flat-vol
   chain → known σ²), since the iVIX overlap is short.
3. **Model-free vs ATM-IV** agreement per instrument (data-quality).
4. **Event alignment:** VIX spikes match known stress (2015 股灾, 2016 熔断, 2018
   selloff, 2020 COVID, subsequent events).
5. **Optional:** source a longer archived iVIX / third-party 50ETF-vol series to
   extend the anchor beyond 70 days (nice-to-have, not blocking).

## 10. Testing

- Unit: forward/K₀ on a synthetic chain with a known answer; σ² integral vs an
  analytic flat-vol chain; 30d interpolation.
- Golden: one real date fully hand-checked end-to-end.
- Integration: the iVIX-correlation gate (≥ 0.95).

## 11. Phase 2 (later)

- **Intraday:** swap EOD-settlement feed for 1-minute-close feed; core is
  driver-agnostic. Heavier (all strikes × minutes).
- **Tick mid-quote:** replace settlement with bid/ask mid (tick data only) for higher
  accuracy on illiquid deep-OTM strikes.
- **Cross-venue spread signals:** since 沪深300 vol is measured in Index VIX (IO),
  大盘蓝筹 (510300/159919), the spreads (Index−ETF, SSE−SZSE) are tradeable vol-basis
  signals — candidate first-class outputs.
- **Re-cluster** groups on realized VIX series (§3 note).

## 12. Open items / risks

- Risk-free source: confirm RQ SHIBOR term structure availability; sensitivity is small.
- Deep-OTM stale strikes on illiquid ETF chains → mitigated by close-fallback + ATM
  gate; monitor.
- Repo is **not** git-initialized — commit of this doc deferred (offer `git init`).
- iVIX ground truth: RQ has `000188.XSHG` but only 70 days (2017-09-12 → 2017-12-25);
  validation anchors on that window + unit tests. Longer archived series = optional.
```
