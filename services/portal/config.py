"""统一入口门户 - 配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """门户服务配置"""

    # 服务配置
    APP_NAME: str = "ONE-DATA-STUDIO-LITE Portal"
    APP_PORT: int = 8010
    DEBUG: bool = False

    # JWT 配置 - 生产环境必须通过环境变量设置
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-only-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # 子系统地址
    CUBE_STUDIO_URL: str = "http://localhost:30080"
    SUPERSET_URL: str = "http://localhost:8088"
    DATAHUB_URL: str = "http://localhost:9002"
    DOLPHINSCHEDULER_URL: str = "http://localhost:12345"
    HOP_URL: str = "http://localhost:8083"

    # 数据库 - 生产环境必须通过环境变量设置
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    model_config = {"env_prefix": "PORTAL_"}


settings = Settings()
