"""脱敏规则 Repository

提供 ShardingSphere 脱敏规则的数据访问接口。
"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.orm_models import MaskRuleORM
from services.common.repositories.base import BaseRepository


class MaskRuleRepository(BaseRepository[MaskRuleORM]):
    """脱敏规则 Repository

    管理脱敏规则配置，用于与 ShardingSphere 同步。
    """

    model = MaskRuleORM

    async def get_by_table(self, table_name: str) -> Sequence[MaskRuleORM]:
        """获取表的所有脱敏规则

        Args:
            table_name: 表名

        Returns:
            脱敏规则列表
        """
        result = await self.session.execute(
            select(MaskRuleORM).where(MaskRuleORM.table_name == table_name)
        )
        return result.scalars().all()

    async def get_by_table_column(
        self,
        table_name: str,
        column_name: str,
    ) -> Optional[MaskRuleORM]:
        """获取特定表列的脱敏规则

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            脱敏规则或 None
        """
        result = await self.session.execute(
            select(MaskRuleORM)
            .where(MaskRuleORM.table_name == table_name)
            .where(MaskRuleORM.column_name == column_name)
        )
        return result.scalar_one_or_none()

    async def get_unsynced_rules(self) -> Sequence[MaskRuleORM]:
        """获取未同步到 Proxy 的规则

        Returns:
            未同步的规则列表
        """
        result = await self.session.execute(
            select(MaskRuleORM)
            .where(MaskRuleORM.synced_to_proxy == False)
            .where(MaskRuleORM.enabled == True)
        )
        return result.scalars().all()

    async def get_enabled_rules(self) -> Sequence[MaskRuleORM]:
        """获取所有启用的规则

        Returns:
            启用的规则列表
        """
        result = await self.session.execute(
            select(MaskRuleORM).where(MaskRuleORM.enabled == True)
        )
        return result.scalars().all()

    async def mark_synced(self, rule_id: int) -> Optional[MaskRuleORM]:
        """标记规则已同步

        Args:
            rule_id: 规则 ID

        Returns:
            更新后的规则或 None
        """
        rule = await self.get_by_id(rule_id)
        if rule:
            rule.synced_to_proxy = True
            await self.session.flush()
        return rule

    async def upsert_by_table_column(
        self,
        table_name: str,
        column_name: str,
        algorithm_type: str,
        algorithm_props: Optional[dict] = None,
    ) -> MaskRuleORM:
        """插入或更新脱敏规则

        Args:
            table_name: 表名
            column_name: 列名
            algorithm_type: 算法类型
            algorithm_props: 算法参数

        Returns:
            保存后的规则对象
        """
        existing = await self.get_by_table_column(table_name, column_name)
        if existing:
            existing.algorithm_type = algorithm_type
            existing.algorithm_props = algorithm_props
            existing.synced_to_proxy = False  # 需要重新同步
            await self.session.flush()
            return existing
        else:
            rule = MaskRuleORM(
                table_name=table_name,
                column_name=column_name,
                algorithm_type=algorithm_type,
                algorithm_props=algorithm_props,
            )
            return await self.create(rule)

    async def delete_by_table_column(
        self,
        table_name: str,
        column_name: str,
    ) -> bool:
        """删除特定表列的脱敏规则

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            是否删除成功
        """
        rule = await self.get_by_table_column(table_name, column_name)
        if rule:
            await self.session.delete(rule)
            await self.session.flush()
            return True
        return False
