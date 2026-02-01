"""AI清洗规则推荐服务 - 配置

使用统一的 ServiceConfig 基类，减少重复配置。
"""

from services.common.base_config import ServiceConfig


class Settings(ServiceConfig):
    """AI 清洗服务配置

    服务端口和特定配置在此定义，通用配置继承自 ServiceConfig。
    """
    APP_NAME: str = "AI Cleaning Rule Service"
    APP_PORT: int = 8012

    # AI Cleaning 特有配置
    ENABLE_RULE_CACHE: bool = True
    MAX_SUGGESTIONS: int = 10
    CONFIDENCE_THRESHOLD: float = 0.7

    model_config = {"env_prefix": "AI_CLEAN_", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
