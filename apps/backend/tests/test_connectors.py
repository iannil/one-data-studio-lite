from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from app.connectors.database import DatabaseConnector
from app.connectors.file import FileConnector


class TestDatabaseConnector:
    @pytest.fixture
    def db_config(self):
        return {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
        }

    def test_init_builds_engine(self, db_config):
        with patch("app.connectors.database.create_engine") as mock_engine:
            connector = DatabaseConnector(db_config)
            mock_engine.assert_called_once()
            assert connector.config == db_config

    @pytest.mark.asyncio
    async def test_test_connection_success(self, db_config):
        with patch("app.connectors.database.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__ = MagicMock(
                return_value=mock_conn
            )
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock(
                return_value=False
            )

            connector = DatabaseConnector(db_config)
            success, message = await connector.test_connection()

            assert success is True
            assert "successful" in message.lower()

    @pytest.mark.asyncio
    async def test_get_tables(self, db_config):
        with patch("app.connectors.database.create_engine"):
            with patch("app.connectors.database.inspect") as mock_inspect:
                mock_inspector = MagicMock()
                mock_inspector.get_schema_names.return_value = ["public"]
                mock_inspector.get_table_names.return_value = ["users", "orders"]
                mock_inspector.get_view_names.return_value = []
                mock_inspect.return_value = mock_inspector

                connector = DatabaseConnector(db_config)
                tables = await connector.get_tables()

                assert len(tables) == 2
                assert tables[0]["table_name"] == "users"
                assert tables[1]["table_name"] == "orders"


class TestFileConnector:
    @pytest.fixture
    def csv_config(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n")
        return {"file_path": str(csv_file), "file_type": "csv"}

    @pytest.mark.asyncio
    async def test_test_connection_success(self, csv_config):
        connector = FileConnector(csv_config)
        success, message = await connector.test_connection()
        assert success is True

    @pytest.mark.asyncio
    async def test_test_connection_file_not_found(self):
        connector = FileConnector({"file_path": "/nonexistent/file.csv"})
        success, message = await connector.test_connection()
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_get_tables_csv(self, csv_config):
        connector = FileConnector(csv_config)
        tables = await connector.get_tables()
        assert len(tables) == 1
        assert tables[0]["table_name"] == "test"

    @pytest.mark.asyncio
    async def test_get_columns_csv(self, csv_config):
        connector = FileConnector(csv_config)
        columns = await connector.get_columns("test")
        assert len(columns) == 3
        column_names = [c["column_name"] for c in columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "value" in column_names

    @pytest.mark.asyncio
    async def test_read_data_csv(self, csv_config):
        connector = FileConnector(csv_config)
        df = await connector.read_data()
        assert len(df) == 2
        assert list(df.columns) == ["id", "name", "value"]

    @pytest.mark.asyncio
    async def test_read_data_with_limit(self, csv_config):
        connector = FileConnector(csv_config)
        df = await connector.read_data(limit=1)
        assert len(df) == 1

    @pytest.mark.asyncio
    async def test_get_row_count(self, csv_config):
        connector = FileConnector(csv_config)
        count = await connector.get_row_count("test")
        assert count == 2

    @pytest.mark.asyncio
    async def test_excel_file(self, tmp_path):
        excel_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        df.to_excel(excel_file, index=False)

        connector = FileConnector({"file_path": str(excel_file), "file_type": "xlsx"})
        result = await connector.read_data()
        # read_excel with sheet_name=None returns dict of sheets
        if isinstance(result, dict):
            sheet_df = list(result.values())[0]
            assert len(sheet_df) == 2
        else:
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_json_file(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]')

        connector = FileConnector({"file_path": str(json_file), "file_type": "json"})
        result = await connector.read_data()
        assert len(result) == 2
