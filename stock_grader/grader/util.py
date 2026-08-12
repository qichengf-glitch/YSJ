"""
util.py -- shared primitives.

The important idea here is the `Metric` class. Every number that enters the
scoring engine carries its own provenance (source, period, actual-vs-estimate).
That mirrors the "CITE EVERYTHING" rule from the manual prompt: when the engine
prints an audit trail, each figure can name where it came from without anyone
having to trace it by hand.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Any, Optional

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.environ.get("STOCK_GRADER_DATA_DIR", os.path.join(ROOT, "data"))
SNAPSHOT_DIR = os.path.join(DATA_DIR, "snapshots")
REPORT_DIR = os.path.join(DATA_DIR, "reports")

for _d in (DATA_DIR, SNAPSHOT_DIR, REPORT_DIR):
    os.makedirs(_d, exist_ok=True)


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def get_logger(name: str = "grader") -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                                     datefmt="%H:%M:%S"))
    log.addHandler(h)
    fh = logging.FileHandler(os.path.join(DATA_DIR, "grader.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s"))
    log.addHandler(fh)
    return log


LOG = get_logger()


# --------------------------------------------------------------------------- #
# Metric: a number plus where it came from
# --------------------------------------------------------------------------- #
@dataclass
class Metric:
    """A single figure with full provenance. `value=None` means genuinely missing."""
    value: Optional[float]
    source: str = "unknown"          # e.g. "yfinance.cashflow"
    period: str = "n/a"              # e.g. "FY2025" or "LTM"
    kind: str = "Actual"             # "Actual" | "Estimate" | "Derived"
    note: str = ""

    @property
    def missing(self) -> bool:
        return self.value is None or (isinstance(self.value, float) and math.isnan(self.value))

    def cite(self) -> str:
        if self.missing:
            return "data missing"
        return f"{fmt_auto(self.value)} ({self.source}, {self.period}, {self.kind})"

    def to_dict(self) -> dict:
        return asdict(self)


def M(value, source="unknown", period="n/a", kind="Actual", note="") -> Metric:
    """Terse Metric constructor that normalises NaN and numpy scalars to None."""
    if value is None:
        return Metric(None, source, period, kind, note)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return Metric(None, source, period, kind, note or "non-numeric")
    if math.isnan(v) or math.isinf(v):
        return Metric(None, source, period, kind, note or "nan/inf")
    return Metric(v, source, period, kind, note)


MISSING = Metric(None, "n/a", "n/a", "Actual", "not sourced")


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def fmt_auto(v: Optional[float]) -> str:
    """Human-readable rendering that guesses a sensible unit."""
    if v is None:
        return "n/a"
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:,.2f}B"
    if a >= 1e6:
        return f"{v/1e6:,.1f}M"
    if a <= 3 and a >= 0.0001:
        return f"{v:.4g}"
    return f"{v:,.2f}"


def fmt_unit(v: Optional[float], unit: str) -> str:
    """Render a value using the unit declared in rubric.yaml."""
    if v is None:
        return "data missing"
    if unit == "pct":
        return f"{v * 100:.1f}%"
    if unit == "bps":
        return f"{v:+.0f}bps"
    if unit == "turns":
        return f"{v:.2f}x"
    if unit == "years":
        return "FCF-positive" if v >= 99 else f"{v:.2f}y"
    if unit in ("count", "points", "score", "grade_points"):
        return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"
    return f"{v:.2f}"


# --------------------------------------------------------------------------- #
# Safe numeric helpers -- never raise, always return None on failure
# --------------------------------------------------------------------------- #
def safe_div(a, b) -> Optional[float]:
    try:
        if a is None or b is None:
            return None
        a, b = float(a), float(b)
        if b == 0 or math.isnan(a) or math.isnan(b):
            return None
        r = a / b
        return None if (math.isnan(r) or math.isinf(r)) else r
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def cagr(begin, end, years) -> Optional[float]:
    """Compound annual growth rate. Undefined when the base is non-positive."""
    try:
        if begin is None or end is None or years is None or years <= 0:
            return None
        begin, end = float(begin), float(end)
        if begin <= 0 or end <= 0:
            return None
        return (end / begin) ** (1.0 / years) - 1.0
    except (TypeError, ValueError):
        return None


def pct_change(new, old) -> Optional[float]:
    try:
        if new is None or old is None or float(old) == 0:
            return None
        return (float(new) - float(old)) / abs(float(old))
    except (TypeError, ValueError):
        return None


def median(vals) -> Optional[float]:
    vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def percentile_rank(value, population) -> Optional[float]:
    """Fraction of the population at or below `value`. Used for GM vs peers."""
    pop = [p for p in population if p is not None]
    if value is None or len(pop) < 2:
        return None
    below = sum(1 for p in pop if p <= value)
    return below / len(pop)


# --------------------------------------------------------------------------- #
# DataFrame row lookup -- yfinance labels shift between versions, so accept
# a list of candidate row names and take the first that exists.
# --------------------------------------------------------------------------- #
def df_row(df, candidates, col_index: int = 0) -> Optional[float]:
    """Pull one cell from a yfinance statement frame (rows=line items, cols=periods)."""
    if df is None or getattr(df, "empty", True):
        return None
    if isinstance(candidates, str):
        candidates = [candidates]
    for name in candidates:
        if name in df.index:
            try:
                row = df.loc[name]
                if col_index >= len(row):
                    continue
                v = row.iloc[col_index]
                if v is None:
                    continue
                fv = float(v)
                if math.isnan(fv):
                    continue
                return fv
            except (KeyError, IndexError, TypeError, ValueError):
                continue
    return None


def df_row_series(df, candidates, max_periods: int = 10) -> list:
    """All periods for a line item, newest first. Missing periods become None."""
    if df is None or getattr(df, "empty", True):
        return []
    if isinstance(candidates, str):
        candidates = [candidates]
    for name in candidates:
        if name in df.index:
            try:
                row = df.loc[name]
                out = []
                for v in list(row)[:max_periods]:
                    try:
                        fv = float(v)
                        out.append(None if math.isnan(fv) else fv)
                    except (TypeError, ValueError):
                        out.append(None)
                return out
            except (KeyError, TypeError):
                continue
    return []


def col_periods(df, max_periods: int = 10) -> list:
    """Period labels for a statement frame, newest first, as 'FY2025' strings."""
    if df is None or getattr(df, "empty", True):
        return []
    out = []
    for c in list(df.columns)[:max_periods]:
        try:
            out.append(f"FY{c.year}")
        except AttributeError:
            out.append(str(c))
    return out


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_rubric() -> dict:
    return load_yaml(os.path.join(CONFIG_DIR, "rubric.yaml"))


def load_universe() -> dict:
    return load_yaml(os.path.join(CONFIG_DIR, "universe.yaml"))


def today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def parse_date(v) -> Optional[date]:
    """Accept datetime, date, or an ISO-ish string. Return None rather than raise."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(v)[:19], fmt).date()
        except ValueError:
            continue
    return None
