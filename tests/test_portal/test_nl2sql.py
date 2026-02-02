"""Unit tests for portal nl2sql router

Tests for services/portal/routers/nl2sql.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.nl2sql import (
    QueryRequest,
    ExplainRequest,
    SERVICE_SECRET,
    router,
)


class TestConstants:
    """测试常量"""

    def test_service_secret_exists(self):
        """测试服务密钥存在"""
        assert SERVICE_SECRET is not None

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/nl2sql"


class TestQueryRequest:
    """测试查询请求模型"""

    def test_query_request_with_query_only(self):
        """测试仅包含查询的请求"""
        req = QueryRequest(query="SELECT * FROM users")
        assert req.query == "SELECT * FROM users"
        assert req.database is None
        assert req.context is None

    def test_query_request_with_all_fields(self):
        """测试包含所有字段的请求"""
        req = QueryRequest(
            query="Find all active users",
            database="mydb",
            context="Looking for users created in last 30 days"
        )
        assert req.query == "Find all active users"
        assert req.database == "mydb"
        assert req.context == "Looking for users created in last 30 days"


class TestExplainRequest:
    """测试解释请求模型"""

    def test_explain_request_with_sql_only(self):
        """测试仅包含 SQL 的请求"""
        req = ExplainRequest(sql="SELECT * FROM users WHERE id = 1")
        assert req.sql == "SELECT * FROM users WHERE id = 1"
        assert req.database is None

    def test_explain_request_with_database(self):
        """测试包含数据库的请求"""
        req = ExplainRequest(
            sql="SELECT COUNT(*) FROM orders",
            database="analytics"
        )
        assert req.sql == "SELECT COUNT(*) FROM orders"
        assert req.database == "analytics"


class TestQueryV1:
    """测试 v1 查询端点"""

    @pytest.mark.asyncio
    async def test_query_v1_success(self):
        """测试查询成功"""
        from services.portal.routers.nl2sql import query_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sql": "SELECT * FROM users", "result": []}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = QueryRequest(query="Find all users")
            result = await query_v1(request, mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_query_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.nl2sql import query_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = QueryRequest(query="Find all users")
            result = await query_v1(request, mock_payload)

            assert result.code != 20000
            assert "NL2SQL 服务错误" in result.message

    @pytest.mark.asyncio
    async def test_query_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.nl2sql import query_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = QueryRequest(query="Find all users")
            result = await query_v1(request, mock_payload)

            assert result.code != 20000
            assert "NL2SQL 服务异常" in result.message


class TestExplainV1:
    """测试 v1 解释端点"""

    @pytest.mark.asyncio
    async def test_explain_v1_success(self):
        """测试解释成功"""
        from services.portal.routers.nl2sql import explain_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"explanation": "Selects all columns from users table"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = ExplainRequest(sql="SELECT * FROM users")
            result = await explain_v1(request, mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_explain_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.nl2sql import explain_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = ExplainRequest(sql="INVALID SQL")
            result = await explain_v1(request, mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_explain_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.nl2sql import explain_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = ExplainRequest(sql="SELECT * FROM users")
            result = await explain_v1(request, mock_payload)

            assert result.code != 20000
            assert "NL2SQL 服务异常" in result.message


class TestGetTablesV1:
    """测试 v1 获取表列表端点"""

    @pytest.mark.asyncio
    async def test_get_tables_v1_success(self):
        """测试获取表列表成功"""
        from services.portal.routers.nl2sql import get_tables_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tables": ["users", "orders", "products"]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_tables_v1(mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_get_tables_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.nl2sql import get_tables_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_tables_v1(mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_get_tables_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.nl2sql import get_tables_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_tables_v1(mock_payload)

            assert result.code != 20000
            assert "NL2SQL 服务异常" in result.message


class TestNL2SQLProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_nl2sql_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.nl2sql import nl2sql_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "ok"}'
        mock_response.headers = {}

        with patch('services.portal.routers.nl2sql.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"status": "ok"}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await nl2sql_proxy("api/test", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_nl2sql_proxy_post(self):
        """测试 POST 代理"""
        from services.portal.routers.nl2sql import nl2sql_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"query": "test"}')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"created": true}'
        mock_response.headers = {}

        with patch('services.portal.routers.nl2sql.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"created": true}', status_code=201)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await nl2sql_proxy("api/query", mock_request, mock_payload)

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_nl2sql_proxy_put(self):
        """测试 PUT 代理"""
        from services.portal.routers.nl2sql import nl2sql_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "PUT"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "updated"}')

        with patch('services.portal.routers.nl2sql.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"updated": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await nl2sql_proxy("api/update/1", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_nl2sql_proxy_delete(self):
        """测试 DELETE 代理"""
        from services.portal.routers.nl2sql import nl2sql_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.nl2sql.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"deleted": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="user",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await nl2sql_proxy("api/delete/1", mock_request, mock_payload)

            assert result.status_code == 200
