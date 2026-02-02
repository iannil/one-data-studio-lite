"""Unit tests for portal data_api router

Tests for services/portal/routers/data_api.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
import httpx

from services.portal.routers.data_api import (
    router,
    search_assets_v1,
    get_asset_detail_v1,
    get_dataset_schema_v1,
    query_dataset_v1,
    subscribe_dataset_v1,
    get_subscriptions_v1,
    data_api_proxy,
    QueryDatasetRequest,
)
from services.common.auth import TokenPayload
from services.common.api_response import ErrorCode


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/data-api"


class TestQueryDatasetRequest:
    """测试请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = QueryDatasetRequest()
        assert req.sql is None
        assert req.limit == 100

    def test_with_values(self):
        """测试带值的请求"""
        req = QueryDatasetRequest(sql="SELECT * FROM table", limit=50)
        assert req.sql == "SELECT * FROM table"
        assert req.limit == 50


class TestSearchAssetsV1:
    """测试搜索数据资产"""

    @pytest.mark.asyncio
    async def test_search_assets_success(self):
        """测试成功搜索资产"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets": [
                {"id": "1", "name": "Dataset 1"},
                {"id": "2", "name": "Dataset 2"}
            ],
            "total": 2
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await search_assets_v1(
                keyword="test",
                type="table",
                page=1,
                page_size=20,
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS
            assert "assets" in result.data

    @pytest.mark.asyncio
    async def test_search_assets_service_error(self):
        """测试服务错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await search_assets_v1(user=mock_user)

            assert result.code == ErrorCode.EXTERNAL_SERVICE_ERROR

    @pytest.mark.asyncio
    async def test_search_assets_exception(self):
        """测试异常情况"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        class MockClient:
            async def __aenter__(self):
                raise ConnectionError("Service unavailable")

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.data_api.httpx.AsyncClient', return_value=MockClient()):
            result = await search_assets_v1(user=mock_user)

            assert result.code == ErrorCode.EXTERNAL_SERVICE_ERROR


class TestGetAssetDetailV1:
    """测试获取资产详情"""

    @pytest.mark.asyncio
    async def test_get_asset_detail_success(self):
        """测试成功获取资产详情"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "asset-123",
            "name": "Test Asset",
            "type": "table"
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_asset_detail_v1(asset_id="asset-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["id"] == "asset-123"

    @pytest.mark.asyncio
    async def test_get_asset_detail_not_found(self):
        """测试资产不存在"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_asset_detail_v1(asset_id="nonexistent", user=mock_user)

            assert result.code == ErrorCode.EXTERNAL_SERVICE_ERROR


class TestGetDatasetSchemaV1:
    """测试获取数据集 Schema"""

    @pytest.mark.asyncio
    async def test_get_dataset_schema_success(self):
        """测试成功获取 Schema"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "dataset_id": "dataset-123",
            "columns": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "varchar"}
            ]
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_dataset_schema_v1(dataset_id="dataset-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "columns" in result.data


class TestQueryDatasetV1:
    """测试自定义查询"""

    @pytest.mark.asyncio
    async def test_query_dataset_success(self):
        """测试成功查询"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rows": [
                {"id": 1, "name": "Row 1"},
                {"id": 2, "name": "Row 2"}
            ],
            "total": 2
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = QueryDatasetRequest(sql="SELECT * FROM table", limit=10)
            result = await query_dataset_v1(
                dataset_id="dataset-123",
                request=req,
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS
            assert "rows" in result.data

    @pytest.mark.asyncio
    async def test_query_dataset_with_default_limit(self):
        """测试使用默认 limit"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rows": [], "total": 0}

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = QueryDatasetRequest()
            result = await query_dataset_v1(
                dataset_id="dataset-123",
                request=req,
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS


class TestSubscribeDatasetV1:
    """测试订阅数据集"""

    @pytest.mark.asyncio
    async def test_subscribe_dataset_success(self):
        """测试成功订阅"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "dataset_id": "dataset-123",
            "subscribed": True
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await subscribe_dataset_v1(dataset_id="dataset-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["subscribed"] is True


class TestGetSubscriptionsV1:
    """测试获取订阅列表"""

    @pytest.mark.asyncio
    async def test_get_subscriptions_success(self):
        """测试成功获取订阅列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subscriptions": [
                {"dataset_id": "dataset-1", "name": "Dataset 1"},
                {"dataset_id": "dataset-2", "name": "Dataset 2"}
            ],
            "total": 2
        }

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_subscriptions_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "subscriptions" in result.data

    @pytest.mark.asyncio
    async def test_get_subscriptions_empty(self):
        """测试空订阅列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"subscriptions": [], "total": 0}

        with patch('services.portal.routers.data_api.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_subscriptions_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["total"] == 0
