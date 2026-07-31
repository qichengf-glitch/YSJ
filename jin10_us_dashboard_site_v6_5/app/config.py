import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    jin10_secret_key: str = os.getenv("JIN10_SECRET_KEY", "").strip()
    jin10_base_url: str = os.getenv("JIN10_BASE_URL", "https://open-data-api.jin10.com/data-api").rstrip("/")
    database_path: str = os.getenv("DATABASE_PATH", "./data/us_dashboard.db")
    sync_past_days: int = int(os.getenv("SYNC_PAST_DAYS", "7"))
    sync_future_days: int = int(os.getenv("SYNC_FUTURE_DAYS", "30"))
    log_poll_interval_minutes: int = int(os.getenv("LOG_POLL_INTERVAL_MINUTES", "3"))
    full_sync_interval_minutes: int = int(os.getenv("FULL_SYNC_INTERVAL_MINUTES", "180"))
    enable_scheduler: bool = _bool(os.getenv("ENABLE_SCHEDULER"), True)
    price_provider: str = os.getenv("PRICE_PROVIDER", "yfinance").strip()
    price_cache_minutes: int = int(os.getenv("PRICE_CACHE_MINUTES", "5"))
    prediction_sync_interval_minutes: int = int(os.getenv("PREDICTION_SYNC_INTERVAL_MINUTES", "10"))
    prediction_sync_max_pages: int = int(os.getenv("PREDICTION_SYNC_MAX_PAGES", "15"))
    prediction_sync_min_prob: float = float(os.getenv("PREDICTION_SYNC_MIN_PROB", "0.10"))
    prediction_sync_min_volume: float = float(os.getenv("PREDICTION_SYNC_MIN_VOLUME", "10000"))


settings = Settings()
