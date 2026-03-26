from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./stablecoin_payments.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    WEBHOOK_SECRET: str = "whsec_test_secret"
    PLATFORM_FEE_BPS: int = 200  # 2% fee in basis points

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
