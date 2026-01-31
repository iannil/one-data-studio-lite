"""元数据联动ETL - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Metadata Sync Service"
    APP_PORT: int = 8013
    DEBUG: bool = False

    # 环境标识
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # DataHub 配置
    DATAHUB_GMS_URL: str = "http://localhost:8081"
    DATAHUB_TOKEN: str = os.environ.get("DATAHUB_TOKEN", "")

    # DataHub Webhook 签名密钥
    # 生产环境必须配置，用于验证 Webhook 请求来源
    # 需要在 DataHub 中配置相同的密钥
    DATAHUB_WEBHOOK_SECRET: str = os.environ.get("DATAHUB_WEBHOOK_SECRET", "")

    # ETL 引擎配置
    SEATUNNEL_API_URL: str = "http://localhost:5801"
    DOLPHINSCHEDULER_API_URL: str = "http://localhost:12345/dolphinscheduler"
    DOLPHINSCHEDULER_TOKEN: str = os.environ.get("DOLPHINSCHEDULER_TOKEN", "")
    HOP_API_URL: str = "http://localhost:8083"

    # 数据库配置
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    model_config = {"env_prefix": "META_SYNC_"}

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def is_development(self) -> bool:
        """是否为开发环境"""
        return not self.is_production()


settings = Settings()
