"""
peers.py -- automatic peer-set construction. The Capital IQ comps grid, rebuilt.

Three sub-metrics need a peer group:
    valuation.tev_ebitda_vs_peers    fwd TEV/EBITDA vs peer median
    profitability.gm_vs_peers        gross margin percentile vs peers
    industry.peer_median_growth      peer-median forward revenue growth

DESIGN PRINCIPLE
A median computed from a bad peer set is WORSE than `data missing`, because it
looks authoritative. So this module is built to refuse rather than guess: every
candidate must survive hard gates, the final set must clear a minimum count, and
the count is checked PER METRIC rather than per peer.

CANDIDATE SOURCES, in order of trust
  1. manual        universe.yaml `peers:` -- your judgment, always wins
  2. screener      Yahoo equity screener filtered by industry + market-cap band
  3. industry      yf.Industry(key).top_companies for the exact industry
  4. sic           SEC EDGAR companies sharing the filer's 4-digit SIC code
  5. sector        sector-level screener -- last resort, always low confidence

Sources 2-5 are unioned, then ranked by a similarity score and truncated. Using
several independent sources matters: Yahoo's industry taxonomy and the SEC's SIC
codes disagree often enough that agreement between them is real evidence a
candidate belongs in the set.

PER-METRIC VALIDITY
A peer with negative EBITDA cannot contribute an EV/EBITDA figure but its gross
margin is still perfectly good. Filtering whole peers would throw away sound
data, so each metric is validated independently and carries its own peer count.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import requests

from .util import DATA_DIR, LOG, load_yaml, median, parse_date, safe_div

try:
    import yfinance as yf
except ImportError:                                            # pragma: no cover
    yf = None

PEER_DIR = os.path.join(DATA_DIR, "peers")
os.makedirs(PEER_DIR, exist_ok=True)

SEC_SIC_BROWSE = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                  "&SIC={sic}&type=10-K&dateb=&owner=include&count={count}"
                  "&action=getcompany&output=atom")

# --------------------------------------------------------------------------- #
# Hard validity gates. A value failing these is not a datapoint, it is noise.
# --------------------------------------------------------------------------- #
METRIC_GATES = {
    # EV/EBITDA is undefined when EBITDA <= 0; >100x is a near-zero denominator,
    # not a rich multiple. Both must be excluded or they corrupt the median.
    "ev_ebitda": (0.5, 100.0),
    "gross_margin": (-0.50, 1.00),
    "fwd_revenue_growth": (-0.90, 5.00),
}

# Archetype-specific peer parameters. Cyclicals compare across the whole cycle
# so size matters less; biotechs and banks have metrics that simply do not apply.
ARCHETYPE_PEER_PARAMS = {
    "A": {"size_band": 12.0, "min_peers": 4, "size_weight": 0.35},
    "B": {"size_band": 12.0, "min_peers": 4, "size_weight": 0.35},
    "C": {"size_band": 25.0, "min_peers": 3, "size_weight": 0.25},
    "D": {"size_band": 30.0, "min_peers": 3, "size_weight": 0.15},
    "E": {"size_band": 40.0, "min_peers": 3, "size_weight": 0.10},
    "F": {"size_band": 20.0, "min_peers": 3, "size_weight": 0.30},
    "G": {"size_band": 30.0, "min_peers": 3, "size_weight": 0.20},
}
DEFAULT_PEER_PARAMS = {"size_band": 15.0, "min_peers": 4, "size_weight": 0.30}

# EV/EBITDA is meaningless for these archetypes -- banks do not have enterprise
# value in any usable sense, and clinical-stage biotechs have negative EBITDA.
EV_EBITDA_NA_ARCHETYPES = {"E", "F"}


# =========================================================================== #
# Containers
# =========================================================================== #
@dataclass
class PeerCandidate:
    ticker: str
    name: str = ""
    sources: list = field(default_factory=list)     # which sources proposed it
    market_cap: Optional[float] = None
    sector: str = ""
    industry: str = ""
    sic: Optional[str] = None
    quote_type: str = ""
    currency: str = ""
    # comps metrics
    ev_ebitda: Optional[float] = None
    gross_margin: Optional[float] = None
    fwd_revenue_growth: Optional[float] = None
    # ranking
    similarity: float = 0.0
    score_detail: str = ""
    excluded_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PeerSet:
    ticker: str
    archetype: str
    source: str = "auto"                 # manual | auto | none
    built_at: str = ""
    own_industry: str = ""
    own_sector: str = ""
    own_sic: Optional[str] = None
    own_market_cap: Optional[float] = None
    peers: list = field(default_factory=list)        # accepted PeerCandidates
    rejected: list = field(default_factory=list)     # (ticker, reason)
    metric_counts: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)   # per metric
    warnings: list = field(default_factory=list)
    sources_used: list = field(default_factory=list)

    @property
    def tickers(self) -> list:
        return [p.ticker for p in self.peers]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["peers"] = [p.to_dict() for p in self.peers]
        return d

    def audit(self) -> str:
        L = [f"  PEER SET for {self.ticker} ({self.archetype}) -- source: {self.source}",
             f"    own: {self.own_industry or 'n/a'} | SIC {self.own_sic or 'n/a'} | "
             f"mcap {_fmt_cap(self.own_market_cap)}",
             f"    discovery sources: {', '.join(self.sources_used) or 'none'}",
             f"    accepted {len(self.peers)} peers:"]
        for p in self.peers:
            L.append(f"      {p.ticker:<7} {_fmt_cap(p.market_cap):>8}  "
                     f"sim {p.similarity:.2f}  [{'+'.join(p.sources)}]  "
                     f"{p.industry[:28]}")
        for m, n in self.metric_counts.items():
            L.append(f"    {m:<22} n={n:<3} confidence={self.confidence.get(m,'n/a')}")
        if self.rejected:
            L.append(f"    rejected {len(self.rejected)}:")
            for tk, why in self.rejected[:10]:
                L.append(f"      {tk:<7} {why}")
            if len(self.rejected) > 10:
                L.append(f"      ... and {len(self.rejected)-10} more")
        for w in self.warnings:
            L.append(f"    WARNING: {w}")
        return "\n".join(L)


def _fmt_cap(v) -> str:
    if v is None:
        return "n/a"
    if v >= 1e12:
        return f"${v/1e12:.1f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


# =========================================================================== #
# Source 2 -- Yahoo equity screener (primary)
# =========================================================================== #
def _screener_candidates(industry: str, sector: str, own_cap: Optional[float],
                         size_band: float, limit: int = 60) -> list:
    """
    One screener call returns every listed name in the industry inside a
    market-cap band. Far cheaper than probing tickers one at a time, and the
    response often carries the comps metrics already.
    """
    if yf is None or not industry:
        return []
    try:
        filters = [yf.EquityQuery("eq", ["industry", industry])]
        if own_cap and own_cap > 0:
            lo = max(5e7, own_cap / size_band)
            hi = own_cap * size_band
            filters.append(yf.EquityQuery("gt", ["intradaymarketcap", lo]))
            filters.append(yf.EquityQuery("lt", ["intradaymarketcap", hi]))
        q = yf.EquityQuery("and", filters) if len(filters) > 1 else filters[0]
        resp = yf.screen(q, size=min(limit, 250), sortField="intradaymarketcap",
                         sortAsc=False)
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("screener query failed for industry '%s': %s", industry, e)
        return []

    quotes = _extract_quotes(resp)
    out = []
    for qd in quotes:
        sym = (qd.get("symbol") or "").strip().upper()
        if not sym:
            continue
        out.append(PeerCandidate(
            ticker=sym,
            name=qd.get("shortName") or qd.get("longName") or "",
            sources=["screener"],
            market_cap=_num(qd.get("marketCap") or qd.get("intradaymarketcap")),
            sector=qd.get("sector") or sector,
            industry=qd.get("industry") or industry,
            quote_type=(qd.get("quoteType") or "").upper(),
            currency=(qd.get("currency") or "").upper(),
            # present on some responses; validated later either way
            ev_ebitda=_num(qd.get("lastclosetevebitda.lasttwelvemonths")),
            gross_margin=_pct(qd.get("grossprofitmargin.lasttwelvemonths")),
        ))
    LOG.info("screener returned %d candidates for industry '%s'", len(out), industry)
    return out


def _extract_quotes(resp) -> list:
    """yfinance has returned several response shapes across versions."""
    if resp is None:
        return []
    if isinstance(resp, dict):
        for key in ("quotes", "records", "result"):
            v = resp.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("quotes"), list):
                return v["quotes"]
        if resp.get("symbol"):
            return [resp]
        return []
    if hasattr(resp, "to_dict"):                     # DataFrame
        try:
            recs = resp.reset_index().to_dict("records")
            for r in recs:
                if "symbol" not in r and "index" in r:
                    r["symbol"] = r["index"]
            return recs
        except Exception:                                      # noqa: BLE001
            return []
    if isinstance(resp, list):
        return resp
    return []


def _num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _pct(v) -> Optional[float]:
    """Yahoo returns margins as either 0.42 or 42.0 depending on the endpoint."""
    f = _num(v)
    if f is None:
        return None
    return f / 100.0 if abs(f) > 1.5 else f


# =========================================================================== #
# Source 3 -- yf.Industry top companies
# =========================================================================== #
def _industry_key(industry: str) -> str:
    """'Semiconductor Equipment & Materials' -> 'semiconductor-equipment-materials'"""
    s = industry.lower().replace("&", "").replace("/", " ")
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", "-", s.strip())


def _industry_candidates(industry: str, limit: int = 40) -> list:
    if yf is None or not industry:
        return []
    try:
        ind = yf.Industry(_industry_key(industry))
        top = ind.top_companies
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("yf.Industry lookup failed for '%s': %s", industry, e)
        return []
    if top is None or getattr(top, "empty", True):
        return []

    out = []
    try:
        df = top.reset_index()
        sym_col = next((c for c in df.columns
                        if str(c).lower() in ("symbol", "index", "ticker")), None)
        name_col = next((c for c in df.columns if "name" in str(c).lower()), None)
        for _, row in df.head(limit).iterrows():
            sym = str(row[sym_col]).strip().upper() if sym_col else ""
            if not sym or sym == "NAN":
                continue
            out.append(PeerCandidate(ticker=sym,
                                     name=str(row[name_col]) if name_col else "",
                                     sources=["industry"], industry=industry))
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("parsing yf.Industry frame failed: %s", e)
    LOG.info("yf.Industry returned %d candidates for '%s'", len(out), industry)
    return out


# =========================================================================== #
# Source 4 -- SEC SIC peers (independent taxonomy, official)
# =========================================================================== #
def get_own_sic(ticker: str, user_agent: str) -> tuple:
    """Return (sic_code, sic_description) from the SEC submissions API."""
    from .fetch import SEC_SUBMISSIONS_URL, sec_lookup_cik
    cik = sec_lookup_cik(ticker, user_agent)
    if cik is None:
        return None, ""
    try:
        time.sleep(0.12)
        r = requests.get(SEC_SUBMISSIONS_URL.format(cik=cik), timeout=30,
                         headers={"User-Agent": user_agent,
                                  "Accept-Encoding": "gzip, deflate",
                                  "Host": "data.sec.gov"})
        r.raise_for_status()
        j = r.json()
        return (str(j.get("sic") or "").strip() or None,
                j.get("sicDescription") or "")
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("[%s] SIC lookup failed: %s", ticker, e)
        return None, ""


def _sic_candidates(sic: str, user_agent: str, limit: int = 60) -> list:
    """
    All filers sharing a 4-digit SIC, via one EDGAR browse request. Companies
    are returned as CIKs, mapped back to tickers through the SEC's own file --
    so a candidate only survives if it is a real listed issuer.
    """
    if not sic:
        return []
    from .fetch import sec_lookup_cik                          # warms the cache
    sec_lookup_cik("AAPL", user_agent)
    from .fetch import _SEC_TICKER_CACHE                       # noqa: PLC2701

    cik_to_ticker = {}
    if _SEC_TICKER_CACHE:
        for tk, cik in _SEC_TICKER_CACHE.items():
            cik_to_ticker.setdefault(int(cik), tk)
    if not cik_to_ticker:
        return []

    try:
        time.sleep(0.12)
        r = requests.get(SEC_SIC_BROWSE.format(sic=sic, count=min(limit, 100)),
                         timeout=30, headers={"User-Agent": user_agent})
        r.raise_for_status()
        ciks = re.findall(r"CIK=(\d{10})", r.text)
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("SEC SIC browse failed for %s: %s", sic, e)
        return []

    out, seen = [], set()
    for c in ciks:
        tk = cik_to_ticker.get(int(c))
        if tk and tk not in seen:
            seen.add(tk)
            out.append(PeerCandidate(ticker=tk, sources=["sic"], sic=sic))
    LOG.info("SEC SIC %s returned %d listed candidates", sic, len(out))
    return out


# =========================================================================== #
# Candidate merging and ranking
# =========================================================================== #
def _merge(*groups) -> dict:
    """Union candidates by ticker, accumulating which sources proposed each."""
    merged: dict = {}
    for grp in groups:
        for c in grp:
            if c.ticker in merged:
                m = merged[c.ticker]
                for s in c.sources:
                    if s not in m.sources:
                        m.sources.append(s)
                for fld in ("market_cap", "sector", "industry", "sic", "name",
                            "ev_ebitda", "gross_margin", "fwd_revenue_growth",
                            "quote_type", "currency"):
                    if not getattr(m, fld) and getattr(c, fld):
                        setattr(m, fld, getattr(c, fld))
            else:
                merged[c.ticker] = c
    return merged


def _similarity(c: PeerCandidate, own_cap: Optional[float], own_industry: str,
                own_sector: str, own_sic: Optional[str],
                size_weight: float) -> tuple:
    """
    Score 0-1. Combines size proximity, taxonomy agreement, and how many
    independent sources proposed the candidate.
    """
    bits = []

    # -- size proximity on a log scale: 2x away costs much less than 20x away
    if own_cap and c.market_cap and own_cap > 0 and c.market_cap > 0:
        dist = abs(math.log10(c.market_cap / own_cap))
        size = max(0.0, 1.0 - dist / 1.5)            # 0 at ~30x apart
        bits.append(f"size {size:.2f}(x{c.market_cap/own_cap:.1f})")
    else:
        size = 0.4                                   # unknown size: neutral-ish
        bits.append("size n/a")

    # -- taxonomy
    if own_industry and c.industry and c.industry.strip().lower() == own_industry.strip().lower():
        tax = 1.0
        bits.append("industry exact")
    elif own_sector and c.sector and c.sector.strip().lower() == own_sector.strip().lower():
        tax = 0.55
        bits.append("sector only")
    else:
        tax = 0.3
        bits.append("taxonomy weak")

    # -- SIC agreement (an independent taxonomy, so agreement is real evidence)
    if own_sic and c.sic:
        if c.sic == own_sic:
            sic = 1.0
            bits.append("SIC exact")
        elif c.sic[:3] == own_sic[:3]:
            sic = 0.7
            bits.append("SIC-3")
        elif c.sic[:2] == own_sic[:2]:
            sic = 0.4
            bits.append("SIC-2")
        else:
            sic = 0.1
            bits.append("SIC differs")
    else:
        sic = 0.5
        bits.append("SIC n/a")

    # -- corroboration across independent sources
    corr = min(1.0, 0.45 + 0.28 * len(set(c.sources)))
    bits.append(f"srcs {len(set(c.sources))}")

    tax_w = (1.0 - size_weight) * 0.45
    sic_w = (1.0 - size_weight) * 0.30
    cor_w = (1.0 - size_weight) * 0.25
    score = size * size_weight + tax * tax_w + sic * sic_w + corr * cor_w
    return round(score, 4), ", ".join(bits)


# =========================================================================== #
# Metric enrichment
# =========================================================================== #
def _enrich(c: PeerCandidate, user_agent: str) -> PeerCandidate:
    """Fill any comps metric the screener did not supply, from a Ticker fetch."""
    if (c.ev_ebitda is not None and c.gross_margin is not None
            and c.fwd_revenue_growth is not None and c.market_cap is not None):
        return c
    if yf is None:
        return c
    try:
        from .fetch import fetch_all
        from .metrics import peer_snapshot
        b = fetch_all(c.ticker, user_agent, use_sec=False, use_scrape_fallback=False)
        snap = peer_snapshot(b)
        info = b.info or {}
        if c.market_cap is None:
            c.market_cap = _num(info.get("marketCap"))
        if not c.industry:
            c.industry = info.get("industry") or ""
        if not c.sector:
            c.sector = info.get("sector") or ""
        if not c.quote_type:
            c.quote_type = (info.get("quoteType") or "").upper()
        if not c.currency:
            c.currency = (info.get("currency") or "").upper()
        if c.ev_ebitda is None:
            c.ev_ebitda = _num(snap.get("ev_ebitda"))
        if c.gross_margin is None:
            c.gross_margin = _num(snap.get("gross_margin"))
        if c.fwd_revenue_growth is None:
            c.fwd_revenue_growth = _num(snap.get("fwd_revenue_growth"))
    except Exception as e:                                     # noqa: BLE001
        LOG.debug("[%s] peer enrichment failed: %s", c.ticker, e)
    return c


# =========================================================================== #
# Gates
# =========================================================================== #
def _hard_gate(c: PeerCandidate, own_cap: Optional[float], size_band: float,
               own_ticker: str) -> Optional[str]:
    """Return a rejection reason, or None to accept."""
    if c.ticker.upper() == own_ticker.upper():
        return "is the subject company"
    if c.quote_type and c.quote_type not in ("EQUITY", ""):
        return f"not an operating equity (quoteType={c.quote_type})"
    if re.search(r"[-.](U|WS|WT|RT|PR[A-Z]?)$", c.ticker):
        return "warrant / unit / preferred line"
    if c.market_cap is not None and c.market_cap < 5e7:
        return f"market cap {_fmt_cap(c.market_cap)} below $50M floor"
    if own_cap and c.market_cap and own_cap > 0:
        ratio = c.market_cap / own_cap
        if ratio > size_band or ratio < 1.0 / size_band:
            return (f"market cap {_fmt_cap(c.market_cap)} is {ratio:.1f}x the "
                    f"subject (band 1/{size_band:.0f}x-{size_band:.0f}x)")
    usable = sum(1 for m in ("ev_ebitda", "gross_margin", "fwd_revenue_growth")
                 if _metric_ok(getattr(c, m), m))
    if usable == 0:
        return "no usable comps metric"
    return None


def _metric_ok(v: Optional[float], metric: str) -> bool:
    if v is None:
        return False
    lo, hi = METRIC_GATES[metric]
    return lo <= v <= hi and not math.isnan(v)


def _trim_outliers(values: list) -> tuple:
    """
    IQR trim. The median already resists outliers, but with n=4-6 a single
    absurd multiple still shifts it, so values beyond 1.5 IQR are dropped and
    reported rather than silently included.
    """
    vals = sorted(v for v in values if v is not None)
    if len(vals) < 5:
        return vals, []
    q1 = vals[len(vals) // 4]
    q3 = vals[(3 * len(vals)) // 4]
    iqr = q3 - q1
    if iqr <= 0:
        return vals, []
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    kept = [v for v in vals if lo <= v <= hi]
    dropped = [v for v in vals if not (lo <= v <= hi)]
    return kept, dropped


def _confidence(n: int, min_peers: int) -> str:
    if n >= max(6, min_peers + 2):
        return "high"
    if n >= max(4, min_peers):
        return "medium"
    if n >= 3:
        return "low"
    return "insufficient"


# =========================================================================== #
# Main entry point
# =========================================================================== #
def build_peer_set(ticker: str, bundle, archetype: str, universe: dict,
                   max_peers: int = 8, force_refresh: bool = False) -> PeerSet:
    """
    Construct the comps grid for one ticker. Manual peers short-circuit
    discovery; otherwise all automatic sources run and are ranked.
    """
    settings = universe.get("settings", {}) or {}
    user_agent = settings.get("sec_user_agent", "Research research@example.com")
    cfg = (universe.get("tickers") or {}).get(ticker.upper(), {}) or {}
    params = {**DEFAULT_PEER_PARAMS, **ARCHETYPE_PEER_PARAMS.get(archetype, {})}
    max_peers = int(settings.get("max_peers", max_peers))

    info = bundle.info or {}
    own_cap = _num(info.get("marketCap"))
    own_industry = info.get("industry") or ""
    own_sector = info.get("sector") or ""

    ps = PeerSet(ticker=ticker.upper(), archetype=archetype,
                 built_at=datetime.now().isoformat(timespec="seconds"),
                 own_industry=own_industry, own_sector=own_sector,
                 own_market_cap=own_cap)

    # ---------------- cache ----------------
    if not force_refresh:
        cached = load_cached_peers(ticker, settings.get("peer_cache_days", 90))
        if cached:
            LOG.info("[%s] using cached peer set (%d peers, built %s)", ticker,
                     len(cached.peers), cached.built_at[:10])
            return cached

    # ---------------- source 1: manual ----------------
    manual = [p.upper() for p in (cfg.get("peers") or [])
              if p.upper() != ticker.upper()]
    if manual:
        ps.source = "manual"
        ps.sources_used = ["manual"]
        LOG.info("[%s] manual peer set: %s", ticker, manual)
        cands = [PeerCandidate(ticker=t, sources=["manual"]) for t in manual]
        for c in cands:
            _enrich(c, user_agent)
            time.sleep(0.25)
        for c in cands:
            reason = _hard_gate(c, own_cap, params["size_band"] * 3, ticker)
            # Manual choices bypass the size band -- you chose them deliberately.
            if reason and "market cap" in reason and "band" in reason:
                reason = None
            if reason:
                ps.rejected.append((c.ticker, reason))
            else:
                c.similarity = 1.0
                c.score_detail = "manual selection"
                ps.peers.append(c)
        _finalise(ps, params)
        save_peers(ps)
        return ps

    # ---------------- sources 2-5: automatic ----------------
    ps.source = "auto"
    own_sic, sic_desc = get_own_sic(ticker, user_agent)
    ps.own_sic = own_sic
    if own_sic:
        LOG.info("[%s] SEC SIC %s (%s)", ticker, own_sic, sic_desc)

    screener = _screener_candidates(own_industry, own_sector, own_cap,
                                    params["size_band"])
    if screener:
        ps.sources_used.append("screener")

    industry_c = _industry_candidates(own_industry)
    if industry_c:
        ps.sources_used.append("industry")

    sic_c = _sic_candidates(own_sic, user_agent) if own_sic else []
    if sic_c:
        ps.sources_used.append("sic")

    merged = _merge(screener, industry_c, sic_c)

    # Last resort: widen to the sector. Always flagged, never silent.
    if len(merged) < params["min_peers"] + 2 and own_sector:
        LOG.info("[%s] thin industry candidates -- widening to sector", ticker)
        sector_c = _screener_candidates("", own_sector, own_cap,
                                        params["size_band"], limit=40)
        if not sector_c and yf is not None:
            try:
                q = yf.EquityQuery("and", [
                    yf.EquityQuery("eq", ["sector", own_sector]),
                    yf.EquityQuery("gt", ["intradaymarketcap",
                                          max(5e7, (own_cap or 1e9) / params["size_band"])]),
                    yf.EquityQuery("lt", ["intradaymarketcap",
                                          (own_cap or 1e9) * params["size_band"]]),
                ])
                sector_c = []
                for qd in _extract_quotes(yf.screen(q, size=40,
                                                    sortField="intradaymarketcap",
                                                    sortAsc=False)):
                    sym = (qd.get("symbol") or "").upper()
                    if sym:
                        sector_c.append(PeerCandidate(
                            ticker=sym, sources=["sector"],
                            market_cap=_num(qd.get("marketCap")),
                            sector=qd.get("sector") or own_sector,
                            industry=qd.get("industry") or ""))
            except Exception as e:                             # noqa: BLE001
                LOG.debug("sector fallback failed: %s", e)
                sector_c = []
        if sector_c:
            ps.sources_used.append("sector")
            ps.warnings.append("industry candidates were thin; sector-level peers "
                               "included -- treat peer-relative sub-metrics as weak")
            merged = _merge(list(merged.values()), sector_c)

    if not merged:
        ps.warnings.append("no peer candidates found from any source -- the three "
                           "peer-relative sub-metrics will record data missing")
        _finalise(ps, params)
        save_peers(ps)
        return ps

    # ---------------- rank before enriching (enrichment costs a request each) --
    for c in merged.values():
        c.similarity, c.score_detail = _similarity(
            c, own_cap, own_industry, own_sector, own_sic, params["size_weight"])

    ranked = sorted(merged.values(), key=lambda c: -c.similarity)
    probe_limit = min(len(ranked), max_peers * 3)
    LOG.info("[%s] %d candidates; enriching top %d", ticker, len(ranked), probe_limit)

    accepted = []
    probed = []
    for c in ranked[:probe_limit]:
        _enrich(c, user_agent)
        # Re-score: enrichment usually fills market cap and industry.
        c.similarity, c.score_detail = _similarity(
            c, own_cap, own_industry, own_sector, own_sic, params["size_weight"])
        probed.append(c)
        time.sleep(0.25)

    # ---- adaptive size band -------------------------------------------------
    # Real industries are not uniformly sized: a $1.4B name may sit between a
    # $350M and a $21B peer. A fixed band rejects the large neighbours and
    # leaves too few valid values, so the band widens until enough peers
    # survive. Enrichment is already paid for, so retrying costs nothing but
    # the widening is always recorded -- a wider band is weaker evidence.
    band = params["size_band"]
    band_used = band
    for attempt in range(4):
        accepted, rejected = [], []
        for c in probed:
            reason = _hard_gate(c, own_cap, band, ticker)
            (rejected if reason else accepted).append((c, reason))
        accepted = [c for c, _ in accepted]

        # Enough peers, and enough of them carry each APPLICABLE metric?
        # EV/EBITDA has to be in this check -- it is the scarcest of the three
        # (any peer with negative EBITDA drops out), so excluding it lets a set
        # that is short on exactly the metric we need pass as adequate.
        required = ["gross_margin", "fwd_revenue_growth"]
        if archetype not in EV_EBITDA_NA_ARCHETYPES:
            required.append("ev_ebitda")
        scarcest = min(
            (sum(1 for c in accepted if _metric_ok(getattr(c, m), m))
             for m in required),
            default=0)
        if len(accepted) >= params["min_peers"] and scarcest >= 3:
            band_used = band
            break
        if attempt == 3:
            band_used = band
            break
        band *= 2.0
        LOG.info("[%s] %d peers / scarcest metric n=%d at %.0fx band -- widening "
                 "to %.0fx", ticker, len(accepted), scarcest, band / 2.0, band)

    ps.rejected = [(c.ticker, r) for c, r in rejected]
    if band_used > params["size_band"]:
        ps.warnings.append(
            f"size band widened from {params['size_band']:.0f}x to "
            f"{band_used:.0f}x to reach {params['min_peers']} peers -- the set "
            "spans a wider size range than ideal, so peer-relative sub-metrics "
            "are weaker evidence")

    for c in ranked[probe_limit:]:
        ps.rejected.append((c.ticker, "outside the top-ranked candidates probed"))

    ps.peers = sorted(accepted, key=lambda c: -c.similarity)[:max_peers]
    _finalise(ps, params)
    save_peers(ps)
    return ps


def _finalise(ps: PeerSet, params: dict) -> None:
    """Count usable peers per metric and assign per-metric confidence."""
    min_peers = params["min_peers"]
    for metric in ("ev_ebitda", "gross_margin", "fwd_revenue_growth"):
        vals = [getattr(p, metric) for p in ps.peers]
        usable = [v for v in vals if _metric_ok(v, metric)]
        ps.metric_counts[metric] = len(usable)
        ps.confidence[metric] = _confidence(len(usable), min_peers)
        if len(usable) < 3 and ps.peers:
            ps.warnings.append(
                f"{metric}: only {len(usable)} peer(s) have a valid value -- "
                "sub-metric will record data missing")

    if ps.peers and len(ps.peers) < min_peers:
        ps.warnings.append(
            f"only {len(ps.peers)} peers accepted (archetype {ps.archetype} "
            f"wants {min_peers}) -- peer-relative sub-metrics are weak evidence")

    if ps.archetype in EV_EBITDA_NA_ARCHETYPES:
        ps.confidence["ev_ebitda"] = "not applicable"
        ps.warnings.append(
            f"archetype {ps.archetype}: EV/EBITDA is not a meaningful multiple "
            "(negative EBITDA or no enterprise value) -- sub-metric suppressed")


# =========================================================================== #
# Applying the grid to a MetricSet
# =========================================================================== #
def apply_peer_set(ms, own_snapshot: dict, ps: PeerSet, min_peers: int = 3) -> None:
    """
    Write the three peer-relative metrics. Each is evaluated independently: a
    metric with too few valid peers stays missing while the others still score.
    """
    from .util import M, percentile_rank

    for w in ps.warnings:
        ms.warn(f"peers: {w}")

    # ---- TEV/EBITDA vs peer median
    if ps.archetype in EV_EBITDA_NA_ARCHETYPES:
        ms.warn(f"peers: EV/EBITDA suppressed for archetype {ps.archetype}")
    else:
        vals = [p.ev_ebitda for p in ps.peers if _metric_ok(p.ev_ebitda, "ev_ebitda")]
        kept, dropped = _trim_outliers(vals)
        own_ev = own_snapshot.get("ev_ebitda")
        own_valid = _metric_ok(own_ev, "ev_ebitda")

        if not own_valid:
            # The subject has no coherent multiple of its own -- almost always
            # negative EBITDA. Nothing to compare, and the peer count is not
            # the problem, so say so plainly.
            ms.warn("peers: TEV/EBITDA not comparable -- the subject has no valid "
                    f"EV/EBITDA (own={own_ev if own_ev is not None else 'n/a'}); "
                    f"{len(kept)} peer value(s) were available but unused")
        elif len(kept) < min_peers:
            ms.warn(f"peers: TEV/EBITDA needs {min_peers} valid peers, has "
                    f"{len(kept)} -- sub-metric excluded")
        else:
            pm = median(kept)
            contributors = [p.ticker for p in ps.peers
                            if _metric_ok(p.ev_ebitda, "ev_ebitda")]
            note = (f"peer median {pm:.1f}x vs own {own_ev:.1f}x, n={len(kept)}"
                    + (f" ({len(dropped)} outlier(s) trimmed)" if dropped else "")
                    + f" [{', '.join(contributors)}]")
            ms.set("tev_ebitda_discount_vs_peers",
                   M((pm - own_ev) / pm, f"comps({ps.source})", "LTM", "Derived", note))

    # ---- gross margin percentile
    vals = [p.gross_margin for p in ps.peers if _metric_ok(p.gross_margin, "gross_margin")]
    own_gm = own_snapshot.get("gross_margin")
    if own_gm is None:
        ms.warn("peers: gross-margin percentile skipped -- the subject's own "
                "gross margin could not be sourced")
    elif len(vals) < min_peers:
        ms.warn(f"peers: gross-margin percentile needs {min_peers} valid peers, "
                f"has {len(vals)} -- sub-metric excluded")
    else:
        pct = percentile_rank(own_gm, vals)
        if pct is not None:
            ms.set("gm_percentile_vs_peers",
                   M(pct, f"comps({ps.source})", "LTM", "Derived",
                     f"own GM {own_gm:.1%} ranks at {pct:.0%} of {len(vals)} peers "
                     f"(peer median {median(vals):.1%})"))

    # ---- peer median forward growth
    vals = [p.fwd_revenue_growth for p in ps.peers
            if _metric_ok(p.fwd_revenue_growth, "fwd_revenue_growth")]
    kept, dropped = _trim_outliers(vals)
    if len(kept) >= min_peers:
        pm = median(kept)
        ms.set("peer_median_fwd_growth",
               M(pm, f"comps({ps.source})", "FY+1", "Estimate",
                 f"median of {len(kept)} peers"
                 + (f", {len(dropped)} outlier(s) trimmed" if dropped else "")))
    else:
        ms.warn(f"peers: peer-median growth needs {min_peers} valid peers, "
                f"has {len(kept)} -- sub-metric excluded")


# =========================================================================== #
# Cache + reviewable export
# =========================================================================== #
def peer_cache_path(ticker: str) -> str:
    return os.path.join(PEER_DIR, f"{ticker.upper()}.json")


def save_peers(ps: PeerSet) -> None:
    with open(peer_cache_path(ps.ticker), "w", encoding="utf-8") as f:
        json.dump(ps.to_dict(), f, indent=2, default=str)


def load_cached_peers(ticker: str, max_age_days: int = 90) -> Optional[PeerSet]:
    path = peer_cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        when = parse_date((d.get("built_at") or "")[:10])
        if when and (datetime.now().date() - when).days > max_age_days:
            return None
        ps = PeerSet(ticker=d["ticker"], archetype=d.get("archetype", "B"),
                     source=d.get("source", "auto"), built_at=d.get("built_at", ""),
                     own_industry=d.get("own_industry", ""),
                     own_sector=d.get("own_sector", ""),
                     own_sic=d.get("own_sic"),
                     own_market_cap=d.get("own_market_cap"),
                     rejected=[tuple(r) for r in d.get("rejected", [])],
                     metric_counts=d.get("metric_counts", {}),
                     confidence=d.get("confidence", {}),
                     warnings=d.get("warnings", []),
                     sources_used=d.get("sources_used", []))
        ps.peers = [PeerCandidate(**p) for p in d.get("peers", [])]
        return ps
    except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
        LOG.warning("[%s] peer cache unreadable (%s) -- rebuilding", ticker, e)
        return None


def export_peers_yaml(path: Optional[str] = None) -> str:
    """
    Dump every discovered peer set to a reviewable YAML. Read it, correct it,
    and paste anything you disagree with into universe.yaml as a manual set --
    manual always wins and never expires.
    """
    from .util import CONFIG_DIR
    path = path or os.path.join(CONFIG_DIR, "peers_auto.yaml")
    lines = [
        "# AUTO-DISCOVERED PEER SETS -- review and correct.",
        "# Move any set you want to freeze into universe.yaml under `peers:`;",
        f"# manual sets override discovery and never expire.",
        f"# generated {datetime.now():%Y-%m-%d %H:%M}",
        "",
    ]
    for fn in sorted(os.listdir(PEER_DIR)):
        if not fn.endswith(".json"):
            continue
        ps = load_cached_peers(fn[:-5], max_age_days=100000)
        if not ps:
            continue
        lines.append(f"{ps.ticker}:")
        lines.append(f"  # {ps.own_industry} | SIC {ps.own_sic or 'n/a'} | "
                     f"{_fmt_cap(ps.own_market_cap)} | source: {ps.source}")
        for m, n in ps.metric_counts.items():
            lines.append(f"  # {m}: n={n} ({ps.confidence.get(m, 'n/a')})")
        lines.append(f"  peers: [{', '.join(ps.tickers)}]")
        for p in ps.peers:
            lines.append(f"  #   {p.ticker:<7} sim {p.similarity:.2f}  "
                         f"{_fmt_cap(p.market_cap):>8}  {p.score_detail}")
        for w in ps.warnings:
            lines.append(f"  # WARNING: {w}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    LOG.info("peer sets exported for review -> %s", path)
    return path
