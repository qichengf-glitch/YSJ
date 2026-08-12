"""
metrics.py -- derive every scoreable field from the raw bundle.

Nothing here scores anything. This module answers exactly one question per
field: "what is the number, where did it come from, and what period is it?"
If a field cannot be sourced it becomes a Metric with value=None, which the
scoring engine then excludes from the median. It is never estimated.

Field naming matches the `field:` keys in rubric.yaml exactly.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .fetch import DataBundle, sec_metric
from .util import (LOG, M, Metric, cagr, col_periods, df_row, df_row_series,
                   median, pct_change, percentile_rank, safe_div)

# Candidate row labels. yfinance renames these between releases, and different
# filers use different line items, so every lookup tries several.
ROWS = {
    "revenue": ["Total Revenue", "Operating Revenue", "TotalRevenue"],
    "cogs": ["Cost Of Revenue", "Cost of Revenue", "CostOfRevenue"],
    "gross_profit": ["Gross Profit", "GrossProfit"],
    "ebit": ["EBIT", "Operating Income", "OperatingIncome"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "net_income": ["Net Income", "Net Income Common Stockholders",
                   "NetIncome", "Net Income From Continuing Operation Net Minority Interest"],
    "pretax_income": ["Pretax Income", "Income Before Tax", "PretaxIncome"],
    "tax_provision": ["Tax Provision", "Income Tax Expense", "TaxProvision"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating",
                         "InterestExpense"],
    "diluted_shares": ["Diluted Average Shares", "DilutedAverageShares",
                       "Basic Average Shares"],
    "total_assets": ["Total Assets", "TotalAssets"],
    "total_equity": ["Stockholders Equity", "Total Stockholder Equity",
                     "StockholdersEquity", "Common Stock Equity"],
    "total_debt": ["Total Debt", "TotalDebt"],
    "long_term_debt": ["Long Term Debt", "LongTermDebt"],
    "current_debt": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "cash": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments",
             "CashAndCashEquivalents"],
    "receivables": ["Accounts Receivable", "Receivables", "AccountsReceivable"],
    "inventory": ["Inventory", "Inventories"],
    "goodwill": ["Goodwill", "Goodwill And Other Intangible Assets"],
    "cfo": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities",
            "OperatingCashFlow"],
    "capex": ["Capital Expenditure", "CapitalExpenditure",
              "Purchase Of Property Plant And Equipment"],
    "fcf": ["Free Cash Flow", "FreeCashFlow"],
    "sbc": ["Stock Based Compensation", "StockBasedCompensation"],
    "dividends_paid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "impairment": ["Impairment Of Capital Assets", "Asset Impairment Charge",
                   "Goodwill Impairment"],
}

# XBRL tag fallbacks used when yfinance has a hole.
SEC_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "ebit": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "sbc": ["ShareBasedCompensation"],
    "total_equity": ["StockholdersEquity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "goodwill": ["Goodwill"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}


class MetricSet:
    """Dict of field -> Metric, with a namespace view for rubric expressions."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.m: dict = {}
        self.warnings: list = []

    def set(self, name: str, metric: Metric) -> None:
        self.m[name] = metric

    def get(self, name: str) -> Metric:
        from .util import MISSING
        return self.m.get(name, MISSING)

    def val(self, name: str) -> Optional[float]:
        return self.get(name).value

    def namespace(self) -> dict:
        """Plain {field: value} view for evaluating rubric `when:` expressions."""
        return {k: v.value for k, v in self.m.items()}

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.m.items()}

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        LOG.warning("[%s] %s", self.ticker, msg)


# =========================================================================== #
# Helpers
# =========================================================================== #
def _fx(b: DataBundle, v: Optional[float]) -> Optional[float]:
    """Convert a statement figure into the price currency."""
    return None if v is None else v * b.fx_rate


def _annual_series(b: DataBundle, df, key: str, n: int = 6) -> list:
    return df_row_series(df, ROWS[key], n)


def _sec_series(b: DataBundle, key: str, n: int = 6) -> list:
    """Annual series from EDGAR, newest first, values only."""
    tags = SEC_TAGS.get(key)
    if not tags or not b.sec_facts:
        return []
    unit = "shares" if key == "diluted_shares" else "USD"
    rows = sec_metric(b.sec_facts, tags, unit=unit, form="10-K", n=n)
    return [r[1] for r in rows]


def _with_fallback(b: DataBundle, ms: MetricSet, key: str, df, n: int = 6):
    """
    yfinance first, EDGAR second. Returns (series, source_label, periods).
    A series is only accepted if it has at least one non-None value.
    """
    ser = _annual_series(b, df, key, n)
    if any(v is not None for v in ser):
        return ser, "yfinance", col_periods(df, n)
    ser = _sec_series(b, key, n)
    if ser:
        LOG.info("[%s] %s sourced from SEC EDGAR fallback", b.ticker, key)
        return ser, "sec_edgar", [f"FY-{i}" for i in range(len(ser))]
    return [], "missing", []


# =========================================================================== #
# Main entry point
# =========================================================================== #
def build_metrics(b: DataBundle) -> MetricSet:
    ms = MetricSet(b.ticker)
    info = b.info or {}
    scrape = getattr(b, "scrape", {}) or {}

    # ---------------------------------------------------------------- basics
    price = (info.get("currentPrice") or info.get("regularMarketPrice")
             or info.get("previousClose"))
    mcap = info.get("marketCap")
    ms.set("price", M(price, "yfinance.info", "spot"))
    ms.set("market_cap", M(mcap, "yfinance.info", "spot"))
    ms.set("shares_outstanding", M(info.get("sharesOutstanding"), "yfinance.info", "spot"))
    ms.set("sector", Metric(None, "yfinance.info", "spot", "Actual",
                            str(info.get("sector") or "")))
    ms.set("industry", Metric(None, "yfinance.info", "spot", "Actual",
                              str(info.get("industry") or "")))

    ev = info.get("enterpriseValue")
    ms.set("enterprise_value", M(ev, "yfinance.info", "spot"))

    # ------------------------------------------------------- annual statements
    rev_s, rev_src, rev_per = _with_fallback(b, ms, "revenue", b.income)
    ni_s, ni_src, _ = _with_fallback(b, ms, "net_income", b.income)
    ebit_s, ebit_src, _ = _with_fallback(b, ms, "ebit", b.income)
    gp_s, _, _ = _with_fallback(b, ms, "gross_profit", b.income)
    cfo_s, cfo_src, _ = _with_fallback(b, ms, "cfo", b.cashflow)
    capex_s, _, _ = _with_fallback(b, ms, "capex", b.cashflow)
    sbc_s, _, _ = _with_fallback(b, ms, "sbc", b.cashflow)
    sh_s, _, _ = _with_fallback(b, ms, "diluted_shares", b.income)
    eq_s, _, _ = _with_fallback(b, ms, "total_equity", b.balance)
    gw_s, _, _ = _with_fallback(b, ms, "goodwill", b.balance)

    period0 = rev_per[0] if rev_per else "latest FY"

    ms.set("revenue", M(_fx(b, rev_s[0] if rev_s else None), f"{rev_src}.income", period0))
    ms.set("net_income", M(_fx(b, ni_s[0] if ni_s else None), f"{ni_src}.income", period0))
    ms.set("ebit", M(_fx(b, ebit_s[0] if ebit_s else None), f"{ebit_src}.income", period0))

    # --------------------------------------------------------------- LTM view
    # Prefer TTM frames; fall back to the latest annual so nothing goes blank.
    ttm_rev = df_row(b.ttm_income, ROWS["revenue"]) or (rev_s[0] if rev_s else None)
    ttm_ebit = df_row(b.ttm_income, ROWS["ebit"]) or (ebit_s[0] if ebit_s else None)
    ttm_ni = df_row(b.ttm_income, ROWS["net_income"]) or (ni_s[0] if ni_s else None)
    ttm_cfo = df_row(b.ttm_cashflow, ROWS["cfo"]) or (cfo_s[0] if cfo_s else None)
    ttm_capex = df_row(b.ttm_cashflow, ROWS["capex"]) or (capex_s[0] if capex_s else None)
    ttm_label = "LTM" if b.ttm_income is not None and not getattr(b.ttm_income, "empty", True) else period0

    ms.set("revenue_ltm", M(_fx(b, ttm_rev), "yfinance.ttm", ttm_label))
    ms.set("ebit_ltm", M(_fx(b, ttm_ebit), "yfinance.ttm", ttm_label))
    ms.set("net_income_ltm", M(_fx(b, ttm_ni), "yfinance.ttm", ttm_label))

    # capex is reported negative on the cash-flow statement; FCF = CFO + capex
    fcf_ltm = None
    if ttm_cfo is not None:
        fcf_ltm = ttm_cfo + (ttm_capex if ttm_capex is not None else 0.0)
    if fcf_ltm is None:
        fcf_ltm = info.get("freeCashflow")
    ms.set("fcf", M(_fx(b, fcf_ltm), "yfinance.ttm(CFO+capex)", ttm_label, "Derived"))

    # ------------------------------------------------------------ balance sheet
    cash = df_row(b.balance, ROWS["cash"]) or info.get("totalCash")
    debt = df_row(b.balance, ROWS["total_debt"]) or info.get("totalDebt")
    if debt is None:
        ltd = df_row(b.balance, ROWS["long_term_debt"])
        cd = df_row(b.balance, ROWS["current_debt"])
        debt = (ltd or 0) + (cd or 0) if (ltd or cd) else None
    equity = eq_s[0] if eq_s else None

    ms.set("cash", M(_fx(b, cash), "yfinance.balance", period0))
    ms.set("total_debt", M(_fx(b, debt), "yfinance.balance", period0))
    ms.set("total_equity", M(_fx(b, equity), "yfinance.balance", period0))
    ms.set("debt_due_24mo", M(_fx(b, df_row(b.balance, ROWS["current_debt"])),
                              "yfinance.balance", period0, "Actual",
                              "current portion only -- understates a 24mo wall"))

    net_debt = None if (debt is None) else debt - (cash or 0.0)
    ms.set("net_debt", M(_fx(b, net_debt), "derived", period0, "Derived"))

    # ---------------------------------------------------------------- EBITDA
    ebitda = info.get("ebitda")
    if ebitda is None and ttm_ebit is not None:
        da = df_row(b.ttm_cashflow, ["Depreciation And Amortization",
                                     "Depreciation Amortization Depletion"])
        ebitda = ttm_ebit + (da or 0.0)
    ms.set("ebitda", M(_fx(b, ebitda), "yfinance.info|derived", ttm_label, "Derived"))

    # =================================================================== 1. VALUATION
    ms.set("fcf_yield", M(safe_div(ms.val("fcf"), ms.val("market_cap")),
                          "derived(FCF/mktcap)", ttm_label, "Derived"))

    fwd_eps = info.get("forwardEps")
    fwd_pe = info.get("forwardPE") or safe_div(price, fwd_eps)
    ms.set("fwd_eps", M(fwd_eps, "yfinance.info", "NTM", "Estimate"))
    ms.set("fwd_pe", M(fwd_pe, "yfinance.info", "NTM", "Estimate"))

    # 5-yr own-history median P/E, reconstructed from price history and annual EPS.
    hist_pe_median = _historical_pe_median(b, ms)
    ms.set("pe_5yr_median", M(hist_pe_median, "derived(price hist / annual EPS)",
                              "5Y", "Actual"))
    # Positive = trading BELOW its own history = cheap.
    ms.set("pe_discount_vs_5yr_median",
           M(pct_change(hist_pe_median, fwd_pe) if (hist_pe_median and fwd_pe) else None,
             "derived", "5Y vs NTM", "Derived"))

    ms.set("ev_ebitda", M(safe_div(ms.val("enterprise_value"), ms.val("ebitda"))
                          or scrape.get("ev_ebitda"),
                          "derived|stockanalysis", ttm_label, "Derived"))

    peg = info.get("pegRatio") or info.get("trailingPegRatio")
    if peg is None:
        g = _fwd_eps_growth(b)
        peg = safe_div(fwd_pe, g * 100) if (fwd_pe and g and g > 0) else None
    ms.set("peg", M(peg, "yfinance.info|derived", "NTM", "Estimate"))

    # =================================================================== 2. GROWTH
    ms.set("fwd_revenue_growth", M(_fwd_revenue_growth(b), "yfinance.growth_estimates",
                                   "FY+1", "Estimate"))
    ms.set("fwd_eps_growth", M(_fwd_eps_growth(b), "yfinance.earnings_estimate",
                               "FY+1", "Estimate"))

    gm_series = _gross_margin_series(rev_s, gp_s)
    ms.set("gross_margin", M(gm_series[0] if gm_series else scrape.get("gross_margin"),
                             "derived(GP/rev)", period0))
    ms.set("gross_margin_trend_3y_bps", M(_gm_trend_bps(gm_series, 3), "derived",
                                          "3Y", "Derived"))
    ms.set("gross_margin_trend_2y_bps", M(_gm_trend_bps(gm_series, 2), "derived",
                                          "2Y", "Derived"))
    band = None
    valid_gm = [g for g in gm_series if g is not None]
    if len(valid_gm) >= 3:
        band = (max(valid_gm) - min(valid_gm)) * 10000
    ms.set("gross_margin_band_bps", M(band, "derived", f"{len(valid_gm)}Y", "Derived"))

    # Guidance history is not available from free sources -> explicitly missing.
    ms.set("guidance_net_raises_8q", Metric(None, "n/a", "8Q", "Actual",
                                            "guidance history not free-sourceable"))

    fcf_margin = safe_div(ms.val("fcf"), ms.val("revenue_ltm"))
    ms.set("fcf_margin", M(fcf_margin, "derived", ttm_label, "Derived"))
    r40 = None
    if ms.val("fwd_revenue_growth") is not None and fcf_margin is not None:
        r40 = ms.val("fwd_revenue_growth") * 100 + fcf_margin * 100
    ms.set("rule_of_40", M(r40, "derived", "FY+1 + LTM", "Derived"))
    # NRR is only ever disclosed in filings -> Tier 3 fills this if present.
    ms.set("nrr", Metric(None, "tier3", "latest 10-K", "Actual", "awaiting LLM extraction"))

    # =================================================================== 3. PROFITABILITY
    roic_series = _roic_series(b, rev_s, ebit_s, ni_s, eq_s)
    ms.set("roic_3y_avg", M(_avg(roic_series[:3]), "derived(NOPAT/invested capital)",
                            "3Y avg", "Derived"))
    valid_roic = [r for r in roic_series if r is not None]
    ms.set("roic_persistence",
           M(safe_div(sum(1 for r in valid_roic if r > 0.12), len(valid_roic))
             if valid_roic else None,
             "derived", f"{len(valid_roic)}Y", "Derived"))

    roe = info.get("returnOnEquity") or safe_div(ms.val("net_income_ltm"),
                                                 ms.val("total_equity"))
    ms.set("roe", M(roe or scrape.get("roe"), "yfinance.info|derived", ttm_label))

    d2e = info.get("debtToEquity")
    if d2e is not None and d2e > 5:      # yfinance reports this as a percentage
        d2e = d2e / 100.0
    if d2e is None:
        d2e = safe_div(ms.val("total_debt"), ms.val("total_equity"))
    ms.set("debt_to_equity", M(d2e, "yfinance.info|derived", period0))

    ms.set("efficiency_ratio", Metric(None, "n/a", "n/a", "Actual",
                                      "bank-specific; not in free sources"))
    ms.set("cet1_ratio", Metric(None, "n/a", "n/a", "Actual",
                                "bank-specific; not in free sources"))

    # =================================================================== 4. FINANCIALS
    ms.set("net_debt_to_ebitda", M(safe_div(ms.val("net_debt"), ms.val("ebitda")),
                                   "derived", ttm_label, "Derived"))

    int_exp = df_row(b.ttm_income, ROWS["interest_expense"]) \
        or df_row(b.income, ROWS["interest_expense"])
    int_exp = abs(int_exp) if int_exp else None
    ms.set("interest_expense", M(_fx(b, int_exp), "yfinance.income", ttm_label))
    # No debt service is a strength, not a divide-by-zero -- score it at the top band.
    ic = safe_div(ms.val("ebit_ltm"), ms.val("interest_expense"))
    if ic is None and (int_exp in (None, 0)) and (ms.val("ebit_ltm") or 0) > 0:
        ic = 999.0
    ms.set("interest_coverage", M(ic or scrape.get("interest_coverage"),
                                  "derived(EBIT/interest)", ttm_label, "Derived"))

    fcf_hist = [(c + (x or 0.0)) if c is not None else None
                for c, x in zip(cfo_s, capex_s + [None] * len(cfo_s))]
    cum_fcf = sum(v for v in fcf_hist[:3] if v is not None) if fcf_hist else None
    cum_ni = sum(v for v in ni_s[:3] if v is not None) if ni_s else None
    ms.set("cum_net_income_3y", M(_fx(b, cum_ni), "derived", "3Y", "Derived"))
    ms.set("fcf_to_ni_3y", M(safe_div(cum_fcf, cum_ni) if (cum_ni and cum_ni > 0) else None,
                             "derived", "3Y", "Derived"))

    streak = 0
    for c, n_ in zip(fcf_hist, ni_s):
        r = safe_div(c, n_) if (n_ and n_ > 0) else None
        if r is not None and r < 0.50:
            streak += 1
        else:
            break
    ms.set("fcf_ni_below_50_streak", M(streak, "derived", "annual", "Derived"))

    if len(sh_s) >= 4 and sh_s[0] and sh_s[3]:
        ms.set("share_count_cagr_3y", M(cagr(sh_s[3], sh_s[0], 3), "derived", "3Y", "Derived"))
    else:
        ms.set("share_count_cagr_3y", Metric(None, "derived", "3Y", "Derived",
                                             "fewer than 4 annual periods"))

    # Cash runway matters only when the company is burning cash.
    runway = 99.0
    if ms.val("fcf") is not None and ms.val("fcf") < 0 and ms.val("cash"):
        runway = safe_div(ms.val("cash"), abs(ms.val("fcf")))
    ms.set("cash_runway_years", M(runway, "derived(cash/burn)", ttm_label, "Derived"))

    div_paid = df_row_series(b.cashflow, ROWS["dividends_paid"], 3)
    dstreak = 0
    for d, f_ in zip(div_paid, fcf_hist):
        if d is not None and f_ is not None and abs(d) > f_ > 0:
            dstreak += 1
        else:
            break
    ms.set("dividend_fcf_payout_streak", M(dstreak, "derived", "annual", "Derived"))

    # ---- working-capital red-flag inputs
    ar_s = _annual_series(b, b.balance, "receivables", 3)
    inv_s = _annual_series(b, b.balance, "inventory", 3)
    ms.set("revenue_growth", M(pct_change(rev_s[0], rev_s[1]) if len(rev_s) > 1 else None,
                               "derived", "YoY", "Derived"))
    ms.set("ar_growth", M(pct_change(ar_s[0], ar_s[1]) if len(ar_s) > 1 else None,
                          "derived", "YoY", "Derived"))
    ms.set("inventory_growth", M(pct_change(inv_s[0], inv_s[1]) if len(inv_s) > 1 else None,
                                 "derived", "YoY", "Derived"))
    dso_now = safe_div(ar_s[0], rev_s[0]) * 365 if (ar_s and rev_s and ar_s[0] and rev_s[0]) else None
    dso_prev = safe_div(ar_s[1], rev_s[1]) * 365 if (len(ar_s) > 1 and len(rev_s) > 1
                                                     and ar_s[1] and rev_s[1]) else None
    ms.set("dso_yoy_change", M(pct_change(dso_now, dso_prev), "derived", "YoY", "Derived"))

    # =================================================================== 6. MANAGEMENT
    sbc_now = df_row(b.ttm_cashflow, ROWS["sbc"]) or (sbc_s[0] if sbc_s else None)
    sbc_pct = safe_div(sbc_now, ttm_rev)
    ms.set("sbc_pct_revenue", M(sbc_pct, "derived(SBC/rev)", ttm_label, "Derived"))
    sbc_prev = safe_div(sbc_s[1], rev_s[1]) if (len(sbc_s) > 1 and len(rev_s) > 1) else None
    ms.set("sbc_pct_revenue_yoy_change",
           M((sbc_pct - sbc_prev) if (sbc_pct is not None and sbc_prev is not None) else None,
             "derived", "YoY", "Derived"))

    beats, misses, streak_miss = _surprise_history(b)
    ms.set("beat_count_8q", M(beats, "yfinance.earnings_history", "last 4-8Q"))
    ms.set("consecutive_miss_streak", M(streak_miss, "yfinance.earnings_history", "recent Q"))

    gw_imp = _goodwill_impairment(b, gw_s, eq_s)
    ms.set("goodwill_impairment_pct_equity", M(gw_imp, "derived(goodwill step-down)",
                                               "YoY", "Derived"))

    ins = _insider_activity(b)
    ms.set("insider_net_score", M(ins["net_score"], "yfinance.insider_transactions",
                                  "6mo", "Actual", ins["detail"]))
    ms.set("insider_sell_cluster_90d", M(ins["sell_cluster_90d"],
                                         "yfinance.insider_transactions", "90d"))

    # =================================================================== 7. INCOME
    # Tier 3 fills these from the filing; deterministic part is revenue behaviour.
    ms.set("recurring_revenue_pct", Metric(None, "tier3", "latest 10-K", "Actual",
                                           "awaiting LLM extraction"))
    ms.set("rpo_coverage", Metric(None, "tier3", "latest 10-K", "Actual",
                                  "awaiting LLM extraction"))
    ms.set("max_customer_pct", Metric(None, "tier3", "latest 10-K", "Actual",
                                      "awaiting LLM extraction"))
    worst = None
    if len(rev_s) >= 3:
        chg = [pct_change(rev_s[i], rev_s[i + 1]) for i in range(len(rev_s) - 1)]
        chg = [c for c in chg if c is not None]
        worst = min(chg) if chg else None
    ms.set("worst_year_revenue_change", M(worst, "derived", f"{len(rev_s)}Y", "Derived"))

    # =================================================================== 8. SENTIMENT
    spf = info.get("shortPercentOfFloat")
    if spf is None:
        spf = safe_div(info.get("sharesShort"), info.get("floatShares"))
    ms.set("short_pct_float", M(spf, "yfinance.info", "latest settlement"))
    ms.set("short_ratio_days", M(info.get("shortRatio"), "yfinance.info",
                                 "latest settlement", "Actual", "days to cover"))
    ms.set("held_pct_institutions", M(info.get("heldPercentInstitutions"),
                                      "yfinance.info", "latest 13F"))
    ms.set("institutional_trend_score", M(_institutional_trend(b),
                                          "yfinance.institutional_holders", "QoQ",
                                          "Derived"))

    # =================================================================== 9. REVISIONS
    ms.set("fy2_eps_change_3mo", M(_fy2_change(b), "yfinance.eps_trend", "FY+1 vs 90d ago",
                                  "Estimate"))
    ms.set("revision_breadth_up", M(_revision_breadth(b), "yfinance.eps_revisions",
                                    "last 30d", "Estimate"))
    ms.set("estimate_dispersion", M(_dispersion(b), "yfinance.earnings_estimate",
                                    "FY+1", "Estimate"))
    ms.set("analyst_count", M(info.get("numberOfAnalystOpinions"), "yfinance.info", "spot"))
    ms.set("median_price_target", M(info.get("targetMedianPrice")
                                    or (b.price_targets or {}).get("median"),
                                    "yfinance.info", "NTM", "Estimate"))

    # =================================================================== 10. INDUSTRY
    ms.set("peer_median_fwd_growth", Metric(None, "comps", "FY+1", "Estimate",
                                            "filled by peer pass"))
    ms.set("tev_ebitda_discount_vs_peers", Metric(None, "comps", ttm_label, "Derived",
                                                  "filled by peer pass"))
    ms.set("gm_percentile_vs_peers", Metric(None, "comps", ttm_label, "Derived",
                                            "filled by peer pass"))

    # =================================================================== triggers
    ms.set("price_runup_6mo", M(_price_change(b, 126), "yfinance.history", "6mo", "Derived"))
    ms.set("price_change_30d", M(_price_change(b, 30), "yfinance.history", "30d", "Derived"))
    ms.set("volume_spike", M(_volume_spike(b), "yfinance.history", "30d", "Derived"))
    ms.set("next_earnings_date", Metric(None, "yfinance.calendar", "next", "Estimate",
                                        str(_next_earnings(b) or "")))
    ms.set("going_concern_flag", Metric(None, "tier3", "latest 10-K", "Actual",
                                        "awaiting LLM extraction"))
    ms.set("llm_moat_score", Metric(None, "tier3", "latest 10-K", "Actual",
                                    "awaiting LLM extraction"))

    missing = [k for k, v in ms.m.items() if v.missing]
    LOG.info("[%s] built %d metrics (%d missing)", b.ticker, len(ms.m), len(missing))
    return ms


# =========================================================================== #
# Sub-calculations
# =========================================================================== #
def _avg(vals) -> Optional[float]:
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def _gross_margin_series(rev_s, gp_s) -> list:
    out = []
    for i in range(min(len(rev_s), len(gp_s))):
        out.append(safe_div(gp_s[i], rev_s[i]))
    return out


def _gm_trend_bps(gm_series, years) -> Optional[float]:
    if len(gm_series) <= years:
        return None
    a, b_ = gm_series[0], gm_series[years]
    if a is None or b_ is None:
        return None
    return (a - b_) * 10000


def _roic_series(b: DataBundle, rev_s, ebit_s, ni_s, eq_s) -> list:
    """
    ROIC = NOPAT / invested capital, where
      NOPAT            = EBIT x (1 - effective tax rate)
      invested capital = total debt + total equity - cash
    Effective tax rate comes from the filed provision, clamped to [0, 0.5] so a
    one-off benefit or a valuation-allowance release cannot produce a nonsense
    negative rate that inflates NOPAT.
    """
    debt_s = df_row_series(b.balance, ROWS["total_debt"], 6)
    cash_s = df_row_series(b.balance, ROWS["cash"], 6)
    tax_s = df_row_series(b.income, ROWS["tax_provision"], 6)
    pre_s = df_row_series(b.income, ROWS["pretax_income"], 6)

    out = []
    for i in range(len(ebit_s)):
        ebit = ebit_s[i]
        if ebit is None:
            out.append(None)
            continue
        tr = safe_div(tax_s[i] if i < len(tax_s) else None,
                      pre_s[i] if i < len(pre_s) else None)
        tr = 0.21 if tr is None else min(max(tr, 0.0), 0.50)
        nopat = ebit * (1 - tr)
        debt = debt_s[i] if i < len(debt_s) else None
        eq = eq_s[i] if i < len(eq_s) else None
        cash = cash_s[i] if i < len(cash_s) else None
        if eq is None:
            out.append(None)
            continue
        ic = (debt or 0.0) + eq - (cash or 0.0)
        out.append(safe_div(nopat, ic) if ic and ic > 0 else None)
    return out


def _historical_pe_median(b: DataBundle, ms: MetricSet) -> Optional[float]:
    """
    Reconstruct a 5-yr median P/E: for each fiscal year-end, price on that date
    divided by that year's diluted EPS. Crude versus a true daily series, but
    it is honest arithmetic from sourced data rather than a recalled number.
    """
    if b.price_history is None or getattr(b.price_history, "empty", True):
        return None
    if b.income is None or getattr(b.income, "empty", True):
        return None
    ni_s = df_row_series(b.income, ROWS["net_income"], 6)
    sh_s = df_row_series(b.income, ROWS["diluted_shares"], 6)
    if not ni_s or not sh_s:
        return None

    try:
        import yfinance as _yf
        long_hist = _yf.Ticker(b.ticker).history(period="6y", auto_adjust=True)
    except Exception:                                          # noqa: BLE001
        long_hist = b.price_history
    if long_hist is None or getattr(long_hist, "empty", True):
        return None

    ratios = []
    for i, col in enumerate(list(b.income.columns)[:5]):
        if i >= len(ni_s) or i >= len(sh_s):
            break
        eps = safe_div(ni_s[i], sh_s[i])
        if eps is None or eps <= 0:
            continue
        try:
            ts = pd.Timestamp(col)
            if long_hist.index.tz is not None and ts.tz is None:
                ts = ts.tz_localize(long_hist.index.tz)
            window = long_hist.loc[:ts]
            if window.empty:
                continue
            px = float(window["Close"].iloc[-1])
            ratios.append(px / eps)
        except Exception:                                      # noqa: BLE001
            continue
    return median(ratios) if len(ratios) >= 3 else None


def _fwd_revenue_growth(b: DataBundle) -> Optional[float]:
    ge = b.growth_estimates
    if ge is not None and not getattr(ge, "empty", True):
        for idx in ("+1y", "0y"):
            if idx in ge.index:
                for col in ("revenueGrowth", "growth"):
                    if col in ge.columns:
                        try:
                            v = float(ge.loc[idx, col])
                            if not math.isnan(v):
                                return v
                        except (TypeError, ValueError, KeyError):
                            continue
    re_ = b.revenue_estimate
    if re_ is not None and not getattr(re_, "empty", True) and "growth" in re_.columns:
        for idx in ("+1y", "0y"):
            if idx in re_.index:
                try:
                    v = float(re_.loc[idx, "growth"])
                    if not math.isnan(v):
                        return v
                except (TypeError, ValueError, KeyError):
                    continue
    return (b.info or {}).get("revenueGrowth")


def _fwd_eps_growth(b: DataBundle) -> Optional[float]:
    """FY+1 consensus EPS vs FY0 consensus EPS."""
    ee = b.earnings_estimate
    if ee is not None and not getattr(ee, "empty", True) and "avg" in ee.columns:
        try:
            if "+1y" in ee.index and "0y" in ee.index:
                f1, f0 = float(ee.loc["+1y", "avg"]), float(ee.loc["0y", "avg"])
                if not math.isnan(f1) and not math.isnan(f0) and f0 > 0:
                    return (f1 - f0) / abs(f0)
        except (TypeError, ValueError, KeyError):
            pass
    ge = b.growth_estimates
    if ge is not None and not getattr(ge, "empty", True):
        for col in ("earningsGrowth", "growth"):
            if col in ge.columns and "+1y" in ge.index:
                try:
                    v = float(ge.loc["+1y", col])
                    if not math.isnan(v):
                        return v
                except (TypeError, ValueError, KeyError):
                    continue
    return (b.info or {}).get("earningsGrowth")


def _fy2_change(b: DataBundle) -> Optional[float]:
    """FY+1 consensus EPS now vs 90 days ago -- the revisions-momentum factor."""
    et = b.eps_trend
    if et is None or getattr(et, "empty", True) or "+1y" not in et.index:
        return None
    try:
        cur = float(et.loc["+1y", "current"])
        for col in ("90daysAgo", "60daysAgo", "30daysAgo"):
            if col in et.columns:
                old = float(et.loc["+1y", col])
                if not math.isnan(old) and old != 0 and not math.isnan(cur):
                    return (cur - old) / abs(old)
    except (TypeError, ValueError, KeyError):
        return None
    return None


def _revision_breadth(b: DataBundle) -> Optional[float]:
    er = b.eps_revisions
    if er is None or getattr(er, "empty", True) or "+1y" not in er.index:
        return None
    try:
        up = float(er.loc["+1y", "upLast30days"])
        down = float(er.loc["+1y", "downLast30days"])
        if math.isnan(up) or math.isnan(down) or (up + down) == 0:
            return None
        return up / (up + down)
    except (TypeError, ValueError, KeyError):
        return None


def _dispersion(b: DataBundle) -> Optional[float]:
    ee = b.earnings_estimate
    if ee is None or getattr(ee, "empty", True) or "+1y" not in ee.index:
        return None
    try:
        hi, lo, avg = (float(ee.loc["+1y", "high"]), float(ee.loc["+1y", "low"]),
                       float(ee.loc["+1y", "avg"]))
        if avg == 0 or math.isnan(hi) or math.isnan(lo):
            return None
        return (hi - lo) / abs(avg)
    except (TypeError, ValueError, KeyError):
        return None


def _surprise_history(b: DataBundle) -> tuple:
    """Return (beats, misses, current consecutive-miss streak) newest first."""
    eh = b.earnings_history
    if eh is None or getattr(eh, "empty", True):
        return None, None, None
    col = next((c for c in ("epsDifference", "surprisePercent", "epsActual")
                if c in eh.columns), None)
    if col is None:
        return None, None, None
    try:
        df = eh.sort_index(ascending=False)
        beats = misses = streak = 0
        streak_open = True
        for _, row in df.iterrows():
            if col == "epsActual":
                if "epsEstimate" not in df.columns:
                    continue
                a, e = row.get("epsActual"), row.get("epsEstimate")
                if a is None or e is None or (isinstance(a, float) and math.isnan(a)):
                    continue
                diff = float(a) - float(e)
            else:
                v = row.get(col)
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue
                diff = float(v)
            if diff > 0:
                beats += 1
                streak_open = False
            else:
                misses += 1
                if streak_open:
                    streak += 1
        return beats, misses, streak
    except Exception:                                          # noqa: BLE001
        return None, None, None


def _goodwill_impairment(b: DataBundle, gw_s, eq_s) -> Optional[float]:
    """
    Infer an impairment from a year-over-year step-down in goodwill. Acquisitions
    push goodwill up, so a fall is the signal. Only counts drops >2% to avoid
    flagging FX translation noise.
    """
    direct = df_row(b.income, ROWS["impairment"])
    if direct and eq_s and eq_s[0]:
        return abs(direct) / eq_s[0]
    if len(gw_s) < 2 or not gw_s[0] or not gw_s[1] or not eq_s or not eq_s[0]:
        return None
    drop = gw_s[1] - gw_s[0]
    if drop <= 0 or (drop / gw_s[1]) < 0.02:
        return None
    return drop / eq_s[0]


_BUY_RE = re.compile(r"purchase|buy|acquisition", re.I)
_SELL_RE = re.compile(r"\bsale\b|\bsold\b|sell|disposition", re.I)
_EXCLUDE_RE = re.compile(r"conversion|exercise|gift|grant|award|vest|10b5-1|tax", re.I)


def _insider_activity(b: DataBundle) -> dict:
    """
    Score open-market insider activity from -2 (heavy selling) to +2 (buy cluster).
    Option exercises, grants, vesting and 10b5-1 sales are excluded -- only
    discretionary open-market trades carry signal.
    """
    out = {"net_score": None, "sell_cluster_90d": None, "detail": ""}
    tx = b.insider_tx
    if tx is None or getattr(tx, "empty", True):
        return out

    date_col = next((c for c in ("Start Date", "startDate", "Date") if c in tx.columns), None)
    text_col = next((c for c in ("Text", "Transaction", "transactionText")
                     if c in tx.columns), None)
    val_col = next((c for c in ("Value", "value") if c in tx.columns), None)
    if text_col is None:
        return out

    now = datetime.now()
    buys = sells = 0
    buy_val = sell_val = 0.0
    sells_90d = 0

    for _, row in tx.iterrows():
        text = str(row.get(text_col, ""))
        if _EXCLUDE_RE.search(text):
            continue
        when = None
        if date_col:
            try:
                when = pd.to_datetime(row.get(date_col)).to_pydatetime().replace(tzinfo=None)
            except Exception:                                  # noqa: BLE001
                when = None
        if when and (now - when).days > 190:
            continue
        try:
            val = abs(float(row.get(val_col))) if val_col and row.get(val_col) else 0.0
        except (TypeError, ValueError):
            val = 0.0

        if _BUY_RE.search(text):
            buys += 1
            buy_val += val
        elif _SELL_RE.search(text):
            sells += 1
            sell_val += val
            if when and (now - when).days <= 90:
                sells_90d += 1

    if buys == 0 and sells == 0:
        out["detail"] = "no open-market transactions in trailing 6mo"
        out["net_score"] = 0.0
        out["sell_cluster_90d"] = 0
        return out

    total = buy_val + sell_val
    ratio = ((buy_val - sell_val) / total) if total > 0 else ((buys - sells) /
                                                              max(buys + sells, 1))
    score = max(-2.0, min(2.0, ratio * 2.0))
    if buys >= 3 and buy_val > sell_val:
        score = min(2.0, score + 0.5)               # cluster of buys, per the rubric

    out["net_score"] = round(score, 2)
    out["sell_cluster_90d"] = sells_90d
    out["detail"] = (f"{buys} open-market buys (${buy_val:,.0f}) vs "
                     f"{sells} sells (${sell_val:,.0f}), trailing 6mo")
    return out


def _institutional_trend(b: DataBundle) -> Optional[float]:
    """
    +1 accumulating / 0 neutral / -1 distributing, from the pctChange column of
    the top-holder table. Only the largest holders are visible for free, so this
    is directional evidence, not a full 13F aggregation.
    """
    ih = b.institutional
    if ih is None or getattr(ih, "empty", True):
        return None
    col = next((c for c in ("pctChange", "% Change", "Change") if c in ih.columns), None)
    if col is None:
        return None
    try:
        vals = [float(v) for v in ih[col].tolist()
                if v is not None and not (isinstance(v, float) and math.isnan(v))]
    except (TypeError, ValueError):
        return None
    if not vals:
        return None
    m = median(vals)
    if m is None:
        return None
    if m > 0.02:
        return 1.0
    if m < -0.02:
        return -1.0
    return 0.0


def _price_change(b: DataBundle, sessions: int) -> Optional[float]:
    ph = b.price_history
    if ph is None or getattr(ph, "empty", True) or len(ph) < sessions + 1:
        return None
    try:
        return float(ph["Close"].iloc[-1]) / float(ph["Close"].iloc[-sessions - 1]) - 1.0
    except Exception:                                          # noqa: BLE001
        return None


def _volume_spike(b: DataBundle) -> Optional[float]:
    ph = b.price_history
    if ph is None or getattr(ph, "empty", True) or len(ph) < 60:
        return None
    try:
        recent = float(ph["Volume"].iloc[-5:].mean())
        base = float(ph["Volume"].iloc[-60:-5].median())
        return safe_div(recent, base)
    except Exception:                                          # noqa: BLE001
        return None


def _next_earnings(b: DataBundle):
    cal = b.calendar or {}
    for key in ("Earnings Date", "earningsDate"):
        v = cal.get(key)
        if isinstance(v, (list, tuple)) and v:
            return v[0]
        if v:
            return v
    return None


# =========================================================================== #
# Peer comps grid -- the Capital IQ "Comparable Companies" replacement
# =========================================================================== #
def apply_peer_comps(ms: MetricSet, own: dict, peer_rows: list) -> None:
    """DEPRECATED -- superseded by peers.apply_peer_set, which validates each
    metric independently and enforces a per-metric minimum peer count.
    Kept so older snapshots and scripts still import cleanly."""
    from .peers import PeerCandidate, PeerSet, apply_peer_set
    ps = PeerSet(ticker=ms.ticker, archetype="B", source="legacy")
    ps.peers = [PeerCandidate(ticker=r.get("ticker", "?"),
                              ev_ebitda=r.get("ev_ebitda"),
                              gross_margin=r.get("gross_margin"),
                              fwd_revenue_growth=r.get("fwd_revenue_growth"))
                for r in peer_rows]
    apply_peer_set(ms, own, ps, min_peers=3)


def peer_snapshot(b: DataBundle) -> dict:
    """Cheap three-field summary of a peer, for the comps grid."""
    info = b.info or {}
    rev_s = df_row_series(b.income, ROWS["revenue"], 2)
    gp_s = df_row_series(b.income, ROWS["gross_profit"], 2)
    return {
        "ticker": b.ticker,
        "ev_ebitda": safe_div(info.get("enterpriseValue"), info.get("ebitda")),
        "gross_margin": (safe_div(gp_s[0], rev_s[0]) if (rev_s and gp_s) else
                         info.get("grossMargins")),
        "fwd_revenue_growth": _fwd_revenue_growth(b),
    }
