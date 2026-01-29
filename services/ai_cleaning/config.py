"""AI清洗服务 - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Cleaning Rule Service"
    APP_PORT: int = 8012
    DEBUG: bool = False

    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    SEATUNNEL_API_URL: str = "http://localhost:5801"

    model_config = {"env_prefix": "AI_CLEAN_"}


settings = Settings()
