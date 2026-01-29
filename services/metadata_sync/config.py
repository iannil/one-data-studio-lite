"""元数据联动ETL - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Metadata Sync Service"
    APP_PORT: int = 8013
    DEBUG: bool = False

    DATAHUB_GMS_URL: str = "http://localhost:8081"
    DATAHUB_TOKEN: str = os.environ.get("DATAHUB_TOKEN", "")
    SEATUNNEL_API_URL: str = "http://localhost:5801"
    DOLPHINSCHEDULER_API_URL: str = "http://localhost:12345/dolphinscheduler"
    DOLPHINSCHEDULER_TOKEN: str = os.environ.get("DOLPHINSCHEDULER_TOKEN", "")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    model_config = {"env_prefix": "META_SYNC_"}


settings = Settings()
