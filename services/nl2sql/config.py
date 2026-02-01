"""NL2SQL 服务 - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """NL2SQL 服务配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "NL2SQL Service"
    APP_PORT: int = 8011

    # NL2SQL 特有配置
    DEFAULT_DATABASE: str = "default"
    MAX_ROWS: int = 1000
    ENABLE_QUERY_CACHE: bool = True

    model_config = {"env_prefix": "NL2SQL_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
