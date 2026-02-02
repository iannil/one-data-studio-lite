"""Unit tests for portal superset router

Tests for services/portal/routers/superset.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import asyncio
import time

import pytest

from services.portal.routers.superset import (
    _session_manager,
    SupersetSessionManager,
    _get_superset_session,
    _superset_request,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/superset"


class TestSupersetSessionManagerInit:
    """测试会话管理器初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        sm = SupersetSessionManager()

        assert sm._cookies is None
        assert sm._csrf_token is None
        assert sm._session_expire == 0

    def test_init_has_locks(self):
        """测试初始化锁"""
        sm = SupersetSessionManager()

        assert isinstance(sm._lock, asyncio.Lock)
        assert isinstance(sm._refresh_lock, asyncio.Lock)


class TestIsSessionValid:
    """测试会话有效性检查"""

    def test_is_session_valid_no_session(self):
        """测试无会话"""
        sm = SupersetSessionManager()

        result = sm._is_session_valid()

        assert result is False

    def test_is_session_valid_no_csrf(self):
        """测试无 CSRF token"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}

        result = sm._is_session_valid()

        assert result is False

    def test_is_session_valid_no_cookies(self):
        """测试无 cookies"""
        sm = SupersetSessionManager()
        sm._csrf_token = "test_token"

        result = sm._is_session_valid()

        assert result is False

    def test_is_session_valid_expired(self):
        """测试会话过期"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}
        sm._csrf_token = "test_token"
        sm._session_expire = time.time() - 400  # Expired more than 5 min ago

        result = sm._is_session_valid()

        assert result is False

    def test_is_session_valid(self):
        """测试有效会话"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}
        sm._csrf_token = "test_token"
        sm._session_expire = time.time() + 3600  # Expires in 1 hour

        result = sm._is_session_valid()

        assert result is True


class TestInvalidate:
    """测试使会话失效"""

    def test_invalidate(self):
        """测试使会话失效"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}
        sm._csrf_token = "test_token"
        sm._session_expire = time.time() + 3600

        sm.invalidate()

        assert sm._cookies is None
        assert sm._csrf_token is None
        assert sm._session_expire == 0


class TestExtractCsrfToken:
    """测试 CSRF token 提取"""

    def test_extract_csrf_token_from_input(self):
        """测试从 input 标签提取"""
        sm = SupersetSessionManager()

        html = '<input name="csrf_token" type="hidden" value="test_token_123" />'
        result = sm._extract_csrf_token(html)

        assert result == "test_token_123"

    def test_extract_csrf_token_from_short_pattern(self):
        """测试从简短模式提取"""
        sm = SupersetSessionManager()

        # Note: The regex pattern matches csrf_token attribute, then captures the value attribute
        # For <input csrf_token="token456" value="other" />, it captures "other"
        html = '<input csrf_token="token456" value="captured_value" />'
        result = sm._extract_csrf_token(html)

        # The pattern r'<input[^>]*csrf_token[^>]*value="([^"]+)"' captures the value attribute
        assert result == "captured_value"

    def test_extract_csrf_token_from_js(self):
        """测试从 JavaScript 提取"""
        sm = SupersetSessionManager()

        html = '"csrfToken":"token789"'
        result = sm._extract_csrf_token(html)

        assert result == "token789"

    def test_extract_csrf_token_not_found(self):
        """测试未找到 token"""
        sm = SupersetSessionManager()

        html = '<div>No token here</div>'
        result = sm._extract_csrf_token(html)

        assert result is None


class TestGetSession:
    """测试获取会话"""

    @pytest.mark.asyncio
    async def test_get_session_valid(self):
        """测试获取有效会话"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}
        sm._csrf_token = "test_token"
        sm._session_expire = time.time() + 3600

        cookies, csrf = await sm.get_session()

        assert cookies == {"session": "test"}
        assert csrf == "test_token"

    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """测试获取过期会话"""
        sm = SupersetSessionManager()
        sm._cookies = {"session": "test"}
        sm._csrf_token = "test_token"
        sm._session_expire = time.time() - 400  # Expired

        # Mock _create_session to return None
        async def mock_create():
            return None, None

        with patch.object(sm, '_create_session', side_effect=mock_create):
            cookies, csrf = await sm.get_session()

            assert cookies is None
            assert csrf is None


class TestGetSupersetSession:
    """测试获取 Superset 会话"""

    @pytest.mark.asyncio
    async def test_get_superset_session(self):
        """测试获取会话"""
        async def mock_get():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._session_manager') as mock_sm:
            mock_sm.get_session = AsyncMock(return_value=({"session": "test"}, "csrf"))
            result = await _get_superset_session()

            assert result == ({"session": "test"}, "csrf")


class TestSupersetRequest:
    """测试 Superset 请求函数"""

    @pytest.mark.asyncio
    async def test_superset_request_no_session(self):
        """测试无会话时请求"""
        async def mock_get_session():
            return None, None

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            result = await _superset_request(path="api/test", method="GET")

            assert result.code != 20000
            assert "无法获取 Superset 会话" in result.message

    @pytest.mark.asyncio
    async def test_superset_request_get_success(self):
        """测试 GET 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="GET")

                assert result.code == 20000

    @pytest.mark.asyncio
    async def test_superset_request_post_success(self):
        """测试 POST 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"created": True}

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="POST", json_data={"key": "value"})

                assert result.code == 20000

    @pytest.mark.asyncio
    async def test_superset_request_unsupported_method(self):
        """测试不支持的 HTTP 方法"""
        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            result = await _superset_request(path="api/test", method="INVALID")

            assert result.code != 20000
            assert "不支持的 HTTP 方法" in result.message

    @pytest.mark.asyncio
    async def test_superset_request_401_invalidates(self):
        """测试 401 响应使会话失效"""
        mock_response = MagicMock()
        mock_response.status_code = 401

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="GET")

                assert result.code != 20000
                assert "认证失败" in result.message

    @pytest.mark.asyncio
    async def test_superset_request_403_permission_denied(self):
        """测试 403 响应权限不足"""
        mock_response = MagicMock()
        mock_response.status_code = 403

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="GET")

                assert result.code != 20000
                assert "权限不足" in result.message

    @pytest.mark.asyncio
    async def test_superset_request_404_returns_empty(self):
        """测试 404 响应返回空结果"""
        mock_response = MagicMock()
        mock_response.status_code = 404

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="GET")

                assert result.code == 20000
                assert result.data == {"result": [], "count": 0}

    @pytest.mark.asyncio
    async def test_superset_request_exception(self):
        """测试异常处理"""
        import httpx

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
                mock_client.cookies = {}
                mock_client_class.return_value = mock_client

                result = await _superset_request(path="api/test", method="GET")

                assert result.code != 20000
                assert "Superset 服务异常" in result.message


class TestGetDashboardsV1:
    """测试 v1 获取仪表板端点"""

    @pytest.mark.asyncio
    async def test_get_dashboards_v1(self):
        """测试获取仪表板列表"""
        from services.portal.routers.superset import get_dashboards_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"dashboards": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_dashboards_v1(user=mock_payload)

            assert result.code == 20000


class TestGetDashboardV1:
    """测试 v1 获取仪表板详情端点"""

    @pytest.mark.asyncio
    async def test_get_dashboard_v1(self):
        """测试获取仪表板详情"""
        from services.portal.routers.superset import get_dashboard_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"id": 1, "name": "Dashboard 1"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_dashboard_v1(dashboard_id=1, user=mock_payload)

            assert result.code == 20000


class TestGetChartsV1:
    """测试 v1 获取图表端点"""

    @pytest.mark.asyncio
    async def test_get_charts_v1(self):
        """测试获取图表列表"""
        from services.portal.routers.superset import get_charts_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"charts": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_charts_v1(user=mock_payload)

            assert result.code == 20000


class TestGetChartV1:
    """测试 v1 获取图表详情端点"""

    @pytest.mark.asyncio
    async def test_get_chart_v1(self):
        """测试获取图表详情"""
        from services.portal.routers.superset import get_chart_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"id": 1, "name": "Chart 1"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_chart_v1(chart_id=1, user=mock_payload)

            assert result.code == 20000


class TestGetDatasetsV1:
    """测试 v1 获取数据集端点"""

    @pytest.mark.asyncio
    async def test_get_datasets_v1(self):
        """测试获取数据集列表"""
        from services.portal.routers.superset import get_datasets_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"datasets": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_datasets_v1(user=mock_payload)

            assert result.code == 20000


class TestGetDatasetV1:
    """测试 v1 获取数据集详情端点"""

    @pytest.mark.asyncio
    async def test_get_dataset_v1(self):
        """测试获取数据集详情"""
        from services.portal.routers.superset import get_dataset_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"id": 1, "name": "Dataset 1"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_dataset_v1(dataset_id=1, user=mock_payload)

            assert result.code == 20000


class TestGetDatabasesV1:
    """测试 v1 获取数据库端点"""

    @pytest.mark.asyncio
    async def test_get_databases_v1(self):
        """测试获取数据库列表"""
        from services.portal.routers.superset import get_databases_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"databases": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_databases_v1(user=mock_payload)

            assert result.code == 20000


class TestGetMeV1:
    """测试 v1 获取用户信息端点"""

    @pytest.mark.asyncio
    async def test_get_me_v1(self):
        """测试获取当前用户信息"""
        from services.portal.routers.superset import get_me_v1
        from services.common.auth import TokenPayload

        with patch('services.portal.routers.superset._superset_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"username": "admin"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_me_v1(user=mock_payload)

            assert result.code == 20000


class TestSupersetProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_superset_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.superset import superset_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock both get_current_user and proxy_request
        with patch('services.portal.routers.superset.get_current_user', return_value=mock_payload):
            with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
                with patch('services.portal.routers.superset.proxy_request', new_callable=AsyncMock) as mock_proxy:
                    from fastapi import Response
                    mock_proxy.return_value = Response(content=b'{"data": []}', status_code=200)

                    result = await superset_proxy("api/dashboards", mock_request)
                    assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_superset_proxy_with_session(self):
        """测试带会话的代理"""
        from services.portal.routers.superset import superset_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.superset.get_current_user', return_value=mock_payload):
            with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
                with patch('services.portal.routers.superset.proxy_request', new_callable=AsyncMock) as mock_proxy:
                    from fastapi import Response
                    mock_proxy.return_value = Response(content=b'{"data": []}', status_code=200)

                    result = await superset_proxy("api/dashboards", mock_request)
                    assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_superset_proxy_post(self):
        """测试 POST 代理"""
        from services.portal.routers.superset import superset_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

        async def mock_get_session():
            return {"session": "test"}, "csrf"

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.superset.get_current_user', return_value=mock_payload):
            with patch('services.portal.routers.superset._get_superset_session', side_effect=mock_get_session):
                with patch('services.portal.routers.superset.proxy_request', new_callable=AsyncMock) as mock_proxy:
                    from fastapi import Response
                    mock_proxy.return_value = Response(content=b'{"created": true}', status_code=201)

                    result = await superset_proxy("api/create", mock_request)
                    assert result.status_code == 201
