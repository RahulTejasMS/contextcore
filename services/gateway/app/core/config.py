# ============================================================
# config.py — Loads all environment variables into a typed
# Settings object. Every service has one of these.
# ============================================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "contextcore"
    postgres_user: str = "contextcore_user"
    postgres_password: str = "contextcore_pass"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    # JWT
    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Service
    gateway_port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


# Single instance used everywhere — import this, not Settings()
settings = Settings()