"""数据资产API网关 - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """数据资产 API 网关配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "Data Asset API Gateway"
    APP_PORT: int = 8014

    # Data API 特有配置
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 300  # 5分钟
    MAX_RESULTS: int = 10000

    model_config = {"env_prefix": "DATA_API_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
