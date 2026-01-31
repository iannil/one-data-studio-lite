"""元数据联动ETL - 配置"""

import os

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    APP_NAME: str = "Metadata Sync Service"
    APP_PORT: int = 8013
    DEBUG: bool = False

    # DataHub 配置
    DATAHUB_GMS_URL: str = "http://localhost:8081"
    DATAHUB_TOKEN: str = os.environ.get("DATAHUB_TOKEN", "")

    # DataHub Webhook 签名密钥
    DATAHUB_WEBHOOK_SECRET: str = os.environ.get("DATAHUB_WEBHOOK_SECRET", "")

    # ETL 引擎配置
    SEATUNNEL_API_URL: str = "http://localhost:5801"
    DOLPHINSCHEDULER_API_URL: str = "http://localhost:12345/dolphinscheduler"
    DOLPHINSCHEDULER_TOKEN: str = os.environ.get("DOLPHINSCHEDULER_TOKEN", "")
    HOP_API_URL: str = "http://localhost:8083"

    model_config = {"env_prefix": "META_SYNC_"}


settings = Settings()
