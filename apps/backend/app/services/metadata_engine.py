from __future__ import annotations

import re
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.models import (
    DataSource,
    MetadataColumn,
    MetadataTable,
    MetadataVersion,
)


class MetadataEngine:
    """Service for metadata management and scanning."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_source(
        self,
        source: DataSource,
        include_row_count: bool = False,
        table_filter: str | None = None,
    ) -> dict[str, Any]:
        """Scan a data source and extract metadata."""
        start_time = time.time()
        tables_scanned = 0
        columns_scanned = 0

        connector = get_connector(source.type, source.connection_config)

        try:
            tables = await connector.get_tables()

            if table_filter:
                pattern = re.compile(table_filter)
                tables = [t for t in tables if pattern.match(t["table_name"])]

            for table_info in tables:
                table_name = table_info["table_name"]
                schema_name = table_info.get("schema_name")

                existing = await self.db.execute(
                    select(MetadataTable).where(
                        MetadataTable.source_id == source.id,
                        MetadataTable.table_name == table_name,
                        MetadataTable.schema_name == schema_name,
                    )
                )
                metadata_table = existing.scalar_one_or_none()

                full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
                columns = await connector.get_columns(full_table_name)

                row_count = None
                if include_row_count:
                    try:
                        row_count = await connector.get_row_count(full_table_name)
                    except Exception:
                        pass

                if metadata_table:
                    await self._create_version_snapshot(metadata_table)
                    metadata_table.row_count = row_count
                    metadata_table.version += 1
                else:
                    metadata_table = MetadataTable(
                        source_id=source.id,
                        schema_name=schema_name,
                        table_name=table_name,
                        row_count=row_count,
                    )
                    self.db.add(metadata_table)
                    await self.db.flush()

                await self._sync_columns(metadata_table, columns)
                tables_scanned += 1
                columns_scanned += len(columns)

            await self.db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            return {
                "source_id": source.id,
                "tables_scanned": tables_scanned,
                "columns_scanned": columns_scanned,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            await self.db.rollback()
            raise RuntimeError(f"Metadata scan failed: {e}") from e

    async def _sync_columns(
        self,
        table: MetadataTable,
        columns: list[dict[str, Any]],
    ) -> None:
        """Synchronize column metadata."""
        existing_columns = await self.db.execute(
            select(MetadataColumn).where(MetadataColumn.table_id == table.id)
        )
        existing_map = {col.column_name: col for col in existing_columns.scalars()}

        for col_info in columns:
            col_name = col_info["column_name"]

            if col_name in existing_map:
                existing_col = existing_map[col_name]
                existing_col.data_type = col_info["data_type"]
                existing_col.nullable = col_info.get("nullable", True)
                existing_col.is_primary_key = col_info.get("is_primary_key", False)
                existing_col.default_value = col_info.get("default_value")
                existing_col.ordinal_position = col_info.get("ordinal_position", 0)
            else:
                new_col = MetadataColumn(
                    table_id=table.id,
                    column_name=col_name,
                    data_type=col_info["data_type"],
                    nullable=col_info.get("nullable", True),
                    is_primary_key=col_info.get("is_primary_key", False),
                    default_value=col_info.get("default_value"),
                    ordinal_position=col_info.get("ordinal_position", 0),
                )
                self.db.add(new_col)

    async def _create_version_snapshot(self, table: MetadataTable) -> None:
        """Create a version snapshot of the current metadata."""
        columns = await self.db.execute(
            select(MetadataColumn).where(MetadataColumn.table_id == table.id)
        )

        snapshot = {
            "table_name": table.table_name,
            "schema_name": table.schema_name,
            "description": table.description,
            "tags": table.tags,
            "columns": [
                {
                    "column_name": col.column_name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "is_primary_key": col.is_primary_key,
                    "description": col.description,
                    "tags": col.tags,
                }
                for col in columns.scalars()
            ],
        }

        version = MetadataVersion(
            table_id=table.id,
            version=table.version,
            snapshot_json=snapshot,
        )
        self.db.add(version)

    async def get_table_metadata(
        self,
        source_id: uuid.UUID,
        table_name: str,
        schema_name: str | None = None,
    ) -> MetadataTable | None:
        """Get metadata for a specific table."""
        query = select(MetadataTable).where(
            MetadataTable.source_id == source_id,
            MetadataTable.table_name == table_name,
        )
        if schema_name:
            query = query.where(MetadataTable.schema_name == schema_name)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_column_metadata(
        self,
        column_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> MetadataColumn | None:
        """Update metadata for a column."""
        result = await self.db.execute(
            select(MetadataColumn).where(MetadataColumn.id == column_id)
        )
        column = result.scalar_one_or_none()

        if not column:
            return None

        for key, value in updates.items():
            if hasattr(column, key):
                setattr(column, key, value)

        await self.db.commit()
        return column
