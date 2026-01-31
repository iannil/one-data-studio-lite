"""数据库连接管理 - SQLAlchemy 异步引擎"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# 默认数据库 URL - 生产环境必须通过环境变量配置
# 警告: 仅用于开发环境，生产环境请设置 DATABASE_URL 环境变量
DEFAULT_DATABASE_URL = "mysql+aiomysql://root:changeme@localhost:3306/one_data_studio"


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


def get_database_url() -> str:
    """获取数据库连接 URL"""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine(database_url: str | None = None):
    """创建异步数据库引擎"""
    url = database_url or get_database_url()

    # SQLite 不支持连接池参数
    if "sqlite" in url:
        return create_async_engine(url, echo=False)

    return create_async_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )


_engine = None
_session_factory = None


def reset_engine():
    """重置引擎实例（用于测试）"""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def get_engine():
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory():
    """获取全局会话工厂"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入 - 获取数据库会话"""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """上下文管理器 - 获取数据库会话"""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


import re

# 合法的标识符模式 - 只允许字母、数字、下划线
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_identifier(name: str) -> str:
    """验证 SQL 标识符（表名、列名）的安全性

    防止 SQL 注入攻击。只允许合法的标识符字符。

    Args:
        name: 标识符名称

    Returns:
        验证通过的标识符（带反引号）

    Raises:
        ValueError: 标识符包含非法字符
    """
    if not name or len(name) > 64:
        raise ValueError(f"标识符长度无效: {name}")
    if not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"标识符包含非法字符: {name}")
    return f"`{name}`"


async def validate_table_exists(session: AsyncSession, table_name: str) -> str:
    """验证表名存在且安全

    先验证标识符格式，再检查表是否存在于数据库中。

    Args:
        session: 数据库会话
        table_name: 表名

    Returns:
        带反引号的安全表名

    Raises:
        ValueError: 表名无效或表不存在
    """
    from sqlalchemy import text

    # 先验证标识符格式
    safe_name = validate_identifier(table_name)

    # 检测数据库类型并验证表存在
    try:
        # 尝试检测 SQLite
        result = await session.execute(text("SELECT sqlite_version()"))
        is_sqlite = result.fetchone() is not None

        if is_sqlite:
            # SQLite 使用 sqlite_master
            result = await session.execute(
                text("SELECT 1 FROM sqlite_master "
                     "WHERE type='table' AND name = :table"),
                {"table": table_name}
            )
        else:
            # MySQL 使用 information_schema
            result = await session.execute(
                text("SELECT 1 FROM information_schema.TABLES "
                     "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"),
                {"table": table_name}
            )

        if not result.fetchone():
            raise ValueError(f"表不存在: {table_name}")
    except ValueError:
        # ValueError 是我们期望的异常（表不存在），重新抛出
        raise
    except Exception:
        # 其他异常（如数据库连接问题）静默处理，继续执行

        # 最后尝试：直接查询表来验证
        try:
            result = await session.execute(text(f"SELECT 1 FROM {safe_name} LIMIT 1"))
            result.fetchone()
        except Exception:
            raise ValueError(f"表不存在: {table_name}")

    return safe_name


async def get_table_columns(session: AsyncSession, table_name: str) -> list[tuple]:
    """获取表的列信息，兼容 SQLite 和 MySQL

    Args:
        session: 数据库会话
        table_name: 表名

    Returns:
        列信息列表，每个元素为 (name, type, nullable) 元组
    """
    from sqlalchemy import text

    try:
        # 检测数据库类型
        result = await session.execute(text("SELECT sqlite_version()"))
        is_sqlite = result.fetchone() is not None

        if is_sqlite:
            # SQLite 使用 PRAGMA table_info
            safe_name = validate_identifier(table_name)
            result = await session.execute(text(f"PRAGMA table_info({safe_name})"))
            rows = result.fetchall()
            # row: (cid, name, type, notnull, default_value, pk)
            return [(row[1], row[2] or "TEXT", "NO" if row[3] else "YES") for row in rows]
        else:
            # MySQL 使用 information_schema
            result = await session.execute(text(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table "
                "ORDER BY ORDINAL_POSITION"
            ), {"table": table_name})
            return result.fetchall()
    except Exception:
        # 查询失败，返回空列表
        return []

