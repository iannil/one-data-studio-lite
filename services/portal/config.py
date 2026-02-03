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

from services.common.base_config import PortalConfig


def _get_jwt_secret() -> str:
    """获取 JWT 密钥

    优先级:
    1. 环境变量 JWT_SECRET
    2. etcd 配置中心
    3. 开发环境默认值（带警告）

    生产环境必须通过环境变量设置强密钥。
    """
    secret = os.environ.get("JWT_SECRET", "")
    if secret:
        return secret
    return "dev-only-change-in-production"


def _get_dev_users() -> dict:
    """获取开发环境用户配置"""
    users_json = os.environ.get("DEV_USERS", "")
    if users_json:
        try:
            return json.loads(users_json)
        except json.JSONDecodeError:
            pass

    return {
        "admin": {"password": "admin123", "role": "admin", "display_name": "管理员"},
        "super_admin": {"password": "admin123", "role": "super_admin", "display_name": "超级管理员"},
        "analyst": {"password": "ana123", "role": "analyst", "display_name": "数据分析师"},
        "viewer": {"password": "view123", "role": "viewer", "display_name": "查看者"},
        "data_scientist": {"password": "sci123", "role": "data_scientist", "display_name": "数据科学家"},
        "engineer": {"password": "eng123", "role": "engineer", "display_name": "数据工程师"},
        "steward": {"password": "stw123", "role": "steward", "display_name": "数据治理员"},
    }


class Settings(PortalConfig):
    """门户服务配置

    支持从环境变量和 etcd 配置中心加载配置。
    通用配置（JWT、数据库、Redis、LLM、子系统URL等）继承自 PortalConfig。
    """

    # CORS 配置
    ALLOWED_ORIGINS: list[str] = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    ).split(",")

    # Cookie 配置
    USE_COOKIE_AUTH: bool = os.environ.get("USE_COOKIE_AUTH", "true").lower() == "true"
    COOKIE_NAME: str = os.environ.get("COOKIE_NAME", "ods_token")
    COOKIE_DOMAIN: str | None = os.environ.get("COOKIE_DOMAIN")
    COOKIE_SAMESITE: str = os.environ.get("COOKIE_SAMESITE", "lax")
    COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_MAX_AGE: int = int(os.environ.get("COOKIE_MAX_AGE", str(24 * 60 * 60)))

    # 外部子系统认证
    SUPERSET_ADMIN_USER: str = os.environ.get("SUPERSET_ADMIN_USER", "admin")
    SUPERSET_ADMIN_PASSWORD: str = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin123")

    # ShardingSphere 配置文件路径
    SHARDINGSPHERE_CONFIG_PATH: str = os.environ.get(
        "SHARDINGSPHERE_CONFIG_PATH",
        "deploy/shardingsphere/config/config-mask.yaml"
    )

    # 邮件服务配置
    SMTP_ENABLED: bool = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.environ.get("SMTP_FROM_EMAIL", "noreply@one-data-studio.local")
    SMTP_FROM_NAME: str = os.environ.get("SMTP_FROM_NAME", "ONE-DATA-STUDIO-LITE")
    SMTP_USE_TLS: bool = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_TIMEOUT: int = int(os.environ.get("SMTP_TIMEOUT", "30"))

    # 开发环境用户配置
    DEV_USERS: dict = _get_dev_users()

    # 配置中心设置
    ETCD_ENDPOINTS: str = os.environ.get("ETCD_ENDPOINTS", "http://localhost:2379")
    CONFIG_CACHE_TTL: int = int(os.environ.get("CONFIG_CACHE_TTL", "60"))
    ENABLE_CONFIG_CENTER: bool = os.environ.get("ENABLE_CONFIG_CENTER", "true").lower() == "true"
    CONFIG_ENCRYPTION_KEY: str = os.environ.get("CONFIG_ENCRYPTION_KEY", "")

    # ============================================================
    # 验证方法
    # ============================================================

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def validate_security(self) -> list[str]:
        """验证安全配置"""
        warnings = []

        # JWT 密钥检查
        if self.is_production():
            if self.JWT_SECRET == "dev-only-change-in-production":
                raise ValueError("生产环境必须设置 JWT_SECRET 环境变量！")
            if len(self.JWT_SECRET) < 32:
                warnings.append("JWT_SECRET 长度不足32字符")
            weak_secrets = ["password", "secret", "123456", "admin", "change-me"]
            if any(weak in self.JWT_SECRET.lower() for weak in weak_secrets):
                warnings.append("JWT_SECRET 包含常见弱密钥词")
        elif self.JWT_SECRET == "dev-only-change-in-production":
            warnings.append("JWT_SECRET 使用默认值！生产环境必须设置环境变量")

        # DataHub Token 检查（从基类继承）
        if not self.DATAHUB_TOKEN:
            warnings.append("DATAHUB_TOKEN 未配置")

        # DolphinScheduler Token 检查
        if not self.DOLPHINSCHEDULER_TOKEN:
            warnings.append("DOLPHINSCHEDULER_TOKEN 未配置")
        elif self.DOLPHINSCHEDULER_TOKEN in ("default-token", "ds_token_2024"):
            warnings.append("DOLPHINSCHEDULER_TOKEN 使用默认值")

        # Superset 凭据检查
        weak_superset_creds = [
            ("admin", "admin"), ("admin", "admin123"), ("admin", "password"),
            ("superset", "superset"),
        ]
        current_creds = (self.SUPERSET_ADMIN_USER, self.SUPERSET_ADMIN_PASSWORD)
        if current_creds in weak_superset_creds:
            if self.is_production():
                raise ValueError(f"Superset 使用弱凭据({current_creds[0]}/{current_creds[1]})！")
            else:
                warnings.append(f"Superset 使用弱凭据({current_creds[0]}/{current_creds[1]})")

        # 数据库配置检查
        if self.DATABASE_URL and "password=password" in self.DATABASE_URL.lower():
            warnings.append("DATABASE_URL 包含默认密码")

        # 用户配置检查
        if self.DEV_USERS == _get_dev_users() and "admin123" in str(self.DEV_USERS):
            if self.is_production():
                raise ValueError("生产环境不允许使用默认用户凭据！")
            else:
                warnings.append("使用默认开发用户(admin/admin123)，生产环境必须修改")

        # 配置中心加密检查
        if self.is_production() and self.ENABLE_CONFIG_CENTER and not self.CONFIG_ENCRYPTION_KEY:
            warnings.append("配置中心已启用但未设置 CONFIG_ENCRYPTION_KEY")

        # 内部服务 Token 检查
        internal_token = os.environ.get("INTERNAL_TOKEN", "")
        if not internal_token and self.is_production():
            warnings.append("INTERNAL_TOKEN 未配置")

        # Webhook 签名密钥检查
        webhook_secret = os.environ.get("META_SYNC_DATAHUB_WEBHOOK_SECRET", "")
        if not webhook_secret and self.is_production():
            warnings.append("META_SYNC_DATAHUB_WEBHOOK_SECRET 未配置")

        return warnings


settings = Settings()


# ============================================================
# 配置热更新支持
# ============================================================

_config_callbacks: list[callable] = []


def register_config_callback(callback: callable) -> None:
    """注册配置变更回调"""
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
    """初始化配置中心并加载配置"""
    if not settings.ENABLE_CONFIG_CENTER:
        return

    try:
        from services.common.config_center import get_config_center

        cc = get_config_center()

        if not cc.is_available():
            import logging
            logging.warning(f"配置中心不可用 ({settings.ETCD_ENDPOINTS})，使用环境变量和默认值")
            return

        cc.register_callback("/one-data-studio/portal/", on_config_change)

        # 从配置中心加载敏感配置
        jwt_secret = await cc.get("portal/jwt/secret", default=settings.JWT_SECRET)
        if jwt_secret and jwt_secret != settings.JWT_SECRET:
            object.__setattr__(settings, 'JWT_SECRET', jwt_secret)

        superset_username = await cc.get("superset/auth/username", default=settings.SUPERSET_ADMIN_USER)
        if superset_username:
            object.__setattr__(settings, 'SUPERSET_ADMIN_USER', superset_username)

        superset_password = await cc.get("superset/auth/password", default=settings.SUPERSET_ADMIN_PASSWORD)
        if superset_password:
            object.__setattr__(settings, 'SUPERSET_ADMIN_PASSWORD', superset_password)

        ds_token = await cc.get("dolphinscheduler/token", default=settings.DOLPHINSCHEDULER_TOKEN)
        if ds_token:
            object.__setattr__(settings, 'DOLPHINSCHEDULER_TOKEN', ds_token)

        import logging
        logging.info("配置中心初始化完成")

    except ImportError:
        import logging
        logging.warning("配置中心模块不可用，使用环境变量和默认值")


# ============================================================
# 便捷函数：运行时获取配置
# ============================================================

async def get_config(key: str, default=None):
    """从配置中心获取配置"""
    env_key = key.upper().replace("/", "_").replace("-", "_")
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value

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
    """设置配置到配置中心"""
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
