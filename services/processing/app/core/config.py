from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "contextcore"
    postgres_user: str = "contextcore_user"
    postgres_password: str = "contextcore_pass"

    kafka_bootstrap_servers: str = "kafka:9092"

    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "contextcore-documents"

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    # Embedding model — runs locally, no API key needed
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Chunking settings
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()