"""审计日志 - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Audit Log Service"
    APP_PORT: int = 8016
    DEBUG: bool = False

    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    LOG_RETENTION_DAYS: int = int(os.environ.get("AUDIT_LOG_RETENTION_DAYS", "90"))

    model_config = {"env_prefix": "AUDIT_"}


settings = Settings()
