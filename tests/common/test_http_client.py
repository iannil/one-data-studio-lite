"""Unit tests for http_client module

Tests for services/common/http_client.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.http_client import (
    ServiceClient,
    create_cube_studio_client,
    create_datahub_client,
    create_dolphinscheduler_client,
    create_seatunnel_client,
    create_superset_client,
)


class TestServiceClient:
    """测试ServiceClient类"""

    def test_init_default(self):
        """测试默认初始化"""
        client = ServiceClient("http://localhost:8080")
        assert client.base_url == "http://localhost:8080"
        assert client.timeout == 30.0
        assert client.token is None

    def test_init_with_token(self):
        """测试带token初始化"""
        client = ServiceClient("http://localhost:8080", token="test-token")
        assert client.token == "test-token"

    def test_init_trailing_slash_removed(self):
        """测试移除尾部斜杠"""
        client = ServiceClient("http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"

    def test_headers_default(self):
        """测试默认请求头"""
        client = ServiceClient("http://localhost:8080")
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_headers_with_token(self):
        """测试带token的请求头"""
        client = ServiceClient("http://localhost:8080", token="test-token")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-token"

    def test_headers_with_extra(self):
        """测试带额外请求头"""
        client = ServiceClient("http://localhost:8080")
        headers = client._headers({"X-Custom": "value"})
        assert headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_get_success(self):
        """测试GET请求成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.get("/test")

            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_get_with_params(self):
        """测试GET请求带参数"""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.get("/test", params={"page": 1})

            assert result == []

    @pytest.mark.asyncio
    async def test_post_success(self):
        """测试POST请求成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.post("/create", data={"name": "test"})

            assert result["id"] == 123

    @pytest.mark.asyncio
    async def test_put_success(self):
        """测试PUT请求成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.put.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.put("/update/123", data={"name": "updated"})

            assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """测试DELETE请求成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.delete("/delete/123")

            assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_not_200(self):
        """测试健康检查返回非200状态码"""
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.common.http_client.httpx.AsyncClient', return_value=mock_client):
            client = ServiceClient("http://localhost:8080")
            result = await client.health_check()

            assert result is False


class TestClientFactories:
    """测试服务客户端工厂函数"""

    def test_create_cube_studio_client(self):
        """测试创建Cube Studio客户端"""
        client = create_cube_studio_client()
        assert client.base_url == "http://localhost:30080"
        assert client.timeout == 30.0

    def test_create_cube_studio_client_custom_url(self):
        """测试创建Cube Studio客户端（自定义URL）"""
        client = create_cube_studio_client("http://custom:30080")
        assert client.base_url == "http://custom:30080"

    def test_create_superset_client(self):
        """测试创建Superset客户端"""
        client = create_superset_client()
        assert client.base_url == "http://localhost:8088"

    def test_create_datahub_client(self):
        """测试创建DataHub客户端"""
        client = create_datahub_client()
        assert client.base_url == "http://localhost:8081"

    def test_create_dolphinscheduler_client(self):
        """测试创建DolphinScheduler客户端"""
        client = create_dolphinscheduler_client()
        assert client.base_url == "http://localhost:12345"

    def test_create_seatunnel_client(self):
        """测试创建SeaTunnel客户端"""
        client = create_seatunnel_client()
        assert client.base_url == "http://localhost:5801"
