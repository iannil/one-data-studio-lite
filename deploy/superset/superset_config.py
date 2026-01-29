# ONE-DATA-STUDIO-LITE - Apache Superset 配置
# 文件路径: deploy/superset/superset_config.py

import os

# ========== 基础配置 ==========
# 警告: 生产环境必须通过环境变量设置 SECRET_KEY
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-this-secret-key-in-production")
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    # 警告: 生产环境必须通过环境变量设置数据库连接
    "mysql+pymysql://root:changeme@host.docker.internal:3306/superset",
)

# ========== SQL Lab 配置 ==========
SQL_MAX_ROW = 10000
SQLLAB_TIMEOUT = 300
SQLLAB_DEFAULT_DBID = None
SQL_VALIDATORS_BY_ENGINE = {}

# 支持的数据库引擎
PREFERRED_DATABASES = [
    "MySQL",
    "PostgreSQL",
    "ClickHouse",
    "SQLite",
]

# ========== 缓存配置 (Redis) ==========
REDIS_URL = os.environ.get("REDIS_URL", "redis://superset-redis:6379/0")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": REDIS_URL,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_data_",
    "CACHE_REDIS_URL": REDIS_URL,
}

FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_filter_",
    "CACHE_REDIS_URL": REDIS_URL,
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_explore_",
    "CACHE_REDIS_URL": REDIS_URL,
}

# ========== Celery 配置 ==========

class CeleryConfig:
    broker_url = REDIS_URL
    imports = ("superset.sql_lab",)
    result_backend = REDIS_URL
    worker_prefetch_multiplier = 1
    task_acks_late = False

CELERY_CONFIG = CeleryConfig

# ========== CORS 配置 (与门户集成) ==========
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": [
        "http://localhost:3000",      # 门户前端
        "http://localhost:8080",      # Cube-Studio
        "http://localhost:9002",      # DataHub
        "http://localhost:8010",      # Portal API
    ],
}

# ========== 嵌入模式 ==========
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ALERT_REPORTS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": True,
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
    "ENABLE_DND_WITH_CLICK_UX": True,
}

GUEST_ROLE_NAME = "Public"
GUEST_TOKEN_JWT_SECRET = SECRET_KEY
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = 3600

# ========== 认证配置 (预留SSO集成) ==========
AUTH_TYPE = 1  # AUTH_DB, 后续可切换为 AUTH_OAUTH
# AUTH_TYPE = 4  # AUTH_OAUTH (SSO启用时取消注释)

# ========== 国际化 ==========
BABEL_DEFAULT_LOCALE = "zh"
LANGUAGES = {
    "zh": {"flag": "cn", "name": "Chinese"},
    "en": {"flag": "us", "name": "English"},
}

# ========== 其他 ==========
WTF_CSRF_ENABLED = True
ENABLE_PROXY_FIX = True
MAPBOX_API_KEY = ""
