"""敏感数据检测服务 - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """敏感数据检测服务配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "Sensitive Data Detection Service"
    APP_PORT: int = 8015

    # Sensitive Detect 特有配置
    CONFIDENCE_THRESHOLD: float = 0.7
    ENABLE_LLM_ANALYSIS: bool = True

    model_config = {"env_prefix": "SENSITIVE_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
