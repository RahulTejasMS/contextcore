from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "contextcore"
    postgres_user: str = "contextcore_user"
    postgres_password: str = "contextcore_pass"

    redis_host: str = "redis"
    redis_port: int = 6379

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    openai_api_key: str = ""

    # ── NEW: NVIDIA settings ──────────────────────────────
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_model: str = "meta/llama-3.1-8b-instruct"
    # ─────────────────────────────────────────────────────

    query_port: int = 8002
    retrieval_top_k: int = 5
    cache_ttl_seconds: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()