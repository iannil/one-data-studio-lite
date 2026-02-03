"""审计日志 Repository

提供审计事件的数据访问接口。
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc, func, select

from services.common.orm_models import AuditEventORM
from services.common.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditEventORM]):
    """审计事件 Repository

    提供审计日志的查询、统计和导出功能。
    """

    model = AuditEventORM

    async def query(
        self,
        subsystem: str | None = None,
        event_type: str | None = None,
        user: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Sequence[AuditEventORM]:
        """查询审计日志

        Args:
            subsystem: 子系统过滤
            event_type: 事件类型过滤
            user: 用户过滤
            start_time: 开始时间
            end_time: 结束时间
            page: 页码（从 1 开始）
            page_size: 每页大小

        Returns:
            审计事件列表
        """
        stmt = select(AuditEventORM)

        if subsystem:
            stmt = stmt.where(AuditEventORM.subsystem == subsystem)
        if event_type:
            stmt = stmt.where(AuditEventORM.event_type == event_type)
        if user:
            stmt = stmt.where(AuditEventORM.user == user)
        if start_time:
            stmt = stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            stmt = stmt.where(AuditEventORM.created_at <= end_time)

        stmt = stmt.order_by(desc(AuditEventORM.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """获取审计统计

        Args:
            start_time: 统计开始时间
            end_time: 统计结束时间

        Returns:
            统计结果字典
        """
        base_stmt = select(AuditEventORM)
        if start_time:
            base_stmt = base_stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            base_stmt = base_stmt.where(AuditEventORM.created_at <= end_time)

        # 总数
        count_result = await self.session.execute(
            select(func.count()).select_from(base_stmt.subquery())
        )
        total = count_result.scalar() or 0

        # 按子系统统计
        subsystem_stmt = select(
            AuditEventORM.subsystem,
            func.count().label("count")
        ).group_by(AuditEventORM.subsystem)
        if start_time:
            subsystem_stmt = subsystem_stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            subsystem_stmt = subsystem_stmt.where(AuditEventORM.created_at <= end_time)
        subsystem_result = await self.session.execute(subsystem_stmt)
        by_subsystem = {row.subsystem: row.count for row in subsystem_result}

        # 按事件类型统计
        type_stmt = select(
            AuditEventORM.event_type,
            func.count().label("count")
        ).group_by(AuditEventORM.event_type)
        if start_time:
            type_stmt = type_stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            type_stmt = type_stmt.where(AuditEventORM.created_at <= end_time)
        type_result = await self.session.execute(type_stmt)
        by_type = {row.event_type: row.count for row in type_result}

        # 按用户统计
        user_stmt = select(
            AuditEventORM.user,
            func.count().label("count")
        ).group_by(AuditEventORM.user)
        if start_time:
            user_stmt = user_stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            user_stmt = user_stmt.where(AuditEventORM.created_at <= end_time)
        user_result = await self.session.execute(user_stmt)
        by_user = {row.user: row.count for row in user_result}

        # 时间范围
        time_stmt = select(
            func.min(AuditEventORM.created_at).label("min_time"),
            func.max(AuditEventORM.created_at).label("max_time"),
        )
        if start_time:
            time_stmt = time_stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            time_stmt = time_stmt.where(AuditEventORM.created_at <= end_time)
        time_result = await self.session.execute(time_stmt)
        time_row = time_result.first()

        return {
            "total_events": total,
            "events_by_subsystem": by_subsystem,
            "events_by_type": by_type,
            "events_by_user": by_user,
            "time_range_start": time_row.min_time if time_row else None,
            "time_range_end": time_row.max_time if time_row else None,
        }

    async def export(
        self,
        subsystem: str | None = None,
        user: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[AuditEventORM]:
        """导出审计日志

        Args:
            subsystem: 子系统过滤
            user: 用户过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            审计事件列表（不分页）
        """
        stmt = select(AuditEventORM)

        if subsystem:
            stmt = stmt.where(AuditEventORM.subsystem == subsystem)
        if user:
            stmt = stmt.where(AuditEventORM.user == user)
        if start_time:
            stmt = stmt.where(AuditEventORM.created_at >= start_time)
        if end_time:
            stmt = stmt.where(AuditEventORM.created_at <= end_time)

        stmt = stmt.order_by(desc(AuditEventORM.created_at))

        result = await self.session.execute(stmt)
        return result.scalars().all()
