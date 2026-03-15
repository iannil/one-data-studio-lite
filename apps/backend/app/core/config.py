from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Smart Data Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_data"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "smart-data"
    MINIO_SECURE: bool = False

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Superset
    SUPERSET_URL: str = "http://localhost:8088"
    SUPERSET_USERNAME: str = "admin"
    SUPERSET_PASSWORD: str = "admin"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@smartdata.local"
    SMTP_USE_TLS: bool = True

    # Label Studio
    LABEL_STUDIO_URL: str = "http://localhost:8080"
    LABEL_STUDIO_SHARED_SECRET: str = "change-this-in-production"
    LABEL_STUDIO_HOST: str = "annotation.one-data-studio.local"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_S3_ENDPOINT_URL: str = "http://localhost:9000"

    # LLM
    LLM_INFERENCE_URL: str = "http://localhost:8000"
    LLM_API_KEY: str = ""
    LLM_DEFAULT_MODEL: str = "gpt-4-turbo-preview"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7

    # Vector Database
    VECTOR_DB_TYPE: str = "chromadb"  # chromadb, faiss, pgvector, memory
    VECTOR_DB_HOST: str = "localhost"
    VECTOR_DB_PORT: int = 8000
    VECTOR_DB_INDEX: str = "default"
    CHROMADB_PERSIST_DIR: str = "./data/chromadb"

    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_PROVIDER: str = "openai"  # openai, cohere, huggingface, bge

    # Knowledge Base
    KNOWLEDGE_CHUNK_SIZE: int = 1000
    KNOWLEDGE_CHUNK_OVERLAP: int = 200
    KNOWLEDGE_TOP_K: int = 5

    # Serverless
    SERVERLESS_RUNTIME: str = "python"
    SERVERLESS_TIMEOUT: int = 300
    SERVERLESS_MEMORY: int = 512

    # Edge Computing
    EDGE_REGISTRY_URL: str = "http://localhost:9000"
    EDGE_HEARTBEAT_INTERVAL: int = 30

    # Storage
    STORAGE_DEFAULT_BACKEND: str = "minio"
    STORAGE_S3_ENDPOINT: str = "http://localhost:9000"
    STORAGE_S3_ACCESS_KEY: str = "minioadmin"
    STORAGE_S3_SECRET_KEY: str = "minioadmin"
    STORAGE_S3_BUCKET: str = "smart-data"
    STORAGE_OSS_ENDPOINT: str = ""
    STORAGE_NFS_ROOT: str = "/data/nfs"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
