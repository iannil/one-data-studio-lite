"""Repository 基类

提供通用的 CRUD 操作模板。
"""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Repository 基类

    提供通用的 CRUD 操作，子类可以重写或扩展。

    Attributes:
        model: ORM 模型类
        session: 数据库会话
    """

    model: type[T]

    def __init__(self, session: AsyncSession):
        """初始化 Repository

        Args:
            session: 异步数据库会话
        """
        self.session = session

    async def get_by_id(self, id: str | int) -> T | None:
        """根据 ID 获取单条记录

        Args:
            id: 记录 ID

        Returns:
            记录对象或 None
        """
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[T]:
        """获取所有记录（分页）

        Args:
            offset: 偏移量
            limit: 限制数量

        Returns:
            记录列表
        """
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """获取记录总数

        Returns:
            记录总数
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0

    async def create(self, entity: T) -> T:
        """创建记录

        Args:
            entity: 实体对象

        Returns:
            创建后的实体对象
        """
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T) -> T:
        """更新记录

        Args:
            entity: 实体对象

        Returns:
            更新后的实体对象
        """
        await self.session.merge(entity)
        await self.session.flush()
        return entity

    async def delete(self, id: str | int) -> bool:
        """删除记录

        Args:
            id: 记录 ID

        Returns:
            是否删除成功
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            return True
        return False

    async def delete_all(self) -> int:
        """删除所有记录

        Returns:
            删除的记录数
        """
        result = await self.session.execute(delete(self.model))
        return result.rowcount
