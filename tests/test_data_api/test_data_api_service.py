"""Unit tests for data_api service main module

Tests for services/data_api/main.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from services.data_api.main import (
    app,
    get_current_user,
)
from services.common.auth import TokenPayload


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
    """测试健康检查"""

    def test_health_check(self):
        """测试健康检查端点"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-api"


class TestQueryDataset:
    """测试查询数据集端点"""

    @pytest.mark.asyncio
    async def test_query_dataset_success(self):
        """测试成功查询数据集"""
        mock_db = AsyncMock()

        # Mock validate_table_exists
        with patch('services.data_api.main.validate_table_exists', return_value="`test_dataset`"):
            # Mock query result
            mock_result = MagicMock()
            mock_result.keys.return_value = ["id", "name"]
            mock_result.fetchall.return_value = [
                (1, "Alice"),
                (2, "Bob"),
            ]
            mock_db.execute.return_value = mock_result

            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/data/test-dataset?page=1&page_size=10")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["dataset_id"] == "test-dataset"
                    assert "total" in result
                    assert "data" in result
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_dataset_not_found(self):
        """测试数据集不存在"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', side_effect=ValueError("Table not found")):
            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/data/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestGetDatasetSchema:
    """测试获取数据集Schema端点"""

    @pytest.mark.asyncio
    async def test_get_schema_sqlite(self):
        """测试SQLite获取Schema"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', return_value="`test_dataset`"):
            # Mock sqlite_version check
            version_result = MagicMock()
            version_result.fetchone.return_value = "3.40.0"

            # Mock PRAGMA result
            pragma_result = MagicMock()
            pragma_result.fetchall.return_value = [
                (0, "id", "INTEGER", 1, None, 1),
                (1, "name", "TEXT", 0, None, 0),
            ]

            # Mock count result
            count_result = MagicMock()
            count_result.scalar.return_value = 100

            call_count = [0]

            async def mock_execute_fn(sql, params=None):
                call_count[0] += 1
                if "sqlite_version" in str(sql):
                    return version_result
                elif "PRAGMA" in str(sql):
                    return pragma_result
                else:
                    return count_result

            mock_db.execute = AsyncMock(side_effect=mock_execute_fn)

            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/data/test-dataset/schema")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["dataset_id"] == "test-dataset"
                    assert "columns" in result
                    # Verify columns have expected properties
                    assert "name" in result["columns"][0]
                    assert "data_type" in result["columns"][0]
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_schema_not_found(self):
        """测试数据集不存在"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', side_effect=ValueError("Table not found")):
            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/data/nonexistent/schema")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestCustomQuery:
    """测试自定义查询端点"""

    @pytest.mark.asyncio
    async def test_custom_query_with_sql(self):
        """测试带SQL的自定义查询"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', return_value="`test_dataset`"):
            mock_result = MagicMock()
            mock_result.keys.return_value = ["id", "name"]
            mock_result.fetchall.return_value = [(1, "Alice")]
            mock_db.execute.return_value = mock_result

            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/data/test-dataset/query",
                        json={"sql": "SELECT * FROM test_dataset LIMIT 10"}
                    )

                    assert response.status_code == 200
                    result = response.json()
                    assert "data" in result
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_custom_query_non_select(self):
        """测试非SELECT查询被拒绝"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', return_value="`test_dataset`"):
            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/data/test-dataset/query",
                        json={"sql": "DROP TABLE test_dataset"}
                    )

                    assert response.status_code == 400
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_custom_query_with_dangerous_keyword(self):
        """测试包含危险关键词被拒绝"""
        mock_db = AsyncMock()

        with patch('services.data_api.main.validate_table_exists', return_value="`test_dataset`"):
            with patch('services.data_api.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/data/test-dataset/query",
                        json={"sql": "SELECT * FROM users WHERE 1=1; DROP TABLE users"}
                    )

                    assert response.status_code == 400
                finally:
                    app.dependency_overrides.clear()


class TestSearchAssets:
    """测试搜索资产端点"""

    @pytest.mark.asyncio
    async def test_search_assets_success(self):
        """测试成功搜索资产"""
        with patch('services.data_api.main.datahub_client') as mock_client:
            mock_client.post = AsyncMock(return_value={
                "value": {
                    "entities": ["entity1", "entity2"],
                    "numEntities": 2
                }
            })

            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/assets/search?query=test&page=1&page_size=20")

                assert response.status_code == 200
                result = response.json()
                assert "total" in result
                assert "assets" in result
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_search_assets_error(self):
        """测试搜索失败时返回空结果"""
        with patch('services.data_api.main.datahub_client') as mock_client:
            mock_client.post = AsyncMock(side_effect=Exception("DataHub unavailable"))

            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/assets/search?query=test")

                assert response.status_code == 200
                result = response.json()
                assert result["total"] == 0
                assert result["assets"] == []
            finally:
                app.dependency_overrides.clear()


class TestGetAsset:
    """测试获取资产详情端点"""

    @pytest.mark.asyncio
    async def test_get_asset_success(self):
        """测试成功获取资产"""
        with patch('services.data_api.main.datahub_client') as mock_client:
            mock_client.get = AsyncMock(return_value={
                "name": "test_dataset",
                "description": "Test dataset"
            })

            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/assets/test-asset-id")

                assert response.status_code == 200
                result = response.json()
                assert result["asset_id"] == "test-asset-id"
                assert result["name"] == "test_dataset"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self):
        """测试资产不存在"""
        with patch('services.data_api.main.datahub_client') as mock_client:
            mock_client.get = AsyncMock(side_effect=Exception("Not found"))

            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/assets/nonexistent")

                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()


class TestSubscribeAsset:
    """测试订阅资产端点"""

    @pytest.mark.asyncio
    async def test_subscribe_asset(self):
        """测试订阅资产"""
        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            # The endpoint sets asset_id and subscriber, but Pydantic requires them in the body
            response = client.post(
                "/api/assets/test-asset-id/subscribe",
                json={"asset_id": "ignored", "subscriber": "ignored"}  # Values will be overridden
            )

            assert response.status_code == 200
            result = response.json()
            assert result["asset_id"] == "test-asset-id"
            assert result["subscriber"] == "test"
        finally:
            app.dependency_overrides.clear()
