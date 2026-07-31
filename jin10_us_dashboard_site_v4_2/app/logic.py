import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(v, fmt)
            if "T" in v or fmt == "%Y-%m-%dT%H:%M:%S.%fZ":
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        s = str(value).strip().replace(",", "")
        # Remove common percent sign but keep numeric value as written.
        s = s.replace("%", "")
        return float(s)
    except Exception:
        return None


def pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / abs(denominator) * 100


def parse_company_name_and_ticker(name: Optional[str]) -> Tuple[str, str]:
    if not name:
        return "", ""
    text = str(name).strip()
    m = re.search(r"^(.*?)\(([^()]+)\)\s*$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip().upper()
    return text, ""


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


GROUPS = {
    "大型科技": {"AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "NFLX"},
    "中概股": {"BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "BILI", "TME", "NTES", "TCOM", "YUMC", "BEKE", "FUTU", "ZTO", "IQ"},
    "半导体": {"NVDA", "AMD", "INTC", "TSM", "ASML", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "ARM", "MRVL", "ON"},
    "金融": {"JPM", "BAC", "GS", "MS", "C", "WFC", "BLK", "AXP", "V", "MA", "COF"},
    "消费": {"WMT", "COST", "MCD", "SBUX", "NKE", "HD", "LOW", "TGT", "PG", "KO", "PEP"},
    "医疗": {"LLY", "UNH", "PFE", "MRK", "JNJ", "ILMN", "ABBV", "AMGN", "GILD", "TMO"},
    "能源": {"XOM", "CVX", "COP", "SLB", "OXY"},
}


def ticker_root(ticker: str) -> str:
    t = normalize_ticker(ticker)
    return t.split(".")[0] if t else ""


def company_groups(ticker: str) -> List[str]:
    root = ticker_root(ticker)
    hits = [name for name, symbols in GROUPS.items() if root in symbols]
    return hits or ["其他"]


def metric_status(actual: Any, consensus: Any = None) -> str:
    if actual is None or str(actual).strip() == "":
        return "unreleased"
    if safe_float(actual) is not None and safe_float(consensus) is not None:
        return "comparable"
    return "released"


def compute_metric_analysis(item: Dict[str, Any]) -> Dict[str, Any]:
    actual = safe_float(item.get("actual"))
    consensus = safe_float(item.get("consensus"))
    previous = safe_float(item.get("previous"))
    surprise_abs = None if actual is None or consensus is None else actual - consensus
    change_abs = None if actual is None or previous is None else actual - previous
    return {
        "surprise_abs": surprise_abs,
        "surprise_pct": pct(surprise_abs, consensus),
        "change_abs": change_abs,
        "change_pct": pct(change_abs, previous),
        "status": metric_status(item.get("actual"), item.get("consensus")),
    }


def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def serialize_raw(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
