from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class AsyncSessionContextManager:
    """Async context manager for database sessions."""

    def __init__(self):
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        self._session = AsyncSessionLocal()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()


def get_async_session() -> AsyncSessionContextManager:
    """Get an async session context manager."""
    return AsyncSessionContextManager()
