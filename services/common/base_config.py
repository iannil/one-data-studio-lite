"""配置基类

提供统一的配置管理基类，减少各服务配置代码重复。
"""

import os
from pathlib import Path as StdPath

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
    DATAHUB_WEBHOOK_SECRET: str = os.environ.get("DATAHUB_WEBHOOK_SECRET", "")
    SUPERSET_URL: str = os.environ.get("SUPERSET_URL", "http://localhost:8088")
    DOLPHINSCHEDULER_URL: str = os.environ.get("DOLPHINSCHEDULER_URL", "http://localhost:12345")
    DOLPHINSCHEDULER_API_URL: str = os.environ.get("DOLPHINSCHEDULER_API_URL", "http://localhost:12345/dolphinscheduler")
    DOLPHINSCHEDULER_TOKEN: str = os.environ.get("DOLPHINSCHEDULER_TOKEN", "")
    HOP_URL: str = os.environ.get("HOP_URL", "http://localhost:8083")
    SEATUNNEL_URL: str = os.environ.get("SEATUNNEL_URL", "http://localhost:5801")
    SEATUNNEL_API_URL: str = os.environ.get("SEATUNNEL_API_URL", "http://localhost:5801")
    CUBE_STUDIO_URL: str = os.environ.get("CUBE_STUDIO_URL", "http://localhost:30080")
    HOP_API_URL: str = os.environ.get("HOP_API_URL", "http://localhost:8083")

    # 内部微服务地址
    NL2SQL_URL: str = os.environ.get("NL2SQL_URL", "http://localhost:8011")
    AI_CLEANING_URL: str = os.environ.get("AI_CLEANING_URL", "http://localhost:8012")
    METADATA_SYNC_URL: str = os.environ.get("METADATA_SYNC_URL", "http://localhost:8013")
    DATA_API_URL: str = os.environ.get("DATA_API_URL", "http://localhost:8014")
    SENSITIVE_DETECT_URL: str = os.environ.get("SENSITIVE_DETECT_URL", "http://localhost:8015")
    AUDIT_LOG_URL: str = os.environ.get("AUDIT_LOG_URL", "http://localhost:8016")

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

    # 外部子系统 API 密钥
    SEA_TUNNEL_API_KEY: str = os.environ.get("SEA_TUNNEL_API_KEY", "")

    model_config = {"env_prefix": "PORTAL_", "case_sensitive": False, "extra": "ignore"}


class ServiceConfig(BaseServiceConfig):
    """内部微服务配置基类

    包含所有内部服务和外部子系统的 URL 配置。
    """

    # ============================================================
    # 外部子系统扩展配置
    # ============================================================
    SEA_TUNNEL_API_KEY: str = os.environ.get("SEA_TUNNEL_API_KEY", "")

    # ============================================================
    # LLM 扩展配置
    # ============================================================
    LLM_TEMPERATURE: float = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
    LLM_TIMEOUT: int = int(os.environ.get("LLM_TIMEOUT", "60"))

    # ============================================================
    # 速率限制配置
    # ============================================================
    RATE_LIMIT_ENABLED: bool = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))

    # ============================================================
    # 文件存储配置
    # ============================================================
    STORAGE_TYPE: str = os.environ.get("STORAGE_TYPE", "local")  # local, s3, oss
    STORAGE_PATH: str = os.environ.get("STORAGE_PATH", "./data/storage")
    S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
    S3_REGION: str = os.environ.get("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY", "")

    # ============================================================
    # 任务队列配置
    # ============================================================
    TASK_QUEUE_TYPE: str = os.environ.get("TASK_QUEUE_TYPE", "memory")  # memory, redis, celery
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "")
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "")

    model_config = {"env_prefix": "", "case_sensitive": False, "extra": "ignore"}

    def get_storage_path(self) -> StdPath:
        """获取存储路径"""
        return StdPath(self.STORAGE_PATH)

    def ensure_storage_dir(self) -> StdPath:
        """确保存储目录存在"""
        path = self.get_storage_path()
        path.mkdir(parents=True, exist_ok=True)
        return path


# ============================================================
# 配置验证函数
# ============================================================

def validate_url(url: str) -> bool:
    """验证 URL 格式是否有效"""
    if not url:
        return False
    return url.startswith(("http://", "https://", "/"))


def validate_database_url(url: str) -> tuple[bool, list[str]]:
    """验证数据库 URL 格式

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    if not url:
        errors.append("数据库 URL 不能为空")
        return False, errors

    # 检查支持的数据库驱动
    supported_drivers = [
        "mysql+aiomysql://",
        "mysql+asyncmy://",
        "postgresql+asyncpg://",
        "sqlite+aiosqlite://",
        "sqlite://",
    ]

    if not any(url.startswith(driver) for driver in supported_drivers):
        errors.append(f"不支持的数据库驱动，支持的驱动: {', '.join(supported_drivers)}")

    # 检查 SQLite 以外的数据库是否包含密码
    if not url.startswith("sqlite") and "password=" in url.lower():
        # 这是一个基本检查，实际部署应该使用环境变量
        pass

    return len(errors) == 0, errors


def validate_redis_url(url: str) -> tuple[bool, list[str]]:
    """验证 Redis URL 格式

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    if not url:
        return True, []  # Redis 是可选的

    if not url.startswith(("redis://", "rediss://")):
        errors.append("Redis URL 必须以 redis:// 或 rediss:// 开头")

    return len(errors) == 0, errors


def check_service_connectivity(timeout: int = 3) -> dict[str, bool]:
    """检查各服务连通性

    Args:
        timeout: 超时时间（秒）

    Returns:
        {服务名称: 是否可达}
    """
    import asyncio

    import httpx

    async def check_one(name: str, url: str) -> tuple[str, bool]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{url.rstrip('/')}/health")
                return name, response.status_code == 200
        except Exception:
            return name, False

    services = ServiceConfig()

    async def check_all():
        checks = [
            check_one("portal", services.PORTAL_URL),
            check_one("nl2sql", services.NL2SQL_URL),
            check_one("data_api", services.DATA_API_URL),
            check_one("audit_log", services.AUDIT_LOG_URL),
        ]
        return await asyncio.gather(*checks)

    return dict(asyncio.run(check_all()))


def get_service_config(service_name: str) -> ServiceConfig:
    """获取服务配置实例

    Args:
        service_name: 服务名称（如 "nl2sql", "data_api"）

    Returns:
        服务配置实例
    """
    config_map = {
        "nl2sql": type("NL2SQLConfig", (ServiceConfig,), {
            "APP_NAME": "NL2SQL Service",
            "APP_PORT": 8011,
        }),
        "data_api": type("DataAPIConfig", (ServiceConfig,), {
            "APP_NAME": "Data Asset API Gateway",
            "APP_PORT": 8014,
        }),
        "ai_cleaning": type("AICleaningConfig", (ServiceConfig,), {
            "APP_NAME": "AI Cleaning Rule Service",
            "APP_PORT": 8012,
        }),
        "metadata_sync": type("MetadataSyncConfig", (ServiceConfig,), {
            "APP_NAME": "Metadata Sync Service",
            "APP_PORT": 8013,
        }),
        "sensitive_detect": type("SensitiveDetectConfig", (ServiceConfig,), {
            "APP_NAME": "Sensitive Data Detection Service",
            "APP_PORT": 8015,
        }),
        "audit_log": type("AuditLogConfig", (ServiceConfig,), {
            "APP_NAME": "Audit Log Service",
            "APP_PORT": 8016,
        }),
    }

    config_class = config_map.get(service_name, ServiceConfig)
    return config_class()


def load_env_file(env_file: str = ".env") -> dict[str, str]:
    """加载 .env 文件

    Args:
        env_file: .env 文件路径

    Returns:
        环境变量字典
    """
    env_vars = {}
    env_path = StdPath(env_file)

    if not env_path.exists():
        return env_vars

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
                os.environ[key] = value

    return env_vars
