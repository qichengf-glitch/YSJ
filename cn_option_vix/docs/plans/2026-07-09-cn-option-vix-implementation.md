# CN Option VIX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a model-free (CBOE-method) 30-day implied-volatility index family for China's 12 listed financial options — one Overall VIX, an Index VIX (IO/HO/MO), and 4 data-driven ETF group VIXs (大盘蓝筹 / 深市成长 / 中小盘 / 硬科技) — as a point-in-time daily series usable as a tradable signal.

**Architecture:** Hierarchical variance aggregation. The atomic unit is a per-instrument 30-day model-free variance computed from its option chain (forward via put-call parity → OTM strike integral → near/next-term interpolation to 30 days). Variances are OI-weighted up three levels (instrument → group → overall) and only the square-root is taken at each published node. EOD settlement-priced, dynamic membership, validated against RiceQuant's official 中国波指 iVIX (`000188.XSHG`).

**Tech Stack:** Python 3.13, `rqdatac` (RiceQuant, via `container/config.py::RQDATAC_URI`), `pandas`, `numpy`, `pyarrow` (parquet), `pytest`, `matplotlib` (notebook). Design doc: `cn_option_vix/docs/plans/2026-07-09-cn-option-vix-design.md`.

**Conventions:** all code under `cn_option_vix/`; tests mirror under `cn_option_vix/tests/`. Run tests from repo root `c:\Users\jimde\Desktop\strat research`. Chinese comments are fine. Never hard-code the RQ URI — import it.

---

## Task 0: Repo & package scaffolding

**Files:**
- Create: `cn_option_vix/__init__.py`, `cn_option_vix/core/__init__.py`, `cn_option_vix/data/__init__.py`, `cn_option_vix/aggregate/__init__.py`, `cn_option_vix/pipeline/__init__.py`, `cn_option_vix/validate/__init__.py`, `cn_option_vix/tests/__init__.py`
- Create: `cn_option_vix/requirements.txt`, `cn_option_vix/.gitignore`, `cn_option_vix/pytest.ini`

**Step 1: Init git (repo is not yet a git repository)**

Run from repo root:
```bash
git init
git add cn_option_vix/docs/plans/
git commit -m "docs: CN option VIX design + implementation plan"
```
Expected: repo initialized, design + plan committed.

**Step 2: Create the package tree**

Each `__init__.py` is empty. `requirements.txt`:
```
rqdatac
pandas
numpy
pyarrow
pytest
matplotlib
```

`.gitignore`:
```
__pycache__/
*.pyc
cn_option_vix/data/cache/
cn_option_vix/outputs/
.ipynb_checkpoints/
```

`pytest.ini`:
```ini
[pytest]
testpaths = cn_option_vix/tests
python_files = test_*.py
addopts = -q
```

**Step 3: Smoke-test the RQ connection**

Create `cn_option_vix/tests/test_rq_connection.py`:
```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from container.config import RQDATAC_URI
import rqdatac as rq

def test_rq_connects_and_lists_options():
    rq.init(uri=RQDATAC_URI)
    df = rq.all_instruments(type="Option")
    assert len(df) > 100000  # RQ carries ~220k option instruments all-time
```

Run: `pytest cn_option_vix/tests/test_rq_connection.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add cn_option_vix/
git commit -m "chore: scaffold cn_option_vix package + RQ smoke test"
```

---

## Task 1: Roster & config

The single source of truth for which 12 instruments exist, their underlying, and their group.

**Files:**
- Create: `cn_option_vix/config.py`
- Test: `cn_option_vix/tests/test_config.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.config import ROSTER, GROUPS, VIX_PARAMS

def test_roster_has_12_instruments():
    assert len(ROSTER) == 12

def test_group_membership_counts():
    # published groups and their underlyings
    assert GROUPS["index_vix"]["underlyings"] == ["HS300", "SH50", "ZZ1000"]
    assert set(GROUPS["blue_chip"]["underlyings"]) == {"SH50", "HS300"}
    assert set(GROUPS["sz_growth"]["underlyings"]) == {"SZ100", "CYB"}
    assert GROUPS["mid_small"]["underlyings"] == ["ZZ500"]
    assert GROUPS["hard_tech"]["underlyings"] == ["KC50"]

def test_every_instrument_maps_to_a_group():
    for r in ROSTER:
        assert r["group"] in GROUPS

def test_vix_params_defaults():
    assert VIX_PARAMS["target_days"] == 30
    assert VIX_PARAMS["min_near_days"] == 7
    assert VIX_PARAMS["weight_mode"] == "oi"
```

**Step 2: Run to verify it fails** — `pytest cn_option_vix/tests/test_config.py -v` → FAIL (no module).

**Step 3: Implement `cn_option_vix/config.py`**
```python
"""Single source of truth for the CN option VIX roster & groups."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from container.config import RQDATAC_URI  # noqa: re-export the RQ connection

# --- The 12 financial-option instruments (option product code, exchange, underlying, group) ---
# underlying keys: SH50 上证50, HS300 沪深300, ZZ500 中证500, ZZ1000 中证1000,
#                  KC50 科创50, CYB 创业板, SZ100 深证100
ROSTER = [
    # CFFEX stock-index options -> Index VIX
    {"symbol": "IO", "kind": "index", "exchange": "CFFEX", "underlying": "HS300",  "group": "index_vix"},
    {"symbol": "HO", "kind": "index", "exchange": "CFFEX", "underlying": "SH50",   "group": "index_vix"},
    {"symbol": "MO", "kind": "index", "exchange": "CFFEX", "underlying": "ZZ1000", "group": "index_vix"},
    # SSE / SZSE ETF options -> the 4 similarity groups
    {"symbol": "510050.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "SH50",  "group": "blue_chip"},
    {"symbol": "510300.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "HS300", "group": "blue_chip"},
    {"symbol": "159919.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "HS300", "group": "blue_chip"},
    {"symbol": "159901.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "SZ100", "group": "sz_growth"},
    {"symbol": "159915.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "CYB",   "group": "sz_growth"},
    {"symbol": "510500.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "ZZ500", "group": "mid_small"},
    {"symbol": "159922.XSHE", "kind": "etf", "exchange": "XSHE", "underlying": "ZZ500", "group": "mid_small"},
    {"symbol": "588000.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "KC50",  "group": "hard_tech"},
    {"symbol": "588080.XSHG", "kind": "etf", "exchange": "XSHG", "underlying": "KC50",  "group": "hard_tech"},
]

GROUPS = {
    "index_vix": {"name_cn": "指数VIX",   "name_en": "Index VIX",            "underlyings": ["HS300", "SH50", "ZZ1000"]},
    "blue_chip": {"name_cn": "大盘蓝筹",   "name_en": "Large-cap Blue-chip",  "underlyings": ["SH50", "HS300"]},
    "sz_growth": {"name_cn": "深市成长",   "name_en": "Shenzhen Growth",      "underlyings": ["SZ100", "CYB"]},
    "mid_small": {"name_cn": "中小盘",     "name_en": "Mid-Small Cap",        "underlyings": ["ZZ500"]},
    "hard_tech": {"name_cn": "硬科技",     "name_en": "Hard-tech / STAR",     "underlyings": ["KC50"]},
}

VIX_PARAMS = {
    "target_days": 30,       # constant-maturity target
    "min_near_days": 7,      # roll the near term when < this many calendar days to expiry
    "annual_days": 365,      # actual/365 convention
    "weight_mode": "oi",     # composite weighting: open interest
    "atm_flag_threshold": 0.05,  # |model-free VIX - ATM IV| above this -> data-quality flag
}

# Official iVIX ground truth in RQ (see design §9): 70 trading days only.
IVIX_CODE = "000188.XSHG"
IVIX_WINDOW = ("2017-09-12", "2017-12-25")
```

**Step 4: Run** — `pytest cn_option_vix/tests/test_config.py -v` → PASS.

**Step 5: Commit** — `git add cn_option_vix/config.py cn_option_vix/tests/test_config.py && git commit -m "feat: roster + group config for CN option VIX"`

---

## Task 2: Forward & K₀ (put-call parity)  ← pure math, TDD first

**Files:**
- Create: `cn_option_vix/core/forward.py`
- Test: `cn_option_vix/tests/test_forward.py`

**Step 1: Write the failing test** (synthetic chain with a known answer)
```python
import math
from cn_option_vix.core.forward import compute_forward

def test_forward_and_k0_basic():
    # Symmetric chain: C==P at K=100 => forward ~ 100
    strikes = [90, 95, 100, 105, 110]
    calls = {90: 11.0, 95: 6.5, 100: 3.0, 105: 1.2, 110: 0.4}
    puts  = {90: 0.4, 95: 1.1, 100: 3.0, 105: 6.3, 110: 10.5}
    r, T = 0.02, 30/365
    F, K0, kstar = compute_forward(calls, puts, r, T)
    assert kstar == 100                 # smallest |C-P|
    assert abs(F - 100.0) < 0.5         # C-P==0 at 100 => F≈K*
    assert K0 == 100                    # first strike <= F

def test_k0_is_strike_below_forward():
    strikes = [90, 95, 100, 105, 110]
    calls = {90: 12.5, 95: 8.2, 100: 4.6, 105: 2.1, 110: 0.8}
    puts  = {90: 0.3, 95: 1.0, 100: 2.3, 105: 4.7, 110: 8.3}
    F, K0, kstar = compute_forward(calls, puts, 0.02, 30/365)
    assert K0 <= F and all((k > F) or (k <= K0) for k in strikes)
```

**Step 2: Run to verify fail** — `pytest cn_option_vix/tests/test_forward.py -v` → FAIL.

**Step 3: Implement `cn_option_vix/core/forward.py`**
```python
"""Forward level and K0 from put-call parity (CBOE VIX step 1)."""
import math

def compute_forward(calls: dict, puts: dict, r: float, T: float):
    """calls/puts: {strike: price}. Returns (F, K0, kstar).

    F   = forward index level implied by put-call parity at the strike with
          the smallest |C-P|.
    K0  = first strike at or below F.
    """
    strikes = sorted(set(calls) & set(puts))
    if not strikes:
        raise ValueError("no common call/put strikes")
    kstar = min(strikes, key=lambda k: abs(calls[k] - puts[k]))
    F = kstar + math.exp(r * T) * (calls[kstar] - puts[kstar])
    below = [k for k in strikes if k <= F]
    K0 = max(below) if below else min(strikes)
    return F, K0, kstar
```

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: forward + K0 via put-call parity"`

---

## Task 3: Single-expiry variance (the σ² integral)  ← the heart of the method

**Files:**
- Create: `cn_option_vix/core/variance.py`
- Test: `cn_option_vix/tests/test_variance.py`

**Step 1: Write the failing test.** Use a flat-vol Black-76 chain: generate option prices at a known σ, run the estimator, expect σ² back within tolerance.
```python
import math
from cn_option_vix.core.variance import build_otm_series, single_expiry_variance

def _black76(F, K, r, T, sigma, cp):
    from math import log, sqrt, exp
    from statistics import NormalDist
    N = NormalDist().cdf
    d1 = (log(F/K) + 0.5*sigma*sigma*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    if cp == "c":
        return exp(-r*T) * (F*N(d1) - K*N(d2))
    return exp(-r*T) * (K*N(-d2) - F*N(-d1))

def test_recovers_flat_vol_variance():
    F, r, T, sigma = 100.0, 0.02, 30/365, 0.25
    strikes = [F*(1+0.01*i) for i in range(-40, 41)]  # dense +/-40% grid, 1% steps
    calls = {round(K,4): _black76(F, K, r, T, sigma, "c") for K in strikes}
    puts  = {round(K,4): _black76(F, K, r, T, sigma, "p") for K in strikes}
    K0 = max(k for k in calls if k <= F)
    otm = build_otm_series(calls, puts, K0)
    var = single_expiry_variance(otm, F, K0, r, T)
    assert abs(math.sqrt(var) - sigma) < 0.01   # recover 25% within 1 vol pt
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/core/variance.py`**
```python
"""Single-expiry model-free variance (CBOE VIX steps 2-3)."""
import math

def build_otm_series(calls: dict, puts: dict, K0: float):
    """Return sorted [(K, Q)] using OTM options: puts below K0, calls above,
    and the average of call & put at K0. Drops non-positive prices, and trims
    each tail after two consecutive dropped strikes (CBOE tail rule)."""
    strikes = sorted(set(calls) & set(puts))
    out = {}
    for K in strikes:
        if K < K0:
            q = puts[K]
        elif K > K0:
            q = calls[K]
        else:
            q = 0.5 * (calls[K] + puts[K])
        out[K] = q

    def trim(seq):
        kept, zeros = [], 0
        for K in seq:
            if out[K] <= 0:
                zeros += 1
                if zeros >= 2:
                    break
                continue
            zeros = 0
            kept.append(K)
        return kept

    below = trim([k for k in strikes if k < K0][::-1])   # walk down from K0
    above = trim([k for k in strikes if k > K0])          # walk up from K0
    kept = sorted(set(below) | set(above) | {K0})
    return [(K, out[K]) for K in kept]

def single_expiry_variance(otm, F: float, K0: float, r: float, T: float) -> float:
    """otm: sorted [(K, Q)]. Returns σ² for this expiry."""
    ks = [K for K, _ in otm]
    q  = {K: Q for K, Q in otm}
    n = len(ks)
    total = 0.0
    for i, K in enumerate(ks):
        if i == 0:
            dK = ks[1] - ks[0]
        elif i == n - 1:
            dK = ks[-1] - ks[-2]
        else:
            dK = (ks[i+1] - ks[i-1]) / 2.0
        total += (dK / (K * K)) * math.exp(r * T) * q[K]
    return (2.0 / T) * total - (1.0 / T) * (F / K0 - 1.0) ** 2
```

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: single-expiry model-free variance + OTM series"`

---

## Task 4: 30-day interpolation & per-chain VIX

**Files:**
- Create: `cn_option_vix/core/vix_chain.py`
- Test: `cn_option_vix/tests/test_vix_chain.py`

**Step 1: Write the failing test**
```python
import math
from cn_option_vix.core.vix_chain import interpolate_to_target, select_near_next

def test_interpolation_between_equal_variances():
    # equal variances on both terms => VIX == sqrt(var)*100 regardless of days
    var = 0.25**2
    vix = interpolate_to_target(t1_days=23, var1=var, t2_days=37, var2=var, target_days=30)
    assert abs(vix - 25.0) < 1e-6

def test_select_near_next_rolls_when_too_close():
    # expiries 3, 31, 59 days; min_near_days=7 => near=31, next=59
    near, nxt = select_near_next([3, 31, 59], min_near_days=7)
    assert (near, nxt) == (31, 59)
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/core/vix_chain.py`**
```python
"""Near/next selection + constant-30-day interpolation (CBOE final step)."""
import math

def select_near_next(days_list, min_near_days: int):
    """days_list: sorted calendar-days-to-expiry. Near = first expiry with
    >= min_near_days; Next = the following expiry."""
    eligible = [d for d in sorted(days_list) if d >= min_near_days]
    if len(eligible) < 2:
        raise ValueError(f"need >=2 expiries with >= {min_near_days} days, got {eligible}")
    return eligible[0], eligible[1]

def interpolate_to_target(t1_days, var1, t2_days, var2, target_days=30, annual_days=365):
    """CBOE 30-day interpolation of total variance, annualized. Returns VIX (%)."""
    N1, N2, NT = t1_days, t2_days, target_days
    T1, T2 = N1/annual_days, N2/annual_days
    w1 = (N2 - NT) / (N2 - N1)
    w2 = (NT - N1) / (N2 - N1)
    interp = (T1*var1*w1 + T2*var2*w2) * (annual_days/NT)
    return 100.0 * math.sqrt(max(interp, 0.0))
```

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: near/next selection + 30-day VIX interpolation"`

---

## Task 5: Risk-free rate (data/rates.py)

**Files:**
- Create: `cn_option_vix/data/rates.py`
- Test: `cn_option_vix/tests/test_rates.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.data.rates import risk_free_rate

def test_rate_is_reasonable():
    r = risk_free_rate("2024-06-03", tenor_days=30)
    assert 0.0 <= r <= 0.10   # CN short rates within 0-10%
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/data/rates.py`.** Try RQ SHIBOR; fall back to a constant if unavailable (log a warning). Verify the exact RQ SHIBOR accessor during implementation (`rq.get_shibor` or the money-rate table); if neither exists use a fixed 0.02 with a `# TODO` and rely on the design note that rate sensitivity is small.
```python
"""Term-matched risk-free rate. SHIBOR if available, else constant fallback."""
import rqdatac as rq
from cn_option_vix.config import RQDATAC_URI

_DEFAULT = 0.02
_inited = False

def _ensure():
    global _inited
    if not _inited:
        rq.init(uri=RQDATAC_URI); _inited = True

def risk_free_rate(date, tenor_days: int) -> float:
    _ensure()
    try:
        sh = rq.get_shibor(start_date=date, end_date=date)  # verify accessor
        if sh is not None and len(sh):
            col = "3M" if tenor_days <= 45 else "6M"
            col = col if col in sh.columns else sh.columns[-1]
            return float(sh.iloc[-1][col]) / 100.0
    except Exception:
        pass
    return _DEFAULT
```

**Step 4: Run** → PASS (fallback guarantees a value).
**Step 5: Commit** — `git commit -m "feat: term-matched risk-free rate with fallback"`

---

## Task 6: Option chain snapshot (data/chains.py)

Pull, for one underlying on one date, the live chain: all strikes across the two 30-day-bracketing expiries, with settlement price (close fallback), call/put flag, and OI. Cache to parquet.

**Files:**
- Create: `cn_option_vix/data/chains.py`
- Test: `cn_option_vix/tests/test_chains.py`

**Step 1: Write the failing test** (integration — real RQ, a known liquid date)
```python
from cn_option_vix.data.chains import get_chain_snapshot

def test_510300_chain_snapshot():
    snap = get_chain_snapshot("510300.XSHG", "2024-06-03")
    assert snap["expiries"]                       # >=2 expiries returned
    near = snap["expiries"][0]
    df = snap["by_expiry"][near]
    # has calls & puts, positive strikes, a price column
    assert set(df["cp"]) == {"c", "p"}
    assert (df["strike"] > 0).all()
    assert "price" in df.columns and "oi" in df.columns
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/data/chains.py`.** Logic:
1. `rq.init(uri=RQDATAC_URI)`.
2. `all_instruments("Option")` filtered to `underlying_symbol == symbol` for index options use `underlying_symbol in {IO/HO/MO}`; keep rows with `listed_date <= date <= de_listed_date`.
3. Compute calendar days to `maturity_date`; pick the two expiries per `select_near_next` (import from core) — but chains.py just returns all live expiries sorted; selection happens in the per-instrument driver (Task 8).
4. For the contracts of those expiries, `rq.get_price(ids, date, date, "1d", fields=["settlement","close","open_interest","strike_price"])`. Build `price = settlement if settlement>0 else close`.
5. Split into calls/puts by `option_type` (C/P). Return dict `{underlying, date, expiries:[days...], by_expiry:{days: DataFrame[strike,cp,price,oi]}, spot}`.
6. Cache the raw pulled frame to `cn_option_vix/data/cache/<symbol>_<date>.parquet`; read cache if present (point-in-time: cache is immutable per date).

Provide the full implementation inline during execution; keep functions small (`_live_contracts`, `_prices`, `get_chain_snapshot`).

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: option chain snapshot loader + parquet cache"`

---

## Task 7: Per-instrument 30-day VIX driver (core/instrument_vix.py)

Wires Tasks 2-6 together: chain snapshot → per-expiry variance → 30-day VIX for ONE instrument on ONE date. Also returns instrument OI (for weights) and the ATM-IV cross-check.

**Files:**
- Create: `cn_option_vix/core/instrument_vix.py`
- Test: `cn_option_vix/tests/test_instrument_vix.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.core.instrument_vix import instrument_vix

def test_instrument_vix_reasonable():
    res = instrument_vix("510300.XSHG", "2024-06-03")
    assert res is not None
    assert 5.0 < res["vix"] < 80.0     # sane CN ETF vol range
    assert res["oi"] > 0
    assert res["n_strikes_near"] >= 5
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/core/instrument_vix.py`.** For the near and next expiry: build call/put dicts, `compute_forward`, `build_otm_series`, `single_expiry_variance`; then `interpolate_to_target`. Compute ATM IV via `rq.options.get_greeks` for the nearest-ATM contract and store `atm_iv` + `atm_gap = abs(vix/100 - atm_iv)`. Return `{symbol, date, vix, var30, oi, near_days, next_days, n_strikes_near, atm_iv, atm_gap, ok}`. Return `None` (or `ok=False`) when fewer than 2 usable expiries or too few strikes — the composite skips it.

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: per-instrument 30-day model-free VIX driver"`

---

## Task 8: Group membership & OI-weighted composite (aggregate/)

**Files:**
- Create: `cn_option_vix/aggregate/composite.py`
- Test: `cn_option_vix/tests/test_composite.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.aggregate.composite import aggregate_variances

def test_oi_weighted_variance_aggregation():
    # two instruments, vars 0.04 (vol .20) & 0.09 (vol .30), OI 3:1
    per_inst = [
        {"symbol":"A","group":"blue_chip","var30":0.04,"oi":300,"ok":True},
        {"symbol":"B","group":"blue_chip","var30":0.09,"oi":100,"ok":True},
    ]
    out = aggregate_variances(per_inst)
    exp_var = (0.04*300 + 0.09*100) / 400          # OI-weighted in variance space
    assert abs(out["groups"]["blue_chip"]["var"] - exp_var) < 1e-12
    assert abs(out["groups"]["blue_chip"]["vix"] - 100*exp_var**0.5) < 1e-9
    assert abs(out["overall"]["var"] - exp_var) < 1e-12   # only one group here

def test_dead_instruments_excluded_and_weights_renormalize():
    per_inst = [
        {"symbol":"A","group":"mid_small","var30":0.04,"oi":300,"ok":True},
        {"symbol":"B","group":"mid_small","var30":0.09,"oi":0,"ok":True},   # zero OI
        {"symbol":"C","group":"mid_small","var30":0.16,"oi":100,"ok":False},# bad chain
    ]
    out = aggregate_variances(per_inst)
    assert abs(out["groups"]["mid_small"]["var"] - 0.04) < 1e-12  # only A counts
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/aggregate/composite.py`.** For each group, take members with `ok and oi>0`, weight `var30` by `oi`, renormalize; `vix = 100*sqrt(var)`. Overall = OI-weighted mean of all qualifying instruments' `var30`. Return `{groups:{g:{var,vix,members,weight_sum}}, overall:{var,vix}}`. Also expose `index_vix` group naturally (it's just another group key).

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: OI-weighted variance-space composite (group + overall)"`

---

## Task 9: One-day snapshot (pipeline/one_day.py)

Compute all 12 instrument VIXs + the 6 published series for a single date. This is the unit the history loop calls.

**Files:**
- Create: `cn_option_vix/pipeline/one_day.py`
- Test: `cn_option_vix/tests/test_one_day.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.pipeline.one_day import compute_day

def test_compute_day_row():
    row = compute_day("2024-06-03")
    for col in ["overall","index_vix","blue_chip","sz_growth","mid_small","hard_tech"]:
        assert col in row and row[col] > 0
    assert row["n_instruments"] >= 6   # most instruments live by 2024
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/pipeline/one_day.py`.** Loop `ROSTER`, call `instrument_vix`, attach `group`; call `aggregate_variances`; flatten to a dict row: the 6 series (`overall` + 5 group keys), each instrument's `vix` as `iv_<symbol>`, `n_instruments`, and a `dq_flags` count (instruments with `atm_gap > atm_flag_threshold` or `ok=False`). Skip instruments that return `None`.

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: single-day VIX snapshot (6 series + diagnostics)"`

---

## Task 10: History backfill (pipeline/build_history.py) → parquet

**Files:**
- Create: `cn_option_vix/pipeline/build_history.py`
- Test: `cn_option_vix/tests/test_build_history.py`

**Step 1: Write the failing test** (short range)
```python
import os
from cn_option_vix.pipeline.build_history import build_history

def test_build_history_small_range(tmp_path):
    out = tmp_path/"vix.parquet"
    df = build_history("2024-06-03", "2024-06-07", out_path=str(out))
    assert os.path.exists(out)
    assert len(df) >= 3                      # ~4-5 trading days
    assert df["overall"].notna().all()
    assert df.index.is_monotonic_increasing  # date-indexed, sorted
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/pipeline/build_history.py`.** Get trading dates via `rq.get_trading_dates(start, end)`; call `compute_day` per date (wrap each in try/except → log & skip failures, never abort the loop); assemble a date-indexed DataFrame; write parquet to `cn_option_vix/outputs/vix_series.parquet` (or `out_path`); also write the 6 published columns to `vix_series.csv`. Print a one-line progress every ~20 days.

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: history backfill loop -> parquet + csv"`

---

## Task 11: Validation vs official iVIX (validate/ivix_compare.py) ← acceptance gate

**Files:**
- Create: `cn_option_vix/validate/ivix_compare.py`
- Test: `cn_option_vix/tests/test_ivix_validation.py`

**Step 1: Write the failing test** (the real acceptance criterion)
```python
from cn_option_vix.validate.ivix_compare import compare_to_ivix

def test_50etf_vix_matches_official_ivix():
    res = compare_to_ivix()   # 510050 vs 000188.XSHG over 2017-09-12..2017-12-25
    assert res["n"] >= 50                 # ~70 overlapping days
    assert res["corr"] >= 0.90            # design target 0.95; 0.90 gate for tolerance
    assert res["rmse"] < 3.0              # within ~3 vol points on level
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/validate/ivix_compare.py`.** Build the 510050 instrument-VIX series over `IVIX_WINDOW` via `instrument_vix` per trading day; pull `000188.XSHG` close over the same window; align on date; compute Pearson `corr`, `rmse`, `mean_bias`; return a dict + save an overlay plot to `outputs/plots/ivix_validation.png`. If the correlation gate fails, the method is wrong — debug forward/variance/interpolation before proceeding.

**Step 4: Run** → PASS (this proves the CBOE implementation is correct).
**Step 5: Commit** — `git commit -m "test: validate 50ETF VIX vs official 中国波指 iVIX"`

---

## Task 12: Daily update entrypoint (pipeline/update_daily.py)

**Files:**
- Create: `cn_option_vix/pipeline/update_daily.py`
- Test: `cn_option_vix/tests/test_update_daily.py`

**Step 1: Write the failing test**
```python
import pandas as pd
from cn_option_vix.pipeline.update_daily import update_daily

def test_update_appends_latest(tmp_path):
    p = tmp_path/"vix.parquet"
    seed = pd.DataFrame({"overall":[20.0]}, index=pd.to_datetime(["2024-06-03"]))
    seed.to_parquet(p)
    df = update_daily(out_path=str(p), asof="2024-06-04")
    assert pd.Timestamp("2024-06-04") in df.index
    assert pd.Timestamp("2024-06-03") in df.index   # preserved
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement `cn_option_vix/pipeline/update_daily.py`.** Read existing parquet (or empty), compute `compute_day(asof)` (default asof = latest trading date), append if absent, de-dup index, sort, re-write parquet + csv. Idempotent (re-running a date overwrites that row identically). Suitable for a cron/scheduler.

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: idempotent daily update entrypoint"`

---

## Task 13: Cross-venue spreads + data-quality report

**Files:**
- Modify: `cn_option_vix/pipeline/one_day.py` (add spread + DQ columns)
- Create: `cn_option_vix/pipeline/quality.py`
- Test: `cn_option_vix/tests/test_quality.py`

**Step 1: Write the failing test**
```python
from cn_option_vix.pipeline.one_day import compute_day

def test_spreads_present():
    row = compute_day("2024-06-03")
    # 沪深300 vol measured via Index VIX (IO) vs blue_chip ETF group
    assert "spread_index_bluechip" in row
    assert "spread_bluechip_szgrowth" in row
    assert "dq_flags" in row
```

**Step 2: Run to verify fail** → FAIL.

**Step 3: Implement.** In `compute_day`, add `spread_index_bluechip = index_vix - blue_chip`, `spread_bluechip_szgrowth = blue_chip - sz_growth`. `quality.py` aggregates per-day DQ: list of instruments dropped, count of close-fallback strikes (thread this count out of `chains.get_chain_snapshot`), and `atm_gap` flags; `build_history` writes a `outputs/quality_report.csv` alongside the parquet.

**Step 4: Run** → PASS.
**Step 5: Commit** — `git commit -m "feat: cross-venue spreads + data-quality report"`

---

## Task 14: Dashboard notebook (notebooks/vix_dashboard.ipynb)

**Files:**
- Create: `cn_option_vix/notebooks/vix_dashboard.ipynb`

**Step 1: Build the notebook** (no unit test; validated by running end-to-end). Cells:
1. Load `outputs/vix_series.parquet`.
2. Plot the 6 published series (Overall + Index VIX + 4 groups) with a Chinese-name legend (指数VIX / 大盘蓝筹 / 深市成长 / 中小盘 / 硬科技), event-annotated (2015/2016/2018/2020…).
3. Plot the cross-venue spreads.
4. Per-group term structure snapshot (near vs next vs 30d) for the latest date.
5. Reprint the iVIX-validation overlay from `outputs/plots/ivix_validation.png`.

**Step 2: Run all cells top-to-bottom.** Expected: no errors, 6-line chart renders.

**Step 3: Commit** — `git commit -m "feat: VIX dashboard notebook"`

---

## Task 15: README + run instructions

**Files:**
- Create: `cn_option_vix/README.md`

**Step 1:** Document: what it is (link the design doc), how to build history (`python -m cn_option_vix.pipeline.build_history`), how to update daily, where outputs land, the validation result, and the group definitions with Chinese names.

**Step 2: Commit** — `git commit -m "docs: cn_option_vix README"`

---

## Final acceptance checklist

- [ ] `pytest cn_option_vix/tests -v` all green (incl. the iVIX validation gate).
- [ ] `build_history` produces `vix_series.parquet` with 6 published series + 12 diagnostics + spreads + DQ, date-indexed from 2015 (50ETF) with dynamic membership.
- [ ] iVIX validation: corr ≥ 0.90 (target 0.95) over the 70-day overlap.
- [ ] Dashboard notebook renders all 6 series with Chinese-name legend.
- [ ] No look-ahead: every `VIX_t` uses only day-t settlement.

## Notes for the implementer
- **Verify RQ accessors at first use** — SHIBOR (`get_shibor` vs money-rate table), `get_greeks` maturity argument, and the exact `option_type` values (`C`/`P` vs `call`/`put`) in `all_instruments`. Adjust once, centrally.
- **CBOE reference:** the SSE iVIX used the CBOE 2003 white-paper method; matching `000188.XSHG` on the overlap is the correctness proof — if corr is low, the bug is almost always in strike trimming, K₀ selection, or the day-count in interpolation.
- **DRY:** import `select_near_next` from `core.vix_chain` everywhere; never re-implement day counting.
- **Point-in-time:** the chain cache is keyed by date and immutable — never overwrite a past date's cache.
```
