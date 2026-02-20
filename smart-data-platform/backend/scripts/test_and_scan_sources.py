"""
Test connections and scan metadata for production data sources.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/test_and_scan_sources.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.connectors import get_connector
from app.models.metadata import DataSource, DataSourceStatus, MetadataTable
from app.services import MetadataEngine


async def test_and_scan_sources() -> None:
    """Test connections and scan all inactive data sources."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("\n" + "=" * 60)
    print("测试连接并扫描元数据")
    print("=" * 60)

    async with async_session() as session:
        # Get all sources that need scanning (no metadata tables)
        result = await session.execute(select(DataSource))
        all_sources = list(result.scalars())

        # Filter sources that don't have metadata tables
        sources = []
        for source in all_sources:
            table_result = await session.execute(
                select(MetadataTable).where(MetadataTable.source_id == source.id)
            )
            tables = list(table_result.scalars())
            if len(tables) == 0:
                sources.append(source)

        if not sources:
            print("\n没有待处理的数据源 (所有数据源已扫描)")
            return

        print(f"\n发现 {len(sources)} 个待扫描的数据源")

        for source in sources:
            print(f"\n{'=' * 50}")
            print(f"📊 处理: {source.name}")
            print(f"   类型: {source.type.value}")
            print(f"   数据库: {source.connection_config.get('database')}")

            # Step 1: Test connection
            print(f"\n   [1/2] 测试连接...")
            try:
                connector = get_connector(source.type, source.connection_config)
                success, message = await connector.test_connection()

                if success:
                    print(f"   ✅ 连接成功: {message}")
                    source.status = DataSourceStatus.ACTIVE
                    await session.commit()
                else:
                    print(f"   ❌ 连接失败: {message}")
                    source.status = DataSourceStatus.ERROR
                    await session.commit()
                    continue
            except Exception as e:
                print(f"   ❌ 连接异常: {e}")
                source.status = DataSourceStatus.ERROR
                await session.commit()
                continue

            # Step 2: Scan metadata
            print(f"\n   [2/2] 扫描元数据...")
            try:
                start_time = time.time()
                metadata_engine = MetadataEngine(session)
                scan_result = await metadata_engine.scan_source(
                    source,
                    include_row_count=True,
                    table_filter=None,
                )
                elapsed = time.time() - start_time

                print(f"   ✅ 扫描完成:")
                print(f"      - 表数量: {scan_result['tables_scanned']}")
                print(f"      - 列数量: {scan_result['columns_scanned']}")
                print(f"      - 耗时: {elapsed:.2f}秒")

            except Exception as e:
                print(f"   ❌ 扫描失败: {e}")

        # Final summary
        print("\n" + "=" * 60)
        print("📋 最终状态")
        print("=" * 60)

        result = await session.execute(select(DataSource))
        all_sources = list(result.scalars())

        for source in all_sources:
            status_icon = {
                DataSourceStatus.ACTIVE: "🟢",
                DataSourceStatus.INACTIVE: "🟡",
                DataSourceStatus.ERROR: "🔴",
                DataSourceStatus.TESTING: "🔵",
            }.get(source.status, "⚪")

            # Count tables
            table_result = await session.execute(
                select(MetadataTable).where(MetadataTable.source_id == source.id)
            )
            table_count = len(list(table_result.scalars()))

            print(f"\n  {status_icon} {source.name}")
            print(f"      状态: {source.status.value}")
            print(f"      表数量: {table_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_and_scan_sources())
