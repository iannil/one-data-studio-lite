"""元数据联动ETL - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """元数据同步服务配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "Metadata Sync Service"
    APP_PORT: int = 8013

    # Metadata Sync 特有配置
    WEBHOOK_SECRET: str = ""  # 由环境变量 META_SYNC_DATAHUB_WEBHOOK_SECRET 覆盖
    ENABLE_AUTO_SYNC: bool = True
    SYNC_BATCH_SIZE: int = 100

    model_config = {"env_prefix": "META_SYNC_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
