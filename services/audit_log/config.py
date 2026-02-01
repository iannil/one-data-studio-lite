"""审计日志服务 - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """审计日志服务配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "Audit Log Service"
    APP_PORT: int = 8016

    # Audit Log 特有配置
    LOG_RETENTION_DAYS: int = 90
    ENABLE_ASYNC_WRITING: bool = True
    BATCH_SIZE: int = 100

    model_config = {"env_prefix": "AUDIT_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
