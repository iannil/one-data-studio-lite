"""
Register production data sources in the Smart Data Platform.

This script registers the 4 production-grade test databases:
- Finance System (PostgreSQL - finance schema)
- IoT Platform (PostgreSQL - iot schema)
- HR System (MySQL - hr_system database)
- Medical System (MySQL - medical database)

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/register_production_sources.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.metadata import DataSource, DataSourceStatus, DataSourceType


# Data source configurations
PRODUCTION_SOURCES = [
    {
        "name": "金融交易系统 (Finance)",
        "description": "PostgreSQL 金融交易系统，包含客户、账户、交易、投资组合等数据。约 475 万条记录。",
        "type": DataSourceType.POSTGRESQL,
        "connection_config": {
            "host": "localhost",
            "port": 5502,
            "database": "smart_data",
            "username": "postgres",
            "password": "postgres",
            "schema": "finance",
        },
    },
    {
        "name": "物联网平台 (IoT)",
        "description": "PostgreSQL IoT 物联网平台，包含设备、传感器、读数、告警等数据。约 590 万条记录。",
        "type": DataSourceType.POSTGRESQL,
        "connection_config": {
            "host": "localhost",
            "port": 5502,
            "database": "smart_data",
            "username": "postgres",
            "password": "postgres",
            "schema": "iot",
        },
    },
    {
        "name": "人力资源系统 (HR)",
        "description": "MySQL HR 人力资源系统，包含部门、员工、薪资、考勤、绩效等数据。约 415 万条记录。",
        "type": DataSourceType.MYSQL,
        "connection_config": {
            "host": "localhost",
            "port": 5510,
            "database": "hr_system",
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
            "port": 5510,
            "database": "medical",
            "username": "root",
            "password": "mysql123",
        },
    },
]


async def register_sources() -> None:
    """Register all production data sources."""
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    print("\n" + "=" * 60)
    print("注册生产级测试数据源")
    print("=" * 60)

    async with async_session() as session:
        registered_count = 0
        skipped_count = 0

        for source_config in PRODUCTION_SOURCES:
            # Check if source already exists
            result = await session.execute(
                select(DataSource).where(DataSource.name == source_config["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
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
            print(f"      状态: {source.status.value}")
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(register_sources())
