"""NL2SQL 服务 - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NL2SQL Service"
    APP_PORT: int = 8011
    DEBUG: bool = False

    # LLM 配置 (Cube-Studio 部署的 Ollama)
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # 数据库连接 - 生产环境必须通过环境变量设置
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # Superset 连接
    SUPERSET_URL: str = "http://localhost:8088"

    model_config = {"env_prefix": "NL2SQL_"}


settings = Settings()
