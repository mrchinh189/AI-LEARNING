"""Cấu hình đọc từ biến môi trường."""
import os
from dataclasses import dataclass, field


def _ids(raw: str) -> set[int]:
    return {int(x) for x in raw.split(",") if x.strip()}


@dataclass(frozen=True)
class Settings:
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    allowed_user_ids: set[int] = field(default_factory=lambda: _ids(os.getenv("ALLOWED_USER_IDS", "")))
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    model_strong: str = os.getenv("MODEL_STRONG", "")
    model_fast: str = os.getenv("MODEL_FAST", "")
    daily_budget_usd: float = float(os.getenv("DAILY_BUDGET_USD", "10"))
    heartbeat_minutes: int = int(os.getenv("HEARTBEAT_MINUTES", "15"))
    max_task_attempts: int = int(os.getenv("MAX_TASK_ATTEMPTS", "3"))


settings = Settings()
