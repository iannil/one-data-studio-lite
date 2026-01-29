"""敏感数据检测 - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Sensitive Data Detection Service"
    APP_PORT: int = 8015
    DEBUG: bool = False

    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    SHARDINGSPHERE_URL: str = "http://localhost:3307"

    model_config = {"env_prefix": "SENSITIVE_"}


settings = Settings()
