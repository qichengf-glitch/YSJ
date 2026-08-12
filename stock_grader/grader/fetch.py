"""
fetch.py -- data acquisition. This is the Capital IQ replacement layer.

Source hierarchy, in order of trust:
  1. yfinance          -- broad coverage, free, but field names drift between
                          versions and occasional fields go silently absent.
  2. SEC EDGAR XBRL    -- the `companyfacts` API. Official, free, no key, and
                          it is literally the filed data. Best fallback for any
                          US-listed issuer. Requires a real User-Agent.
  3. stockanalysis.com -- light HTML fallback for a handful of ratios.

Every accessor is wrapped so a failure downgrades to None rather than killing
the run. A pipeline that dies on one bad ticker is useless overnight.

CURRENCY: `info["currency"]` is the currency the SHARE PRICE trades in;
`info["financialCurrency"]` is the currency the STATEMENTS are filed in. For an
ADR these differ, which silently corrupts any ratio mixing price and financials
(FCF yield, EV/EBITDA, P/E). We detect the mismatch and convert statements into
the price currency before any ratio is computed.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests

from .util import LOG, DATA_DIR, parse_date

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None
    LOG.error("yfinance is not installed -- run: pip install yfinance")

CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

_FX_CACHE: dict = {}
_SEC_TICKER_CACHE: Optional[dict] = None


# ===========================================================================
# Generic guard
# ===========================================================================
def _try(fn, what: str, default=None):
    """Run `fn`, log and swallow any failure. Keeps one bad field from
    aborting a whole ticker."""
    try:
        return fn()
    except Exception as e:                                   # noqa: BLE001
        LOG.debug("fetch: %s unavailable (%s: %s)", what, type(e).__name__, e)
        return default


# ===========================================================================
# The bundle every downstream module consumes
# ===========================================================================
class DataBundle:
    """Everything fetched for one ticker, plus an audit list of what failed."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.info: dict = {}
        self.income: Optional[pd.DataFrame] = None            # annual
        self.balance: Optional[pd.DataFrame] = None
        self.cashflow: Optional[pd.DataFrame] = None
        self.q_income: Optional[pd.DataFrame] = None          # quarterly
        self.q_balance: Optional[pd.DataFrame] = None
        self.q_cashflow: Optional[pd.DataFrame] = None
        self.ttm_income: Optional[pd.DataFrame] = None
        self.ttm_cashflow: Optional[pd.DataFrame] = None
        self.earnings_history: Optional[pd.DataFrame] = None
        self.eps_trend: Optional[pd.DataFrame] = None
        self.eps_revisions: Optional[pd.DataFrame] = None
        self.earnings_estimate: Optional[pd.DataFrame] = None
        self.revenue_estimate: Optional[pd.DataFrame] = None
        self.growth_estimates: Optional[pd.DataFrame] = None
        self.insider_tx: Optional[pd.DataFrame] = None
        self.insider_purchases: Optional[pd.DataFrame] = None
        self.institutional: Optional[pd.DataFrame] = None
        self.price_history: Optional[pd.DataFrame] = None
        self.calendar: dict = {}
        self.price_targets: dict = {}
        self.sec_facts: dict = {}
        self.fx_rate: float = 1.0
        self.price_currency: str = "USD"
        self.financial_currency: str = "USD"
        self.errors: list = []
        self.fetched_at: str = datetime.now().isoformat(timespec="seconds")

    def note_error(self, msg: str) -> None:
        self.errors.append(msg)
        LOG.warning("[%s] %s", self.ticker, msg)


# ===========================================================================
# yfinance
# ===========================================================================
def fetch_yfinance(ticker: str, bundle: DataBundle) -> DataBundle:
    if yf is None:
        bundle.note_error("yfinance unavailable")
        return bundle

    tk = yf.Ticker(ticker)

    bundle.info = _try(lambda: dict(tk.info or {}), "info", {}) or {}
    if not bundle.info:
        bundle.note_error("info dict empty -- ticker may be delisted or wrong")

    bundle.income = _try(lambda: tk.income_stmt, "income_stmt")
    bundle.balance = _try(lambda: tk.balance_sheet, "balance_sheet")
    bundle.cashflow = _try(lambda: tk.cashflow, "cashflow")
    bundle.q_income = _try(lambda: tk.quarterly_income_stmt, "quarterly_income_stmt")
    bundle.q_balance = _try(lambda: tk.quarterly_balance_sheet, "quarterly_balance_sheet")
    bundle.q_cashflow = _try(lambda: tk.quarterly_cashflow, "quarterly_cashflow")
    bundle.ttm_income = _try(lambda: tk.ttm_income_stmt, "ttm_income_stmt")
    bundle.ttm_cashflow = _try(lambda: tk.ttm_cashflow, "ttm_cashflow")

    bundle.earnings_history = _try(lambda: tk.earnings_history, "earnings_history")
    bundle.eps_trend = _try(lambda: tk.eps_trend, "eps_trend")
    bundle.eps_revisions = _try(lambda: tk.eps_revisions, "eps_revisions")
    bundle.earnings_estimate = _try(lambda: tk.earnings_estimate, "earnings_estimate")
    bundle.revenue_estimate = _try(lambda: tk.revenue_estimate, "revenue_estimate")
    bundle.growth_estimates = _try(lambda: tk.growth_estimates, "growth_estimates")

    bundle.insider_tx = _try(lambda: tk.insider_transactions, "insider_transactions")
    bundle.insider_purchases = _try(lambda: tk.insider_purchases, "insider_purchases")
    bundle.institutional = _try(lambda: tk.institutional_holders, "institutional_holders")

    bundle.price_history = _try(lambda: tk.history(period="1y", auto_adjust=True),
                                "price_history")

    cal = _try(lambda: tk.calendar, "calendar", {})
    bundle.calendar = cal if isinstance(cal, dict) else {}

    pt = _try(lambda: tk.analyst_price_targets, "analyst_price_targets", {})
    bundle.price_targets = pt if isinstance(pt, dict) else {}

    bundle.price_currency = (bundle.info.get("currency") or "USD").upper()
    bundle.financial_currency = (bundle.info.get("financialCurrency")
                                 or bundle.price_currency).upper()
    return bundle


# ===========================================================================
# SEC EDGAR XBRL -- the serious fallback
# ===========================================================================
def _sec_headers(user_agent: str) -> dict:
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"}


def sec_lookup_cik(ticker: str, user_agent: str) -> Optional[int]:
    """Resolve ticker -> CIK using the SEC's own mapping file, cached on disk."""
    global _SEC_TICKER_CACHE
    cache_file = os.path.join(CACHE_DIR, "sec_tickers.json")

    if _SEC_TICKER_CACHE is None:
        fresh = (os.path.exists(cache_file) and
                 time.time() - os.path.getmtime(cache_file) < 30 * 86400)
        if fresh:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    _SEC_TICKER_CACHE = json.load(f)
            except (OSError, json.JSONDecodeError):
                _SEC_TICKER_CACHE = None
        if _SEC_TICKER_CACHE is None:
            try:
                r = requests.get(SEC_TICKER_MAP_URL, timeout=30,
                                 headers={"User-Agent": user_agent})
                r.raise_for_status()
                raw = r.json()
                _SEC_TICKER_CACHE = {v["ticker"].upper(): int(v["cik_str"])
                                     for v in raw.values()}
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(_SEC_TICKER_CACHE, f)
            except Exception as e:                            # noqa: BLE001
                LOG.warning("SEC ticker map fetch failed: %s", e)
                _SEC_TICKER_CACHE = {}
    return _SEC_TICKER_CACHE.get(ticker.upper())


def fetch_sec_facts(ticker: str, user_agent: str, cache_days: int = 7) -> dict:
    """Pull the XBRL companyfacts blob. Cached -- it is large and slow-moving."""
    cik = sec_lookup_cik(ticker, user_agent)
    if cik is None:
        LOG.info("[%s] no SEC CIK (likely non-US listing) -- EDGAR fallback off", ticker)
        return {}

    cache_file = os.path.join(CACHE_DIR, f"secfacts_{ticker.upper()}.json")
    if (os.path.exists(cache_file) and
            time.time() - os.path.getmtime(cache_file) < cache_days * 86400):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    try:
        time.sleep(0.12)                                  # SEC asks for <10 req/s
        r = requests.get(SEC_FACTS_URL.format(cik=cik), timeout=45,
                         headers=_sec_headers(user_agent))
        r.raise_for_status()
        data = r.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data
    except Exception as e:                                    # noqa: BLE001
        LOG.warning("[%s] SEC companyfacts fetch failed: %s", ticker, e)
        return {}


def sec_metric(facts: dict, tags: list, unit: str = "USD",
               form: str = "10-K", n: int = 1) -> list:
    """
    Extract annual values for the first matching us-gaap tag.
    Returns [(fiscal_year, value, end_date), ...] newest first.

    `tags` is a list because the same concept has several XBRL names across
    filers (e.g. Revenues vs RevenueFromContractWithCustomerExcludingAssessedTax).
    """
    if not facts:
        return []
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        series = node.get("units", {}).get(unit)
        if not series:
            continue
        rows = []
        for item in series:
            if item.get("form") != form or item.get("fp") != "FY":
                continue
            # Annual duration facts only: reject quarterly/partial periods.
            start, end = parse_date(item.get("start")), parse_date(item.get("end"))
            if start and end and not (330 <= (end - start).days <= 400):
                continue
            rows.append((item.get("fy"), item.get("val"), item.get("end")))
        if rows:
            seen, out = set(), []
            for fy, val, end in sorted(rows, key=lambda r: r[2] or "", reverse=True):
                if fy in seen:
                    continue
                seen.add(fy)
                out.append((fy, val, end))
            return out[:n] if n else out
    return []


def fetch_sec_latest_filing_text(ticker: str, user_agent: str,
                                 forms=("10-K", "10-Q"),
                                 max_chars: int = 400_000) -> tuple:
    """
    Download the most recent 10-K (or 10-Q) primary document and strip it to
    text. Returns (text, form_type, filing_date, url). Feeds the Tier 3 pass.
    """
    cik = sec_lookup_cik(ticker, user_agent)
    if cik is None:
        return "", "", "", ""

    try:
        time.sleep(0.12)
        r = requests.get(SEC_SUBMISSIONS_URL.format(cik=cik), timeout=45,
                         headers=_sec_headers(user_agent))
        r.raise_for_status()
        recent = r.json().get("filings", {}).get("recent", {})
    except Exception as e:                                    # noqa: BLE001
        LOG.warning("[%s] SEC submissions fetch failed: %s", ticker, e)
        return "", "", "", ""

    forms_list = recent.get("form", [])
    for i, form in enumerate(forms_list):
        if form not in forms:
            continue
        accession = recent["accessionNumber"][i].replace("-", "")
        primary = recent["primaryDocument"][i]
        filed = recent["filingDate"][i]
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
               f"{accession}/{primary}")
        try:
            time.sleep(0.12)
            doc = requests.get(url, timeout=90,
                               headers={"User-Agent": user_agent})
            doc.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(doc.content, "lxml")
            for tag in soup(["script", "style", "table"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ").split())
            return text[:max_chars], form, filed, url
        except Exception as e:                                # noqa: BLE001
            LOG.warning("[%s] filing document fetch failed: %s", ticker, e)
            return "", form, filed, url
    return "", "", "", ""


# ===========================================================================
# stockanalysis.com -- light HTML fallback for a few ratios
# ===========================================================================
def fetch_stockanalysis_ratios(ticker: str) -> dict:
    """Best-effort scrape of a handful of ratios. Returns {} on any failure."""
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/ratios/"
    try:
        tables = pd.read_html(url)
    except Exception as e:                                    # noqa: BLE001
        LOG.debug("[%s] stockanalysis fallback unavailable: %s", ticker, e)
        return {}

    out = {}
    wanted = {
        "PE Ratio": "pe_ratio", "PS Ratio": "ps_ratio", "PB Ratio": "pb_ratio",
        "EV/EBITDA": "ev_ebitda", "EV/Sales": "ev_sales",
        "Debt / EBITDA": "debt_ebitda", "Interest Coverage": "interest_coverage",
        "Return on Equity (ROE)": "roe", "Return on Capital (ROIC)": "roic",
        "Gross Margin": "gross_margin", "FCF Yield": "fcf_yield",
    }
    for tbl in tables:
        if tbl.empty or tbl.shape[1] < 2:
            continue
        first = tbl.columns[0]
        for _, row in tbl.iterrows():
            label = str(row[first]).strip()
            if label in wanted:
                try:
                    val = str(row.iloc[1]).replace("%", "").replace(",", "").strip()
                    if val in ("-", "", "nan", "Upgrade"):
                        continue
                    num = float(val)
                    if "%" in str(row.iloc[1]) or wanted[label] in (
                            "roe", "roic", "gross_margin", "fcf_yield"):
                        num /= 100.0
                    out[wanted[label]] = num
                except (TypeError, ValueError):
                    continue
    if out:
        LOG.info("[%s] stockanalysis fallback supplied: %s", ticker, sorted(out))
    return out


# ===========================================================================
# FX
# ===========================================================================
def get_fx_rate(from_ccy: str, to_ccy: str) -> float:
    """Spot FX via yfinance. Returns 1.0 on failure and logs loudly, because a
    silently wrong rate is worse than an obvious no-op."""
    from_ccy, to_ccy = from_ccy.upper(), to_ccy.upper()
    if from_ccy == to_ccy:
        return 1.0
    key = f"{from_ccy}{to_ccy}"
    if key in _FX_CACHE:
        return _FX_CACHE[key]
    if yf is None:
        return 1.0
    for pair, invert in ((f"{from_ccy}{to_ccy}=X", False),
                         (f"{to_ccy}{from_ccy}=X", True)):
        try:
            hist = yf.Ticker(pair).history(period="5d")
            if hist is not None and not hist.empty:
                rate = float(hist["Close"].iloc[-1])
                if rate > 0:
                    rate = (1.0 / rate) if invert else rate
                    _FX_CACHE[key] = rate
                    return rate
        except Exception:                                     # noqa: BLE001
            continue
    LOG.error("FX %s->%s unavailable; using 1.0. Ratios mixing price and "
              "financials will be WRONG for this ticker.", from_ccy, to_ccy)
    return 1.0


# ===========================================================================
# Orchestrator
# ===========================================================================
def fetch_all(ticker: str, sec_user_agent: str, use_sec: bool = True,
              use_scrape_fallback: bool = True) -> DataBundle:
    """Fetch every source for one ticker and resolve the currency question."""
    LOG.info("[%s] fetching...", ticker)
    b = DataBundle(ticker)
    fetch_yfinance(ticker, b)

    if use_sec:
        b.sec_facts = fetch_sec_facts(ticker, sec_user_agent)
        if b.sec_facts:
            LOG.info("[%s] SEC companyfacts available", ticker)

    if use_scrape_fallback:
        b.scrape = fetch_stockanalysis_ratios(ticker)         # type: ignore[attr-defined]
    else:
        b.scrape = {}                                         # type: ignore[attr-defined]

    if b.financial_currency != b.price_currency:
        b.fx_rate = get_fx_rate(b.financial_currency, b.price_currency)
        LOG.info("[%s] statements in %s, price in %s -- applying FX %.4f",
                 ticker, b.financial_currency, b.price_currency, b.fx_rate)
    return b
