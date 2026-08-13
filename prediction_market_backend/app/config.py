import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_path: str = (
        os.getenv("PREDICTION_MARKET_DB")
        or os.getenv("DATABASE_PATH")
        or "./data/prediction_market.db"
    )
    enable_scheduler: bool = _bool(os.getenv("PREDICTION_MARKET_ENABLE_SCHEDULER"), True)
    prediction_sync_interval_minutes: int = int(
        os.getenv("PREDICTION_SYNC_INTERVAL_MINUTES", "10")
    )
    prediction_sync_max_pages: int = int(os.getenv("PREDICTION_SYNC_MAX_PAGES", "15"))
    prediction_sync_min_prob: float = float(os.getenv("PREDICTION_SYNC_MIN_PROB", "0.10"))
    prediction_sync_min_volume: float = float(
        os.getenv("PREDICTION_SYNC_MIN_VOLUME", "10000")
    )


settings = Settings()
