"""Alembic 环境配置

用于数据库迁移的 Alembic 运行时配置。
支持同步和异步两种模式运行迁移。
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# 添加 services 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 ORM 模型和 Base
from common.database import Base

# Alembic Config 对象
config = context.config

# 从环境变量获取数据库 URL
database_url = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:changeme@localhost:3306/one_data_studio"
)
# 同步版本 URL（迁移使用同步驱动）
if "aiomysql" in database_url:
    database_url = database_url.replace("aiomysql", "pymysql")
config.set_main_option("sqlalchemy.url", database_url)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 模型元数据，用于自动生成迁移
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移

    仅生成 SQL 脚本，不实际连接数据库。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移

    连接数据库并执行迁移。
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
