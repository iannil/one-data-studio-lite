"""Unit tests for portal audit router

Tests for services/portal/routers/audit.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.audit import (
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
        assert router.prefix == "/api/proxy/audit"


class TestGetLogsV1:
    """测试 v1 获取日志端点"""

    @pytest.mark.asyncio
    async def test_get_logs_v1_success(self):
        """测试获取日志成功"""
        from services.portal.routers.audit import get_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "logs": [
                {"id": "1", "user": "admin", "action": "login"}
            ],
            "total": 1
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
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_logs_v1(
                subsystem="portal",
                event_type="login",
                user="admin",
                page=1,
                page_size=50,
                user_info=mock_payload
            )

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_get_logs_v1_default_params(self):
        """测试默认参数"""
        from services.portal.routers.audit import get_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"logs": [], "total": 0}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_logs_v1(user_info=mock_payload)

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_logs_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.audit import get_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_logs_v1(user_info=mock_payload)

            assert result.code != 20000
            assert "审计日志服务错误" in result.message

    @pytest.mark.asyncio
    async def test_get_logs_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.audit import get_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_logs_v1(user_info=mock_payload)

            assert result.code != 20000
            assert "审计日志服务异常" in result.message


class TestGetLogV1:
    """测试 v1 获取单条日志端点"""

    @pytest.mark.asyncio
    async def test_get_log_v1_success(self):
        """测试获取单条日志成功"""
        from services.portal.routers.audit import get_log_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "user": "admin",
            "action": "login",
            "timestamp": "2024-01-01T00:00:00"
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
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_log_v1("123", mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_get_log_v1_not_found(self):
        """测试日志不存在"""
        from services.portal.routers.audit import get_log_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_log_v1("999", mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_get_log_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.audit import get_log_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_log_v1("123", mock_payload)

            assert result.code != 20000
            assert "审计日志服务异常" in result.message


class TestGetStatsV1:
    """测试 v1 获取统计端点"""

    @pytest.mark.asyncio
    async def test_get_stats_v1_success(self):
        """测试获取统计成功"""
        from services.portal.routers.audit import get_stats_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_logs": 1000,
            "today_logs": 50,
            "by_event_type": {
                "login": 20,
                "logout": 15,
                "create": 10
            }
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
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_stats_v1(mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_get_stats_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.audit import get_stats_v1
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
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_stats_v1(mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_get_stats_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.audit import get_stats_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_stats_v1(mock_payload)

            assert result.code != 20000
            assert "审计日志服务异常" in result.message


class TestExportLogsV1:
    """测试 v1 导出日志端点"""

    @pytest.mark.asyncio
    async def test_export_logs_v1_success(self):
        """测试导出日志成功"""
        from services.portal.routers.audit import export_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "export_id": "exp_123",
            "status": "processing",
            "format": "csv"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await export_logs_v1(
                format="csv",
                subsystem="portal",
                event_type="login",
                user="admin",
                user_info=mock_payload
            )

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_export_logs_v1_default_params(self):
        """测试默认参数导出"""
        from services.portal.routers.audit import export_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"export_id": "exp_456"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await export_logs_v1(user_info=mock_payload)

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_export_logs_v1_service_error(self):
        """测试服务返回错误"""
        from services.portal.routers.audit import export_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await export_logs_v1(user_info=mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_export_logs_v1_exception(self):
        """测试异常处理"""
        from services.portal.routers.audit import export_logs_v1
        from services.common.auth import TokenPayload
        from datetime import datetime
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("HTTP error"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await export_logs_v1(user_info=mock_payload)

            assert result.code != 20000
            assert "审计日志服务异常" in result.message


class TestAuditProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_audit_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.audit import audit_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.audit.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"logs": []}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await audit_proxy("api/logs", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_proxy_post(self):
        """测试 POST 代理"""
        from services.portal.routers.audit import audit_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"query": "test"}')

        with patch('services.portal.routers.audit.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"result": "ok"}', status_code=201)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await audit_proxy("api/export", mock_request, mock_payload)

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_audit_proxy_put(self):
        """测试 PUT 代理"""
        from services.portal.routers.audit import audit_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "PUT"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "updated"}')

        with patch('services.portal.routers.audit.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"updated": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await audit_proxy("api/update/1", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_proxy_delete(self):
        """测试 DELETE 代理"""
        from services.portal.routers.audit import audit_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.audit.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"deleted": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await audit_proxy("api/logs/123", mock_request, mock_payload)

            assert result.status_code == 200
