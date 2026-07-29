from datetime import datetime
from zoneinfo import ZoneInfo

from .config import settings


def dashboard_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.dashboard_timezone))
    except Exception:
        return datetime.now().astimezone()


def dashboard_today():
    return dashboard_now().date()
