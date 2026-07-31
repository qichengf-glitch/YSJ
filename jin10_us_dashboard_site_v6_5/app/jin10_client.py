from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from .config import settings


class Jin10ClientError(RuntimeError):
    pass


class Jin10Client:
    def __init__(self, secret_key: Optional[str] = None, base_url: Optional[str] = None):
        self.secret_key = (secret_key or settings.jin10_secret_key).strip()
        self.base_url = (base_url or settings.jin10_base_url).rstrip("/")
        if not self.secret_key:
            raise Jin10ClientError("Missing JIN10_SECRET_KEY in .env")

    @property
    def headers(self) -> Dict[str, str]:
        return {"secret-key": self.secret_key}

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.base_url + path
        resp = requests.get(url, headers=self.headers, params=params or {}, timeout=25)
        try:
            payload = resp.json()
        except Exception as exc:
            raise Jin10ClientError(f"Non-JSON response from {url}: {resp.status_code} {resp.text[:300]}") from exc
        if resp.status_code != 200 or payload.get("status") not in (200, None):
            raise Jin10ClientError(f"Jin10 error {resp.status_code}: {payload}")
        return payload

    def fetch_calendar_data(self, category: str, start: str, end: str) -> List[Dict[str, Any]]:
        return self.get("/calendar/data", {"category": category, "date": start, "end_date": end}).get("data", []) or []

    def fetch_calendar_event(self, category: str, start: str, end: str) -> List[Dict[str, Any]]:
        return self.get("/calendar/event", {"category": category, "date": start, "end_date": end}).get("data", []) or []

    def fetch_calendar_holiday(self, category: str, start: str, end: str) -> List[Dict[str, Any]]:
        return self.get("/calendar/holiday", {"category": category, "date": start, "end_date": end}).get("data", []) or []

    def fetch_log(self, source_type: str, category: str, last_log_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"category": category}
        if last_log_id is not None:
            params["last_log_id"] = last_log_id
        return self.get(f"/calendar/{source_type}/log", params).get("data", []) or []


def split_date_windows(start: date, end: date, max_days: int = 7) -> Iterable[Tuple[str, str]]:
    cur = start
    while cur <= end:
        window_end = min(cur + timedelta(days=max_days - 1), end)
        yield cur.isoformat(), window_end.isoformat()
        cur = window_end + timedelta(days=1)
