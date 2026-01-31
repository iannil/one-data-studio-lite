"""配置基类

提供统一的配置管理基类，减少各服务配置代码重复。
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:
    PYDANTIC_SETTINGS_AVAILABLE = False
    # 创建一个简单的替代类
    from pydantic import BaseModel
    BaseSettings = BaseModel


class BaseServiceConfig(BaseSettings):
    """微服务配置基类

    提供通用配置项和环境变量加载逻辑。
    所有服务配置应继承此基类以保持一致性。
    """

    # ============================================================
    # 服务基础配置
    # ============================================================
    APP_NAME: str = "ONE-DATA-STUDIO-LITE Service"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # 环境标识
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # ============================================================
    # JWT 配置
    # ============================================================
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-only-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))
    JWT_REFRESH_THRESHOLD_MINUTES: int = int(os.environ.get("JWT_REFRESH_THRESHOLD_MINUTES", "30"))

    # ============================================================
    # 数据库配置
    # ============================================================
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # ============================================================
    # Redis 配置
    # ============================================================
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_BLACKLIST_DB: int = int(os.environ.get("REDIS_BLACKLIST_DB", "0"))

    # ============================================================
    # 服务间通信
    # ============================================================
    SERVICE_SECRET: str = os.environ.get(
        "SERVICE_SECRET",
        "internal-service-secret-dev-do-not-use-in-prod"
    )
    INTERNAL_TOKEN: str = os.environ.get("INTERNAL_TOKEN", "")

    # ============================================================
    # LLM 配置
    # ============================================================
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")

    # ============================================================
    # 配置中心
    # ============================================================
    ETCD_ENDPOINTS: str = os.environ.get("ETCD_ENDPOINTS", "http://localhost:2379")
    ENABLE_CONFIG_CENTER: bool = (
        os.environ.get("ENABLE_CONFIG_CENTER", "true").lower() == "true"
    )
    CONFIG_CACHE_TTL: int = int(os.environ.get("CONFIG_CACHE_TTL", "60"))
    CONFIG_ENCRYPTION_KEY: str = os.environ.get("CONFIG_ENCRYPTION_KEY", "")

    # ============================================================
    # 监控追踪
    # ============================================================
    ENABLE_METRICS: bool = (
        os.environ.get("ENABLE_METRICS", "true").lower() == "true"
    )
    ENABLE_TRACING: bool = (
        os.environ.get("ENABLE_TRACING", "true").lower() == "true"
    )

    # ============================================================
    # 日志配置
    # ============================================================
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # ============================================================
    # 子系统地址（常用）
    # ============================================================
    PORTAL_URL: str = os.environ.get("PORTAL_URL", "http://localhost:8010")
    DATAHUB_URL: str = os.environ.get("DATAHUB_URL", "http://localhost:9002")
    DATAHUB_GMS_URL: str = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8081")
    DATAHUB_TOKEN: str = os.environ.get("DATAHUB_TOKEN", "")
    SUPERSET_URL: str = os.environ.get("SUPERSET_URL", "http://localhost:8088")
    DOLPHINSCHEDULER_URL: str = os.environ.get("DOLPHINSCHEDULER_URL", "http://localhost:12345")
    DOLPHINSCHEDULER_TOKEN: str = os.environ.get("DOLPHINSCHEDULER_TOKEN", "")

    model_config = {"env_prefix": "", "case_sensitive": False, "extra": "ignore"}

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT.lower() in ("development", "dev")

    def is_test(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT.lower() in ("test", "testing")

    def get_log_level(self) -> str:
        """获取日志级别"""
        level_map = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
        }
        return level_map.get(self.LOG_LEVEL.upper(), "INFO")

    def validate_security(self) -> list[str]:
        """验证安全配置

        Returns:
            警告信息列表

        Raises:
            ValueError: 生产环境存在严重安全问题时抛出
        """
        warnings = []

        # JWT 密钥检查
        if self.is_production():
            if self.JWT_SECRET == "dev-only-change-in-production":
                raise ValueError(
                    "生产环境必须设置 JWT_SECRET 环境变量！"
                )
            if len(self.JWT_SECRET) < 32:
                warnings.append("JWT_SECRET 长度不足32字符")

        # 数据库检查
        if not self.DATABASE_URL and self.is_production():
            warnings.append("DATABASE_URL 未配置")

        # 服务密钥检查
        if self.SERVICE_SECRET == "internal-service-secret-dev-do-not-use-in-prod":
            warnings.append("SERVICE_SECRET 使用默认值")

        return warnings


class PortalConfig(BaseServiceConfig):
    """门户服务配置"""

    APP_NAME: str = "ONE-DATA-STUDIO-LITE Portal"
    APP_PORT: int = 8010

    # 门户特有配置
    CUBE_STUDIO_URL: str = os.environ.get("CUBE_STUDIO_URL", "http://localhost:30080")
    SUPERSET_ADMIN_USER: str = os.environ.get("SUPERSET_ADMIN_USER", "admin")
    SUPERSET_ADMIN_PASSWORD: str = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin123")

    model_config = {"env_prefix": "PORTAL_", "case_sensitive": False, "extra": "ignore"}


class ServiceConfig(BaseServiceConfig):
    """内部微服务配置基类"""

    # 内部服务间通信
    PORTAL_URL: str = os.environ.get("PORTAL_URL", "http://localhost:8010")

    # 审计日志服务地址
    AUDIT_LOG_URL: str = os.environ.get("AUDIT_LOG_URL", "http://localhost:8016")

    model_config = {"env_prefix": "", "case_sensitive": False, "extra": "ignore"}
