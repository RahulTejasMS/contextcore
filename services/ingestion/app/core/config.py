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

    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    ingestion_port: int = 8001

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()