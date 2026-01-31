"""统一入口门户 - 配置

支持多层级配置加载:
1. etcd 配置中心（优先）
2. 环境变量（降级兜底）
3. 代码默认值（最后）

配置热更新:
- 当 etcd 中配置变更时，自动重新加载
- 支持配置变更回调注册
"""

import json
import os
import re
import secrets
from typing import Optional

from services.common.base_config import BaseServiceConfig


def _get_jwt_secret() -> str:
    """获取 JWT 密钥

    优先级:
    1. 环境变量 JWT_SECRET
    2. etcd 配置中心
    3. 开发环境默认值（带警告）

    生产环境必须通过环境变量设置强密钥。
    """
    # 1. 环境变量优先
    secret = os.environ.get("JWT_SECRET", "")
    if secret:
        return secret

    # 2. 尝试从 etcd 获取（异步，需在应用启动后）
    # 这里不做同步获取，避免启动阻塞
    # 实际使用时通过 ConfigCenter 异步获取

    # 3. 开发环境默认值
    return "dev-only-change-in-production"


def _get_dev_users() -> dict:
    """获取开发环境用户配置

    支持通过环境变量配置用户，格式为 JSON:
    DEV_USERS='{"admin": {"password": "xxx", "role": "admin", "display_name": "管理员"}}'

    开发环境默认值仅在未配置时使用。
    """
    users_json = os.environ.get("DEV_USERS", "")
    if users_json:
        try:
            return json.loads(users_json)
        except json.JSONDecodeError:
            pass

    # 开发环境默认用户（生产环境不应使用）
    return {
        "admin": {"password": "admin123", "role": "admin", "display_name": "管理员"},
        "super_admin": {"password": "admin123", "role": "super_admin", "display_name": "超级管理员"},
        "analyst": {"password": "ana123", "role": "analyst", "display_name": "数据分析师"},
        "viewer": {"password": "view123", "role": "viewer", "display_name": "查看者"},
        "data_scientist": {"password": "sci123", "role": "data_scientist", "display_name": "数据科学家"},
        "engineer": {"password": "eng123", "role": "engineer", "display_name": "数据工程师"},
        "steward": {"password": "stw123", "role": "steward", "display_name": "数据治理员"},
    }


class Settings(BaseServiceConfig):
    """门户服务配置

    支持从环境变量和 etcd 配置中心加载配置。
    环境变量优先级高于 etcd。
    """

    # ============================================================
    # 服务配置
    # ============================================================
    APP_NAME: str = "ONE-DATA-STUDIO-LITE Portal"
    APP_PORT: int = 8010
    DEBUG: bool = False

    # 环境标识
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # ============================================================
    # JWT 配置 - 生产环境必须通过环境变量设置
    # ============================================================
    JWT_SECRET: str = _get_jwt_secret()
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # ============================================================
    # 子系统地址
    # ============================================================
    CUBE_STUDIO_URL: str = "http://localhost:30080"
    SUPERSET_URL: str = "http://localhost:8088"
    DATAHUB_URL: str = "http://localhost:9002"
    DOLPHINSCHEDULER_URL: str = "http://localhost:12345"
    HOP_URL: str = "http://localhost:8083"

    # ============================================================
    # 代理目标地址
    # ============================================================
    SEATUNNEL_URL: str = "http://localhost:5802"
    DATAHUB_GMS_URL: str = "http://localhost:8081"
    DATAHUB_TOKEN: str = ""
    NL2SQL_URL: str = "http://localhost:8011"
    AI_CLEANING_URL: str = "http://localhost:8012"
    METADATA_SYNC_URL: str = "http://localhost:8013"
    DATA_API_URL: str = "http://localhost:8014"
    SENSITIVE_DETECT_URL: str = "http://localhost:8015"
    AUDIT_LOG_URL: str = "http://localhost:8016"

    # ============================================================
    # 外部子系统认证
    # ============================================================
    SUPERSET_ADMIN_USER: str = "admin"
    SUPERSET_ADMIN_PASSWORD: str = "admin123"
    DOLPHINSCHEDULER_TOKEN: str = "a27c7d529a0bf364de5c14dc0c481469"

    # SeaTunnel API Key（可选，用于 SeaTunnel 认证）
    SEA_TUNNEL_API_KEY: str = ""

    # ============================================================
    # ShardingSphere 配置文件路径
    # ============================================================
    SHARDINGSPHERE_CONFIG_PATH: str = "deploy/shardingsphere/config/config-mask.yaml"

    # ============================================================
    # 数据库 - 生产环境必须通过环境变量设置
    # ============================================================
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # ============================================================
    # Redis 配置（用于 Token 黑名单）
    # ============================================================
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_BLACKLIST_DB: int = int(os.environ.get("REDIS_BLACKLIST_DB", "0"))

    # ============================================================
    # 开发环境用户配置（生产环境应使用数据库或外部认证）
    # 可通过 DEV_USERS 环境变量配置，格式为 JSON
    # ============================================================
    DEV_USERS: dict = _get_dev_users()

    # ============================================================
    # 配置中心设置
    # ============================================================
    # etcd 服务地址
    ETCD_ENDPOINTS: str = os.environ.get("ETCD_ENDPOINTS", "http://localhost:2379")
    # 配置缓存过期时间（秒）
    CONFIG_CACHE_TTL: int = int(os.environ.get("CONFIG_CACHE_TTL", "60"))
    # 是否启用配置中心
    ENABLE_CONFIG_CENTER: bool = os.environ.get("ENABLE_CONFIG_CENTER", "true").lower() == "true"

    # ============================================================
    # 敏感配置加密
    # ============================================================
    # 加密密钥（Base64 编码的 Fernet key）
    CONFIG_ENCRYPTION_KEY: str = os.environ.get("CONFIG_ENCRYPTION_KEY", "")

    model_config = {"env_prefix": "PORTAL_"}

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def validate_security(self) -> list[str]:
        """验证安全配置

        Returns:
            警告信息列表

        Raises:
            ValueError: 生产环境存在严重安全问题时抛出
        """
        warnings = []

        # ============================================================
        # JWT 密钥检查
        # ============================================================
        if self.is_production():
            if self.JWT_SECRET == "dev-only-change-in-production":
                raise ValueError(
                    "生产环境必须设置 JWT_SECRET 环境变量！"
                    "请使用强随机字符串: openssl rand -hex 32"
                )
            if len(self.JWT_SECRET) < 32:
                warnings.append("JWT_SECRET 长度不足32字符，建议使用更长的密钥")
            # 检查是否使用了常见的弱密钥
            weak_secrets = ["password", "secret", "123456", "admin", "change-me"]
            if any(weak in self.JWT_SECRET.lower() for weak in weak_secrets):
                warnings.append("JWT_SECRET 包含常见弱密钥词，请使用随机生成的密钥")
        elif self.JWT_SECRET == "dev-only-change-in-production":
            warnings.append(
                "JWT_SECRET 使用默认值！生产环境必须设置环境变量 JWT_SECRET 为强随机字符串"
            )

        # ============================================================
        # 子系统 Token 检查
        # ============================================================
        # DataHub Token
        if not self.DATAHUB_TOKEN:
            warnings.append(
                "DATAHUB_TOKEN 未配置，DataHub 代理将无法正常工作。"
                "请在 DataHub 中生成 Personal Access Token 并设置环境变量"
            )
        elif len(self.DATAHUB_TOKEN) < 16:
            warnings.append("DATAHUB_TOKEN 长度较短，请确认 Token 正确性")

        # DolphinScheduler Token
        if not self.DOLPHINSCHEDULER_TOKEN:
            warnings.append(
                "DOLPHINSCHEDULER_TOKEN 未配置，DolphinScheduler 代理将无法正常工作。"
                "请在 DS 中创建 Token 并设置环境变量"
            )
        elif self.DOLPHINSCHEDULER_TOKEN in ("default-token", "ds_token_2024"):
            warnings.append(
                "DOLPHINSCHEDULER_TOKEN 使用默认值，生产环境请更换为随机生成的 Token"
            )

        # SeaTunnel API Key
        if not self.SEA_TUNNEL_API_KEY:
            warnings.append(
                "SEA_TUNNEL_API_KEY 未配置，SeaTunnel API 访问未启用认证。"
                "生产环境建议配置以启用 API Key 认证"
            )

        # ============================================================
        # Superset 凭据检查
        # ============================================================
        weak_superset_creds = [
            ("admin", "admin"),
            ("admin", "admin123"),
            ("admin", "password"),
            ("superset", "superset"),
        ]
        current_creds = (self.SUPERSET_ADMIN_USER, self.SUPERSET_ADMIN_PASSWORD)
        if current_creds in weak_superset_creds:
            if self.is_production():
                raise ValueError(
                    f"Superset 使用弱凭据({current_creds[0]}/{current_creds[1]})！"
                    "生产环境必须修改 SUPERSET_ADMIN_USER 和 SUPERSET_ADMIN_PASSWORD"
                )
            else:
                warnings.append(
                    f"Superset 使用弱凭据({current_creds[0]}/{current_creds[1]})，"
                    "生产环境请设置 SUPERSET_ADMIN_USER 和 SUPERSET_ADMIN_PASSWORD"
                )
        # 检查密码强度
        if self.SUPERSET_ADMIN_PASSWORD and len(self.SUPERSET_ADMIN_PASSWORD) < 8:
            warnings.append("SUPERSET_ADMIN_PASSWORD 长度不足8字符，建议使用更强的密码")

        # ============================================================
        # 数据库配置检查
        # ============================================================
        if not self.DATABASE_URL and self.is_production():
            warnings.append("DATABASE_URL 未配置，生产环境必须设置数据库连接")
        elif self.DATABASE_URL:
            # 检查是否包含默认密码
            if "password=password" in self.DATABASE_URL.lower():
                warnings.append("DATABASE_URL 包含默认密码，请修改")
            if "password=123456" in self.DATABASE_URL.lower():
                warnings.append("DATABASE_URL 包含弱密码，请使用强密码")

        # ============================================================
        # 用户配置检查
        # ============================================================
        if self.DEV_USERS == _get_dev_users() and "admin123" in str(self.DEV_USERS):
            if self.is_production():
                raise ValueError(
                    "生产环境不允许使用默认用户凭据！"
                    "请通过 DEV_USERS 环境变量配置用户，或集成外部认证系统"
                )
            else:
                warnings.append(
                    "使用默认开发用户(admin/admin123)，生产环境必须修改 DEV_USERS 或集成外部认证"
                )

        # ============================================================
        # 配置中心加密检查
        # ============================================================
        if self.is_production() and self.ENABLE_CONFIG_CENTER and not self.CONFIG_ENCRYPTION_KEY:
            warnings.append(
                "配置中心已启用但未设置 CONFIG_ENCRYPTION_KEY，敏感配置将无法加密存储。"
                "生成方法: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        # ============================================================
        # 内部服务 Token 检查
        # ============================================================
        internal_token = os.environ.get("INTERNAL_TOKEN", "")
        if not internal_token and self.is_production():
            warnings.append(
                "INTERNAL_TOKEN 未配置，服务间通信未加密。"
                "生产环境建议配置以启用服务间认证。"
                "生成方法: openssl rand -hex 32"
            )

        # ============================================================
        # Webhook 签名密钥检查
        # ============================================================
        webhook_secret = os.environ.get("META_SYNC_DATAHUB_WEBHOOK_SECRET", "")
        if not webhook_secret and self.is_production():
            warnings.append(
                "META_SYNC_DATAHUB_WEBHOOK_SECRET 未配置，DataHub Webhook 验证未启用。"
                "生产环境建议配置以验证 Webhook 请求来源。"
                "生成方法: openssl rand -hex 32"
            )

        return warnings


settings = Settings()


# ============================================================
# 配置热更新支持
# ============================================================

_config_callbacks: list[callable] = []


def register_config_callback(callback: callable) -> None:
    """注册配置变更回调

    当配置中心的配置变更时，所有注册的回调将被调用。

    Args:
        callback: 回调函数，签名 (key: str, value: Any) -> None
    """
    if callback not in _config_callbacks:
        _config_callbacks.append(callback)


def unregister_config_callback(callback: callable) -> None:
    """取消注册配置变更回调"""
    if callback in _config_callbacks:
        _config_callbacks.remove(callback)


def on_config_change(key: str, value) -> None:
    """触发配置变更回调"""
    for callback in _config_callbacks:
        try:
            callback(key, value)
        except Exception as e:
            import logging
            logging.warning(f"配置变更回调执行失败: {e}")


# ============================================================
# 配置中心初始化（异步）
# ============================================================

async def init_config_center():
    """初始化配置中心并加载配置

    此函数应在应用启动后调用。
    """
    if not settings.ENABLE_CONFIG_CENTER:
        return

    try:
        from services.common.config_center import get_config_center

        cc = get_config_center()

        # 检查服务可用性
        if not cc.is_available():
            import logging
            logging.warning(f"配置中心不可用 ({settings.ETCD_ENDPOINTS})，使用环境变量和默认值")
            return

        # 注册全局配置变更回调
        cc.register_callback("/one-data-studio/portal/", on_config_change)

        # 从配置中心加载敏感配置
        jwt_secret = await cc.get("portal/jwt/secret", default=settings.JWT_SECRET)
        if jwt_secret and jwt_secret != settings.JWT_SECRET:
            settings.JWT_SECRET = jwt_secret

        # 更新其他配置
        superset_username = await cc.get("superset/auth/username", default=settings.SUPERSET_ADMIN_USER)
        if superset_username:
            settings.SUPERSET_ADMIN_USER = superset_username

        superset_password = await cc.get("superset/auth/password", default=settings.SUPERSET_ADMIN_PASSWORD)
        if superset_password:
            settings.SUPERSET_ADMIN_PASSWORD = superset_password

        ds_token = await cc.get("dolphinscheduler/token", default=settings.DOLPHINSCHEDULER_TOKEN)
        if ds_token:
            settings.DOLPHINSCHEDULER_TOKEN = ds_token

        import logging
        logging.info("配置中心初始化完成")

    except ImportError:
        import logging
        logging.warning("配置中心模块不可用，使用环境变量和默认值")


# ============================================================
# 便捷函数：运行时获取配置
# ============================================================

async def get_config(key: str, default=None):
    """从配置中心获取配置

    优先级: 配置中心 > 环境变量 > 默认值

    Args:
        key: 配置键（不含前缀）
        default: 默认值

    Returns:
        配置值
    """
    # 1. 尝试环境变量
    env_key = key.upper().replace("/", "_").replace("-", "_")
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value

    # 2. 尝试配置中心
    if settings.ENABLE_CONFIG_CENTER:
        try:
            from services.common.config_center import get_config_center
            cc = get_config_center()
            if cc.is_available():
                return await cc.get(f"portal/{key}", default=default)
        except Exception:
            pass

    return default


async def set_config(key: str, value, encrypt: bool = False) -> bool:
    """设置配置到配置中心

    Args:
        key: 配置键（不含前缀）
        value: 配置值
        encrypt: 是否加密存储

    Returns:
        是否成功
    """
    if not settings.ENABLE_CONFIG_CENTER:
        return False

    try:
        from services.common.config_center import get_config_center
        cc = get_config_center()
        if cc.is_available():
            return await cc.put(f"portal/{key}", value, encrypt=encrypt)
    except Exception:
        pass

    return False
