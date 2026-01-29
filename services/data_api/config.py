"""数据资产API - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Data Asset API Gateway"
    APP_PORT: int = 8014
    DEBUG: bool = False

    DATAHUB_GMS_URL: str = "http://localhost:8081"
    DATAHUB_TOKEN: str = os.environ.get("DATAHUB_TOKEN", "")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = {"env_prefix": "DATA_API_"}


settings = Settings()
