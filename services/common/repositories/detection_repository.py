"""敏感数据检测 Repository

提供检测规则和扫描报告的数据访问接口。
"""

from typing import Optional, Sequence

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.orm_models import (
    DetectionRuleORM,
    ScanReportORM,
    SensitiveFieldORM,
)
from services.common.repositories.base import BaseRepository


class DetectionRuleRepository(BaseRepository[DetectionRuleORM]):
    """检测规则 Repository

    管理自定义敏感数据检测规则。
    """

    model = DetectionRuleORM

    async def get_by_name(self, name: str) -> Optional[DetectionRuleORM]:
        """根据名称获取规则

        Args:
            name: 规则名称

        Returns:
            规则对象或 None
        """
        result = await self.session.execute(
            select(DetectionRuleORM).where(DetectionRuleORM.name == name)
        )
        return result.scalar_one_or_none()

    async def get_enabled_rules(self) -> Sequence[DetectionRuleORM]:
        """获取所有启用的规则

        Returns:
            启用的规则列表
        """
        result = await self.session.execute(
            select(DetectionRuleORM).where(DetectionRuleORM.enabled == True)
        )
        return result.scalars().all()

    async def toggle_enabled(self, id: str, enabled: bool) -> Optional[DetectionRuleORM]:
        """切换规则启用状态

        Args:
            id: 规则 ID
            enabled: 是否启用

        Returns:
            更新后的规则对象或 None
        """
        rule = await self.get_by_id(id)
        if rule:
            rule.enabled = enabled
            await self.session.flush()
        return rule


class ScanReportRepository(BaseRepository[ScanReportORM]):
    """扫描报告 Repository

    管理敏感数据扫描报告和字段详情。
    """

    model = ScanReportORM

    async def get_by_table(
        self,
        table_name: str,
        limit: int = 10,
    ) -> Sequence[ScanReportORM]:
        """获取表的扫描报告

        Args:
            table_name: 表名
            limit: 最大返回数量

        Returns:
            扫描报告列表
        """
        result = await self.session.execute(
            select(ScanReportORM)
            .where(ScanReportORM.table_name == table_name)
            .order_by(desc(ScanReportORM.scan_time))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_latest_reports(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Sequence[ScanReportORM]:
        """获取最新扫描报告

        Args:
            page: 页码
            page_size: 每页大小

        Returns:
            扫描报告列表
        """
        result = await self.session.execute(
            select(ScanReportORM)
            .order_by(desc(ScanReportORM.scan_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all()

    async def create_with_fields(
        self,
        report: ScanReportORM,
        fields: list[SensitiveFieldORM],
    ) -> ScanReportORM:
        """创建报告及其字段

        Args:
            report: 报告对象
            fields: 敏感字段列表

        Returns:
            创建后的报告对象
        """
        self.session.add(report)
        for field in fields:
            field.report_id = report.id
            self.session.add(field)
        await self.session.flush()
        return report

    async def get_fields(self, report_id: str) -> Sequence[SensitiveFieldORM]:
        """获取报告的敏感字段

        Args:
            report_id: 报告 ID

        Returns:
            敏感字段列表
        """
        result = await self.session.execute(
            select(SensitiveFieldORM).where(SensitiveFieldORM.report_id == report_id)
        )
        return result.scalars().all()

    async def delete_with_fields(self, report_id: str) -> bool:
        """删除报告及其字段

        Args:
            report_id: 报告 ID

        Returns:
            是否删除成功
        """
        # 先删除字段
        await self.session.execute(
            select(SensitiveFieldORM)
            .where(SensitiveFieldORM.report_id == report_id)
        )
        from sqlalchemy import delete
        await self.session.execute(
            delete(SensitiveFieldORM).where(SensitiveFieldORM.report_id == report_id)
        )
        # 再删除报告
        return await self.delete(report_id)
