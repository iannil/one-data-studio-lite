"""Unit tests for portal proxy router

Tests for services/portal/routers/proxy.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import TimeoutException, ConnectError, HTTPError as HTTPXError

from services.portal.routers.proxy import (
    proxy_request,
    SERVICE_SECRET,
    HOP_BY_HOP_HEADERS,
)


class TestConstants:
    """测试常量"""

    def test_service_secret_exists(self):
        """测试服务密钥存在"""
        assert SERVICE_SECRET is not None

    def test_hop_by_hop_headers_not_empty(self):
        """测试 hop-by-hop 头列表不为空"""
        assert len(HOP_BY_HOP_HEADERS) > 0

    def test_hop_by_hop_headers_contains_expected(self):
        """测试包含预期的 hop-by-hop 头"""
        assert "connection" in HOP_BY_HOP_HEADERS
        assert "content-length" in HOP_BY_HOP_HEADERS
        assert "transfer-encoding" in HOP_BY_HOP_HEADERS


class TestProxyRequest:
    """测试代理请求函数"""

    @pytest.mark.asyncio
    async def test_proxy_request_get_success(self):
        """测试 GET 请求成功"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "ok"}'
        mock_response.headers = {"content-type": "application/json"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test"
            )

            assert result.status_code == 200
            assert result.body == b'{"result": "ok"}'

    @pytest.mark.asyncio
    async def test_proxy_request_with_authorization(self):
        """测试带 Authorization 头的请求"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {"authorization": "Bearer test_token"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test"
            )

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_proxy_request_with_content_type(self):
        """测试带 Content-Type 头的请求"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"key": "value"}')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"created": true}'
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/create"
            )

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_proxy_request_with_extra_headers(self):
        """测试带额外头的请求"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test",
                extra_headers={"X-Custom-Header": "custom_value"}
            )

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_proxy_request_with_query_params(self):
        """测试带查询参数的请求"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {"key": "value", "page": "1"}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test"
            )

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_proxy_request_timeout(self):
        """测试请求超时"""
        from fastapi import Request, HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(side_effect=TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await proxy_request(
                    mock_request,
                    "http://example.com",
                    "/api/test"
                )

            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_proxy_request_connect_error(self):
        """测试连接错误"""
        from fastapi import Request, HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(side_effect=ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await proxy_request(
                    mock_request,
                    "http://example.com",
                    "/api/test"
                )

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_proxy_request_http_error(self):
        """测试 HTTP 错误"""
        from fastapi import Request, HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(side_effect=HTTPXError("HTTP error"))
            mock_client_class.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await proxy_request(
                    mock_request,
                    "http://example.com",
                    "/api/test"
                )

            assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_proxy_request_filters_hop_by_hop_headers(self):
        """测试过滤 hop-by-hop 响应头"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {
            "content-type": "application/json",
            "content-encoding": "gzip",
            "connection": "keep-alive",
            "transfer-encoding": "chunked",
            "x-custom-header": "custom"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test"
            )

            # Check that hop-by-hop headers are filtered (content-length is auto-added by Starlette)
            assert "content-encoding" not in result.headers
            assert "connection" not in result.headers
            assert "transfer-encoding" not in result.headers
            # Check that custom header is preserved
            assert result.headers.get("x-custom-header") == "custom"

    @pytest.mark.asyncio
    async def test_proxy_request_custom_timeout(self):
        """测试自定义超时"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/test",
                timeout=60.0
            )

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_proxy_request_url_construction(self):
        """测试 URL 构建正确"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"ok"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # Test with trailing slash in base URL and leading slash in path
            await proxy_request(
                mock_request,
                "http://example.com/",
                "/api/test"
            )

            # Test without trailing/leading slashes
            await proxy_request(
                mock_request,
                "http://example.com",
                "api/test"
            )

    @pytest.mark.asyncio
    async def test_proxy_request_post_with_body(self):
        """测试 POST 请求带 body"""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"name": "test"}')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"created": true}'
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await proxy_request(
                mock_request,
                "http://example.com",
                "/api/create"
            )

            assert result.status_code == 201
