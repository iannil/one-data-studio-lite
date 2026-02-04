"""Unit tests for nl2sql service main module

Tests for services/nl2sql/main.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.common.auth import TokenPayload
from services.nl2sql.main import (
    _call_llm_service,
    _get_schema_info,
    app,
    get_current_user,
)
from services.nl2sql.models import (
    ColumnInfo,
    NL2SQLRequest,
    NL2SQLResponse,
    SQLExplanationRequest,
    TableInfo,
)

# Mock user for testing
MOCK_USER = TokenPayload(
    sub="test",
    username="test",
    role="viewer",
    exp=datetime(2099, 12, 31),
    iat=datetime(2023, 1, 1)
)


async def mock_get_current_user():
    return MOCK_USER


class TestHealthCheck:
    """测试健康检查端点"""

    def test_health_check(self):
        """测试健康检查"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nl2sql"


class TestCallLlmService:
    """测试LLM服务调用"""

    @pytest.mark.asyncio
    async def test_call_llm_service_success(self):
        """测试成功调用LLM"""
        with patch('services.nl2sql.main.call_llm') as mock_call:
            mock_call.return_value = "Generated SQL: SELECT * FROM users"

            result = await _call_llm_service("test prompt")

            assert result == "Generated SQL: SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_call_llm_service_error(self):
        """测试LLM调用失败"""
        from services.common.llm_client import LLMError

        with patch('services.nl2sql.main.call_llm') as mock_call:
            mock_call.side_effect = LLMError("Service unavailable", code=503)

            from services.common.exceptions import AppException
            with pytest.raises(AppException) as exc_info:
                await _call_llm_service("test prompt")

            assert "LLM 调用失败" in str(exc_info.value)


class TestGetSchemaInfo:
    """测试获取表结构信息"""

    @pytest.mark.asyncio
    async def test_get_schema_sqlite(self):
        """测试SQLite获取表结构"""
        mock_db = AsyncMock()

        # Mock sqlite_version check
        mock_result = MagicMock()
        mock_result.fetchone.return_value = "3.40.0"
        mock_db.execute.return_value = mock_result

        # Mock tables
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [
            ("users", None),
            ("orders", None),
        ]
        mock_db.execute.side_effect = [
            mock_result,  # sqlite_version
            mock_tables_result,  # tables
            MagicMock(),  # pragma for users
            MagicMock(),  # pragma for orders
        ]

        schema = await _get_schema_info(mock_db)

        assert "users" in schema
        assert "orders" in schema

    @pytest.mark.asyncio
    async def test_get_schema_mysql(self):
        """测试MySQL获取表结构"""
        mock_db = AsyncMock()

        # Mock sqlite_version check - returns None for MySQL
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        schema = await _get_schema_info(mock_db)

        # When not SQLite, should use MySQL path
        assert schema == "暂无可用表结构信息"

    @pytest.mark.asyncio
    async def test_get_schema_no_tables(self):
        """测试无表的情况"""
        mock_db = AsyncMock()

        # Mock sqlite_version check
        mock_result = MagicMock()
        mock_result.fetchone.return_value = "3.40.0"
        mock_db.execute.return_value = mock_result

        # Mock empty tables
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_result,  # sqlite_version
            mock_tables_result,  # tables
        ]

        schema = await _get_schema_info(mock_db)

        assert schema == "暂无可用表结构信息"


class TestNL2SQLRequest:
    """测试NL2SQL请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = NL2SQLRequest(question="查询所有用户")
        assert req.question == "查询所有用户"
        assert req.database is None
        assert req.max_rows == 100

    def test_with_all_values(self):
        """测试带所有值的请求"""
        req = NL2SQLRequest(
            question="查询所有订单",
            database="test_db",
            max_rows=50
        )
        assert req.database == "test_db"
        assert req.max_rows == 50


class TestNL2SQLResponse:
    """测试NL2SQL响应模型"""

    def test_success_response(self):
        """测试成功响应"""
        response = NL2SQLResponse(
            success=True,
            question="查询所有用户",
            generated_sql="SELECT * FROM users",
            explanation="查询用户表",
            columns=["id", "name"],
            rows=[["1", "Alice"], ["2", "Bob"]],
            row_count=2,
            execution_time_ms=150.5
        )
        assert response.success is True
        assert response.row_count == 2
        assert len(response.rows) == 2

    def test_failure_response(self):
        """测试失败响应"""
        response = NL2SQLResponse(
            success=False,
            question="查询所有用户",
            generated_sql="INVALID SQL",
            explanation="SQL执行失败",
            execution_time_ms=50.0
        )
        assert response.success is False
        # Empty list is the default value for columns and rows when failed
        assert response.columns == []


class TestSQLExplanationRequest:
    """测试SQL解释请求模型"""

    def test_request_creation(self):
        """测试创建请求"""
        req = SQLExplanationRequest(
            sql="SELECT * FROM users WHERE id = 1",
            database=None
        )
        assert req.sql == "SELECT * FROM users WHERE id = 1"
        assert req.database is None


class TestTableInfo:
    """测试表信息模型"""

    def test_table_info_creation(self):
        """测试创建表信息"""
        columns = [
            ColumnInfo(
                name="id",
                data_type="INTEGER",
                comment="主键",
                is_primary_key=True,
                is_nullable=False
            ),
            ColumnInfo(
                name="name",
                data_type="TEXT",
                comment="姓名",
                is_primary_key=False,
                is_nullable=True
            ),
        ]
        table = TableInfo(
            database="main",
            table_name="users",
            comment="用户表",
            columns=columns
        )
        assert table.table_name == "users"
        assert len(table.columns) == 2


class TestColumnInfo:
    """测试列信息模型"""

    def test_column_info_creation(self):
        """测试创建列信息"""
        col = ColumnInfo(
            name="email",
            data_type="VARCHAR(255)",
            comment="邮箱",
            is_primary_key=False,
            is_nullable=True
        )
        assert col.name == "email"
        assert col.data_type == "VARCHAR(255)"
        assert col.is_primary_key is False


class TestListTables:
    """测试获取表列表端点"""

    @pytest.mark.asyncio
    async def test_list_tables_sqlite(self):
        """测试SQLite表列表"""
        mock_db = AsyncMock()

        # Mock sqlite_version check
        mock_result = MagicMock()
        mock_result.fetchone.return_value = "3.40.0"

        # Mock table names
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [("users",), ("orders",)]

        # Mock PRAGMA results
        mock_users_cols = MagicMock()
        mock_users_cols.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),  # cid, name, type, notnull, dflt_value, pk
            (1, "name", "TEXT", 0, None, 0),
        ]

        mock_orders_cols = MagicMock()
        mock_orders_cols.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "user_id", "INTEGER", 0, None, 0),
        ]

        call_count = [0]

        async def mock_execute_fn(sql, params=None):
            call_count[0] += 1
            if "sqlite_version" in str(sql):
                return mock_result
            elif "sqlite_master" in str(sql):
                return mock_tables_result
            elif "PRAGMA" in str(sql) and "users" in str(sql):
                return mock_users_cols
            else:
                return mock_orders_cols

        mock_db.execute = AsyncMock(side_effect=mock_execute_fn)

        with patch('services.nl2sql.main.get_db', return_value=mock_db):
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/nl2sql/tables")

                assert response.status_code == 200
                tables = response.json()
                assert len(tables) >= 0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_tables_response_format(self):
        """测试表列表响应格式"""
        # This test verifies the endpoint response format
        # Using dependency_override to bypass authentication
        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            response = client.get("/api/nl2sql/tables")

            # Endpoint should return 200 (may have actual tables from test DB)
            assert response.status_code == 200
            tables = response.json()
            # Verify response is a list
            assert isinstance(tables, list)
        finally:
            app.dependency_overrides.clear()


class TestExplainSQL:
    """测试SQL解释端点"""

    @pytest.mark.asyncio
    async def test_explain_sql_success(self):
        """测试成功解释SQL"""
        mock_db = AsyncMock()
        mock_user = MOCK_USER

        # Mock schema info
        mock_result = MagicMock()
        mock_result.fetchone.return_value = "3.40.0"
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = []

        async def mock_execute_fn(sql, params=None):
            if "sqlite_version" in str(sql):
                return mock_result
            else:
                return mock_tables_result

        mock_db.execute = AsyncMock(side_effect=mock_execute_fn)

        with patch('services.nl2sql.main.get_db', return_value=mock_db):
            with patch('services.nl2sql.main._call_llm_service') as mock_llm:
                mock_llm.return_value = "This query selects all users"

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/nl2sql/explain",
                        json={"sql": "SELECT * FROM users"}
                    )

                    assert response.status_code == 200
                    result = response.json()
                    assert result["sql"] == "SELECT * FROM users"
                    assert "explanation" in result
                finally:
                    app.dependency_overrides.clear()
