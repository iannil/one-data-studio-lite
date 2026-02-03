"""ETL 映射规则 Repository

提供元数据到 ETL 任务映射规则的数据访问接口。
"""

from collections.abc import Sequence

from sqlalchemy import select

from services.common.orm_models import ETLMappingORM
from services.common.repositories.base import BaseRepository


class ETLMappingRepository(BaseRepository[ETLMappingORM]):
    """ETL 映射规则 Repository

    管理 DataHub 元数据变更与 ETL 任务的映射关系。
    """

    model = ETLMappingORM

    async def get_by_source_urn(self, source_urn: str) -> Sequence[ETLMappingORM]:
        """根据源 URN 获取映射规则

        Args:
            source_urn: DataHub 数据源 URN

        Returns:
            映射规则列表
        """
        result = await self.session.execute(
            select(ETLMappingORM).where(ETLMappingORM.source_urn == source_urn)
        )
        return result.scalars().all()

    async def get_enabled_mappings(self) -> Sequence[ETLMappingORM]:
        """获取所有启用的映射规则

        Returns:
            启用的映射规则列表
        """
        result = await self.session.execute(
            select(ETLMappingORM).where(ETLMappingORM.enabled == True)
        )
        return result.scalars().all()

    async def get_by_target(
        self,
        task_type: str,
        task_id: str,
    ) -> ETLMappingORM | None:
        """根据目标任务获取映射规则

        Args:
            task_type: 任务类型 (seatunnel/hop/dolphinscheduler)
            task_id: 任务 ID

        Returns:
            映射规则或 None
        """
        result = await self.session.execute(
            select(ETLMappingORM)
            .where(ETLMappingORM.target_task_type == task_type)
            .where(ETLMappingORM.target_task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def find_matching(
        self,
        entity_urn: str,
        change_type: str,
    ) -> Sequence[ETLMappingORM]:
        """查找匹配的映射规则

        用于处理元数据变更事件，查找需要触发的 ETL 任务。

        Args:
            entity_urn: 变更的实体 URN
            change_type: 变更类型 (CREATE/UPDATE/DELETE)

        Returns:
            匹配的映射规则列表
        """
        # 获取所有启用且 source_urn 匹配的规则
        result = await self.session.execute(
            select(ETLMappingORM)
            .where(ETLMappingORM.source_urn == entity_urn)
            .where(ETLMappingORM.enabled == True)
        )
        mappings = result.scalars().all()

        # 过滤 trigger_on 包含该变更类型的规则
        return [m for m in mappings if change_type in m.trigger_on]

    async def toggle_enabled(self, id: str, enabled: bool) -> ETLMappingORM | None:
        """切换映射规则启用状态

        Args:
            id: 规则 ID
            enabled: 是否启用

        Returns:
            更新后的规则对象或 None
        """
        mapping = await self.get_by_id(id)
        if mapping:
            mapping.enabled = enabled
            await self.session.flush()
        return mapping

    async def upsert(self, mapping: ETLMappingORM) -> ETLMappingORM:
        """插入或更新映射规则

        Args:
            mapping: 映射规则对象

        Returns:
            保存后的映射规则对象
        """
        existing = await self.get_by_id(mapping.id)
        if existing:
            existing.source_urn = mapping.source_urn
            existing.target_task_type = mapping.target_task_type
            existing.target_task_id = mapping.target_task_id
            existing.trigger_on = mapping.trigger_on
            existing.auto_update_config = mapping.auto_update_config
            existing.description = mapping.description
            existing.enabled = mapping.enabled
            await self.session.flush()
            return existing
        else:
            return await self.create(mapping)
