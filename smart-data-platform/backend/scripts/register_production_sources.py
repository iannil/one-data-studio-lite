"""
Register production data sources in the Smart Data Platform.

This script registers the 4 production-grade test databases:
- Finance System (PostgreSQL - finance_db database)
- IoT Platform (PostgreSQL - iot_db database)
- HR System (MySQL - hr_system_db database)
- Medical System (MySQL - medical_db database)

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/register_production_sources.py [--force]

Options:
    --force    Update existing data sources instead of skipping them
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.metadata import DataSource, DataSourceStatus, DataSourceType, MetadataTable


# Data source configurations
PRODUCTION_SOURCES = [
    {
        "name": "金融交易系统 (Finance)",
        "description": "PostgreSQL 金融交易系统，包含客户、账户、交易、投资组合等数据。约 475 万条记录。",
        "type": DataSourceType.POSTGRESQL,
        "connection_config": {
            "host": "localhost",
            "port": 3102,
            "database": "finance_db",
            "username": "postgres",
            "password": "postgres",
        },
    },
    {
        "name": "物联网平台 (IoT)",
        "description": "PostgreSQL IoT 物联网平台，包含设备、传感器、读数、告警等数据。约 590 万条记录。",
        "type": DataSourceType.POSTGRESQL,
        "connection_config": {
            "host": "localhost",
            "port": 3102,
            "database": "iot_db",
            "username": "postgres",
            "password": "postgres",
        },
    },
    {
        "name": "人力资源系统 (HR)",
        "description": "MySQL HR 人力资源系统，包含部门、员工、薪资、考勤、绩效等数据。约 415 万条记录。",
        "type": DataSourceType.MYSQL,
        "connection_config": {
            "host": "localhost",
            "port": 3108,
            "database": "hr_system_db",
            "username": "root",
            "password": "mysql123",
        },
    },
    {
        "name": "医疗健康系统 (Medical)",
        "description": "MySQL 医疗健康系统，包含医院、医生、患者、预约、诊断、处方等数据。约 682 万条记录。",
        "type": DataSourceType.MYSQL,
        "connection_config": {
            "host": "localhost",
            "port": 3108,
            "database": "medical_db",
            "username": "root",
            "password": "mysql123",
        },
    },
]


async def register_sources(force: bool = False) -> None:
    """Register all production data sources.

    Args:
        force: If True, update existing data sources instead of skipping them.
    """
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    action = "强制更新" if force else "注册"
    print("\n" + "=" * 60)
    print(f"{action}生产级测试数据源")
    print("=" * 60)

    async with async_session() as session:
        registered_count = 0
        updated_count = 0
        skipped_count = 0

        for source_config in PRODUCTION_SOURCES:
            # Check if source already exists
            result = await session.execute(
                select(DataSource).where(DataSource.name == source_config["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                if force:
                    # Update existing source
                    existing.description = source_config["description"]
                    existing.connection_config = source_config["connection_config"]
                    # Delete old metadata tables
                    await session.execute(
                        delete(MetadataTable).where(MetadataTable.source_id == existing.id)
                    )
                    print(f"\n🔄 更新: {source_config['name']}")
                    print(f"   数据库: {source_config['connection_config'].get('database')}")
                    print(f"   ID: {existing.id}")
                    updated_count += 1
                else:
                    print(f"\n⏭️  跳过: {source_config['name']}")
                    print(f"   (已存在, ID: {existing.id})")
                    skipped_count += 1
                continue

            # Create new data source
            source = DataSource(
                name=source_config["name"],
                description=source_config["description"],
                type=source_config["type"],
                connection_config=source_config["connection_config"],
                status=DataSourceStatus.INACTIVE,
            )

            session.add(source)
            await session.flush()

            print(f"\n✅ 已注册: {source_config['name']}")
            print(f"   类型: {source_config['type'].value}")
            print(f"   数据库: {source_config['connection_config'].get('database')}")
            print(f"   ID: {source.id}")

            registered_count += 1

        await session.commit()

        print("\n" + "-" * 60)
        if force:
            print(f"完成: 更新 {updated_count} 个数据源, 注册 {registered_count} 个新数据源")
        else:
            print(f"完成: 注册 {registered_count} 个数据源, 跳过 {skipped_count} 个")
        print("=" * 60)

        # List all sources
        result = await session.execute(select(DataSource))
        all_sources = result.scalars().all()

        print("\n📋 当前所有数据源:")
        print("-" * 60)
        for source in all_sources:
            status_icon = "🟢" if source.status == DataSourceStatus.ACTIVE else "🔴"
            print(f"  {status_icon} {source.name}")
            print(f"      ID: {source.id}")
            print(f"      类型: {source.type.value}")
            db_name = source.connection_config.get("database", "N/A")
            print(f"      数据库: {db_name}")
            print(f"      状态: {source.status.value}")
        print()

    await engine.dispose()


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(register_sources(force=force))
