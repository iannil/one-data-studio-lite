from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metadata_engine import MetadataEngine
from app.models import DataSource, DataSourceType, MetadataTable, MetadataColumn


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_source():
    """Create a mock data source."""
    source = MagicMock(spec=DataSource)
    source.id = uuid.uuid4()
    source.type = DataSourceType.POSTGRESQL
    source.connection_config = {"host": "localhost", "database": "test"}
    return source


@pytest.fixture
def mock_connector():
    """Create a mock connector."""
    connector = AsyncMock()
    connector.get_tables = AsyncMock(return_value=[
        {"table_name": "users", "schema_name": "public"},
        {"table_name": "orders", "schema_name": "public"},
    ])
    connector.get_columns = AsyncMock(return_value=[
        {"column_name": "id", "data_type": "integer", "nullable": False, "is_primary_key": True},
        {"column_name": "name", "data_type": "varchar", "nullable": True, "is_primary_key": False},
    ])
    connector.get_row_count = AsyncMock(return_value=100)
    return connector


class TestMetadataEngineInit:
    def test_init(self, mock_db):
        engine = MetadataEngine(mock_db)
        assert engine.db == mock_db


class TestScanSource:
    @pytest.mark.asyncio
    async def test_scan_source_basic(self, mock_db, mock_source, mock_connector):
        with patch("app.services.metadata_engine.get_connector", return_value=mock_connector):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            engine = MetadataEngine(mock_db)
            result = await engine.scan_source(mock_source)

            assert result["source_id"] == mock_source.id
            assert result["tables_scanned"] == 2
            assert result["columns_scanned"] == 4
            assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_scan_source_with_row_count(self, mock_db, mock_source, mock_connector):
        with patch("app.services.metadata_engine.get_connector", return_value=mock_connector):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            engine = MetadataEngine(mock_db)
            result = await engine.scan_source(mock_source, include_row_count=True)

            assert mock_connector.get_row_count.called
            assert result["tables_scanned"] == 2

    @pytest.mark.asyncio
    async def test_scan_source_with_table_filter(self, mock_db, mock_source, mock_connector):
        with patch("app.services.metadata_engine.get_connector", return_value=mock_connector):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            engine = MetadataEngine(mock_db)
            result = await engine.scan_source(mock_source, table_filter="users")

            assert result["tables_scanned"] == 1

    @pytest.mark.asyncio
    async def test_scan_source_updates_existing_table(self, mock_db, mock_source):
        # Single-table connector for this test
        single_table_connector = AsyncMock()
        single_table_connector.get_tables = AsyncMock(return_value=[
            {"table_name": "users", "schema_name": "public"},
        ])
        single_table_connector.get_columns = AsyncMock(return_value=[
            {"column_name": "id", "data_type": "integer"},
        ])

        with patch("app.services.metadata_engine.get_connector", return_value=single_table_connector):
            existing_table = MagicMock(spec=MetadataTable)
            existing_table.id = uuid.uuid4()
            existing_table.version = 1
            existing_table.table_name = "users"
            existing_table.schema_name = "public"
            existing_table.description = None
            existing_table.tags = None

            call_count = [0]

            def execute_side_effect(query):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = existing_table
                else:
                    result.scalars.return_value = iter([])
                return result

            mock_db.execute = AsyncMock(side_effect=execute_side_effect)

            engine = MetadataEngine(mock_db)
            await engine.scan_source(mock_source)

            # Version should be incremented (1 -> 2)
            assert existing_table.version == 2

    @pytest.mark.asyncio
    async def test_scan_source_error_rollback(self, mock_db, mock_source):
        with patch("app.services.metadata_engine.get_connector") as mock_get_connector:
            mock_get_connector.return_value.get_tables = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            engine = MetadataEngine(mock_db)

            with pytest.raises(RuntimeError, match="Metadata scan failed"):
                await engine.scan_source(mock_source)

            mock_db.rollback.assert_called_once()


class TestGetTableMetadata:
    @pytest.mark.asyncio
    async def test_get_table_metadata_found(self, mock_db):
        expected_table = MagicMock(spec=MetadataTable)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_table
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        source_id = uuid.uuid4()
        result = await engine.get_table_metadata(source_id, "users")

        assert result == expected_table

    @pytest.mark.asyncio
    async def test_get_table_metadata_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        source_id = uuid.uuid4()
        result = await engine.get_table_metadata(source_id, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_table_metadata_with_schema(self, mock_db):
        expected_table = MagicMock(spec=MetadataTable)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_table
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        source_id = uuid.uuid4()
        result = await engine.get_table_metadata(source_id, "users", schema_name="public")

        assert result == expected_table
        mock_db.execute.assert_called_once()


class TestUpdateColumnMetadata:
    @pytest.mark.asyncio
    async def test_update_column_metadata_success(self, mock_db):
        column = MagicMock(spec=MetadataColumn)
        column.description = None
        column.tags = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = column
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        column_id = uuid.uuid4()
        result = await engine.update_column_metadata(
            column_id,
            {"description": "User ID", "tags": ["primary"]}
        )

        assert result == column
        assert column.description == "User ID"
        assert column.tags == ["primary"]
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_column_metadata_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        column_id = uuid.uuid4()
        result = await engine.update_column_metadata(column_id, {"description": "Test"})

        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_column_metadata_ignores_invalid_keys(self, mock_db):
        column = MagicMock(spec=MetadataColumn)
        column.description = None

        def hasattr_side_effect(obj, name):
            return name in ["description", "tags"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = column
        mock_db.execute.return_value = mock_result

        engine = MetadataEngine(mock_db)
        column_id = uuid.uuid4()

        with patch("builtins.hasattr", side_effect=hasattr_side_effect):
            result = await engine.update_column_metadata(
                column_id,
                {"description": "Valid", "invalid_field": "ignored"}
            )

        assert result == column
