"""Unit tests for error handler utilities

Tests for services/common/error_handler.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from services.common.error_handler import (
    UnifiedErrorMiddleware,
    ApiErrorHandler,
    ProxyErrorHandler,
    handle_proxy_error,
)
from services.common.exceptions import AppException
from services.common.api_response import ErrorCode


class TestUnifiedErrorMiddleware:
    """测试统一错误处理中间件"""

    def test_init_default(self):
        """测试默认初始化"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        assert middleware.app == app
        assert middleware.debug is False
        assert middleware.hide_traceback is True

    def test_init_debug_mode(self):
        """测试调试模式初始化"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app, debug=True, hide_traceback=False)

        assert middleware.debug is True
        assert middleware.hide_traceback is False

    @pytest.mark.asyncio
    async def test_dispatch_no_exception(self):
        """测试正常请求处理"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"
        request.url = MagicMock()
        request.url.path = "/test"
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock()
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_handles_exception(self):
        """测试异常处理"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.url = MagicMock()
        request.url.path = "/api/test"
        request.query_params = {"id": "1"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        call_next = AsyncMock(side_effect=ValueError("Test error"))

        result = await middleware.dispatch(request, call_next)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_exception_app_exception(self):
        """测试应用异常处理"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"
        request.url = MagicMock()
        request.url.path = "/test"
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        exc = AppException("Test error", code=ErrorCode.INVALID_PARAMS)

        result = await middleware._handle_exception(request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_handle_exception_in_debug_mode(self):
        """测试调试模式下的异常处理"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app, debug=True, hide_traceback=False)

        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"
        request.url = MagicMock()
        request.url.path = "/test"
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        exc = ValueError("Debug test error")

        result = await middleware._handle_exception(request, exc)

        assert isinstance(result, JSONResponse)
        content = result.body.decode()
        # In debug mode, should include detail
        assert "detail" in content or "Debug test error" in content

    def test_parse_exception_app_exception(self):
        """测试解析应用异常"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = AppException("Custom error", code=ErrorCode.USER_NOT_FOUND, detail="User id: 123")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.USER_NOT_FOUND
        assert message == "Custom error"
        assert detail == "User id: 123"

    def test_parse_exception_http_exception_401(self):
        """测试解析 HTTP 401 异常"""
        from fastapi import HTTPException

        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = HTTPException(status_code=401, detail="Not authenticated")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.UNAUTHORIZED
        assert "未授权" in message

    def test_parse_exception_http_exception_403(self):
        """测试解析 HTTP 403 异常"""
        from fastapi import HTTPException

        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = HTTPException(status_code=403, detail="Forbidden")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.PERMISSION_DENIED
        assert "权限不足" in message

    def test_parse_exception_http_exception_404(self):
        """测试解析 HTTP 404 异常"""
        from fastapi import HTTPException

        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = HTTPException(status_code=404, detail="Not found")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.NOT_FOUND
        assert "不存在" in message

    def test_parse_exception_http_exception_422(self):
        """测试解析 HTTP 422 异常"""
        from fastapi import HTTPException

        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = HTTPException(status_code=422, detail="Validation failed")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.VALIDATION_FAILED
        # When detail is provided, it uses the detail message
        assert "Validation failed" in message or "校验" in message

    def test_parse_exception_generic_exception(self):
        """测试解析通用异常"""
        app = MagicMock()
        middleware = UnifiedErrorMiddleware(app)

        exc = ValueError("Generic error")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.INTERNAL_ERROR
        assert "内部服务错误" in message
        assert detail == "Generic error"


class TestApiErrorHandler:
    """测试 API 错误处理工具类"""

    def test_not_found_default(self):
        """测试默认 404 响应"""
        response = ApiErrorHandler.not_found()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    def test_not_found_custom_resource(self):
        """测试自定义资源 404 响应"""
        response = ApiErrorHandler.not_found("用户")

        assert response.status_code == 404

    def test_unauthorized_default(self):
        """测试默认 401 响应"""
        response = ApiErrorHandler.unauthorized()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    def test_unauthorized_custom_message(self):
        """测试自定义消息 401 响应"""
        response = ApiErrorHandler.unauthorized("Token 已过期")

        assert response.status_code == 401

    def test_forbidden_default(self):
        """测试默认 403 响应"""
        response = ApiErrorHandler.forbidden()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

    def test_forbidden_custom_message(self):
        """测试自定义消息 403 响应"""
        response = ApiErrorHandler.forbidden("需要管理员权限")

        assert response.status_code == 403

    def test_validation_error_default(self):
        """测试默认 422 响应"""
        response = ApiErrorHandler.validation_error()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

    def test_validation_error_custom_message(self):
        """测试自定义消息 422 响应"""
        response = ApiErrorHandler.validation_error("邮箱格式错误")

        assert response.status_code == 422

    def test_internal_error_default(self):
        """测试默认 500 响应"""
        response = ApiErrorHandler.internal_error()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    def test_internal_error_custom_message(self):
        """测试自定义消息 500 响应"""
        response = ApiErrorHandler.internal_error("数据库连接失败")

        assert response.status_code == 500

    def test_service_unavailable_default(self):
        """测试默认 503 响应"""
        response = ApiErrorHandler.service_unavailable()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

    def test_service_unavailable_custom_service(self):
        """测试自定义服务 503 响应"""
        response = ApiErrorHandler.service_unavailable("DataHub")

        assert response.status_code == 503

    def test_gateway_timeout(self):
        """测试 504 响应"""
        response = ApiErrorHandler.gateway_timeout()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 504


class TestProxyErrorHandler:
    """测试代理服务错误处理工具类"""

    def test_service_error_seatunnel(self):
        """测试 SeaTunnel 服务错误"""
        response = ProxyErrorHandler.service_error("seatunnel", "Connection refused")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200  # Based on ErrorCode mapping

    def test_service_error_datahub(self):
        """测试 DataHub 服务错误"""
        response = ProxyErrorHandler.service_error("datahub")

        assert isinstance(response, JSONResponse)

    def test_service_error_dolphinscheduler(self):
        """测试 DolphinScheduler 服务错误"""
        response = ProxyErrorHandler.service_error("dolphinscheduler")

        assert isinstance(response, JSONResponse)

    def test_service_error_superset(self):
        """测试 Superset 服务错误"""
        response = ProxyErrorHandler.service_error("superset")

        assert isinstance(response, JSONResponse)

    def test_service_error_shardingsphere(self):
        """测试 ShardingSphere 服务错误"""
        response = ProxyErrorHandler.service_error("shardingsphere")

        assert isinstance(response, JSONResponse)

    def test_service_error_hop(self):
        """测试 Hop 服务错误"""
        response = ProxyErrorHandler.service_error("hop")

        assert isinstance(response, JSONResponse)

    def test_service_error_cube_studio(self):
        """测试 Cube Studio 服务错误"""
        response = ProxyErrorHandler.service_error("cube-studio")

        assert isinstance(response, JSONResponse)

    def test_service_error_unknown_service(self):
        """测试未知服务错误"""
        response = ProxyErrorHandler.service_error("unknown-service")

        assert isinstance(response, JSONResponse)

    def test_service_unavailable(self):
        """测试服务不可用"""
        response = ProxyErrorHandler.service_unavailable("SeaTunnel")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

    def test_connection_failed(self):
        """测试连接失败"""
        response = ProxyErrorHandler.connection_failed("DataHub")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503


class TestHandleProxyError:
    """测试代理服务异常处理函数"""

    def test_handle_timeout_exception(self):
        """测试超时异常处理"""
        import httpx

        exc = httpx.TimeoutException("Request timed out")
        response = handle_proxy_error("SeaTunnel", exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 504

    def test_handle_connect_error(self):
        """测试连接错误处理"""
        import httpx

        exc = httpx.ConnectError("Connection failed")
        response = handle_proxy_error("DataHub", exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

    def test_handle_http_status_error(self):
        """测试 HTTP 状态错误处理"""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 502
        exc = httpx.HTTPStatusError("Bad Gateway", request=MagicMock(), response=mock_response)
        response = handle_proxy_error("Superset", exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 502

    def test_handle_generic_exception(self):
        """测试通用异常处理"""
        exc = ValueError("Unknown error")
        response = handle_proxy_error("SeaTunnel", exc)

        assert isinstance(response, JSONResponse)
