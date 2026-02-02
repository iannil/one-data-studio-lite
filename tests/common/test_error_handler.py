"""Unit tests for error handler module

Tests for services/common/error_handler.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
import httpx

from services.common.error_handler import (
    UnifiedErrorMiddleware,
    ApiErrorHandler,
    ProxyErrorHandler,
    handle_proxy_error,
)
from services.common.api_response import ErrorCode
from services.common.exceptions import AppException


class TestUnifiedErrorMiddleware:
    """测试统一错误处理中间件"""

    def test_init_default(self):
        """测试默认初始化"""
        middleware = UnifiedErrorMiddleware(app=None)
        assert middleware.debug is False
        assert middleware.hide_traceback is True

    def test_init_with_params(self):
        """测试带参数初始化"""
        middleware = UnifiedErrorMiddleware(
            app=None,
            debug=True,
            hide_traceback=False
        )
        assert middleware.debug is True
        assert middleware.hide_traceback is False

    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """测试正常请求通过"""
        middleware = UnifiedErrorMiddleware(app=None)

        # Mock request and call_next
        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"
        mock_request.query_params = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_call_next(request):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result is mock_response

    @pytest.mark.asyncio
    async def test_dispatch_app_exception(self):
        """测试应用异常处理"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.method = "POST"
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.query_params = {"id": "123"}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        async def mock_call_next(request):
            raise AppException(
                message="Test error",
                code=ErrorCode.VALIDATION_FAILED,
                detail="Invalid input"
            )

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(result, JSONResponse)
        # VALIDATION_FAILED (40004) is not in HTTP_STATUS_MAP, defaults to 200
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_http_exception_401(self):
        """测试 HTTP 401 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/protected"
        mock_request.query_params = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        async def mock_call_next(request):
            raise HTTPException(status_code=401, detail="Unauthorized")

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_http_exception_403(self):
        """测试 HTTP 403 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/admin"
        mock_request.query_params = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.2"

        async def mock_call_next(request):
            raise HTTPException(status_code=403)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_dispatch_http_exception_404(self):
        """测试 HTTP 404 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/nonexistent"
        mock_request.query_params = {}
        mock_request.client = MagicMock()

        async def mock_call_next(request):
            raise HTTPException(status_code=404)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_dispatch_http_exception_422(self):
        """测试 HTTP 422 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/test"
        mock_request.query_params = {}
        mock_request.client = MagicMock()

        async def mock_call_next(request):
            raise HTTPException(status_code=422, detail="Validation failed")

        result = await middleware.dispatch(mock_request, mock_call_next)

        # VALIDATION_FAILED maps to 200 (not in HTTP_STATUS_MAP)
        assert result.status_code == 200
        import json
        body = json.loads(result.body.decode())
        assert body["code"] == ErrorCode.VALIDATION_FAILED

    @pytest.mark.asyncio
    async def test_dispatch_generic_exception(self):
        """测试普通异常处理"""
        middleware = UnifiedErrorMiddleware(app=None)

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/error"
        mock_request.query_params = {}
        mock_request.client = MagicMock()

        async def mock_call_next(request):
            raise ValueError("Something went wrong")

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_exception_with_debug(self):
        """测试调试模式下的异常处理"""
        middleware = UnifiedErrorMiddleware(
            app=None,
            debug=True,
            hide_traceback=False
        )

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/test"
        mock_request.query_params = {}
        mock_request.client = MagicMock()

        exc = ValueError("Test error")

        result = await middleware._handle_exception(mock_request, exc)

        assert isinstance(result, JSONResponse)
        # Debug mode should include detail and traceback
        import json
        body = json.loads(result.body.decode())
        assert "detail" in body or "traceback" in body

    @pytest.mark.asyncio
    async def test_handle_exception_without_debug(self):
        """测试生产模式下的异常处理"""
        middleware = UnifiedErrorMiddleware(
            app=None,
            debug=False,
            hide_traceback=True
        )

        mock_request = MagicMock(spec=StarletteRequest)
        mock_request.url.path = "/api/test"
        mock_request.query_params = {}
        mock_request.client = MagicMock()

        exc = ValueError("Test error")

        result = await middleware._handle_exception(mock_request, exc)

        assert isinstance(result, JSONResponse)
        import json
        body = json.loads(result.body.decode())
        # Production mode should not include detail or traceback
        assert "detail" not in body
        assert "traceback" not in body

    def test_parse_exception_app_exception(self):
        """测试解析应用异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = AppException(
            message="Custom error",
            code=ErrorCode.VALIDATION_FAILED,
            detail="Field 'name' is required"
        )

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.VALIDATION_FAILED
        assert message == "Custom error"
        assert detail == "Field 'name' is required"

    def test_parse_exception_http_401(self):
        """测试解析 HTTP 401 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = HTTPException(status_code=401)

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.UNAUTHORIZED
        assert "未授权" in message

    def test_parse_exception_http_403(self):
        """测试解析 HTTP 403 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = HTTPException(status_code=403)

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.PERMISSION_DENIED
        assert "权限" in message

    def test_parse_exception_http_404(self):
        """测试解析 HTTP 404 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = HTTPException(status_code=404)

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.NOT_FOUND
        assert "不存在" in message

    def test_parse_exception_http_422(self):
        """测试解析 HTTP 422 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = HTTPException(status_code=422, detail="Invalid email format")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.VALIDATION_FAILED
        assert "Invalid email format" in message

    def test_parse_exception_http_500(self):
        """测试解析 HTTP 500 异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = HTTPException(status_code=500, detail="Internal error")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.INTERNAL_ERROR

    def test_parse_exception_generic(self):
        """测试解析普通异常"""
        middleware = UnifiedErrorMiddleware(app=None)

        exc = RuntimeError("Database connection failed")

        code, message, detail = middleware._parse_exception(exc)

        assert code == ErrorCode.INTERNAL_ERROR
        assert "内部" in message


class TestApiErrorHandler:
    """测试 API 错误处理工具类"""

    def test_not_found_default(self):
        """测试默认 404 响应"""
        response = ApiErrorHandler.not_found()

        assert response.status_code == 404
        import json
        body = json.loads(response.body.decode())
        assert "不存在" in body["message"]

    def test_not_found_custom_resource(self):
        """测试自定义资源 404 响应"""
        response = ApiErrorHandler.not_found(resource="用户")

        assert response.status_code == 404
        import json
        body = json.loads(response.body.decode())
        assert "用户" in body["message"]

    def test_unauthorized_default(self):
        """测试默认 401 响应"""
        response = ApiErrorHandler.unauthorized()

        assert response.status_code == 401
        import json
        body = json.loads(response.body.decode())
        assert "未授权" in body["message"]

    def test_unauthorized_custom_message(self):
        """测试自定义 401 响应"""
        response = ApiErrorHandler.unauthorized(message="Token 已过期")

        assert response.status_code == 401
        import json
        body = json.loads(response.body.decode())
        assert body["message"] == "Token 已过期"

    def test_forbidden_default(self):
        """测试默认 403 响应"""
        response = ApiErrorHandler.forbidden()

        assert response.status_code == 403
        import json
        body = json.loads(response.body.decode())
        assert "权限" in body["message"]

    def test_validation_error_default(self):
        """测试默认 422 响应"""
        response = ApiErrorHandler.validation_error()

        assert response.status_code == 422
        import json
        body = json.loads(response.body.decode())
        assert "校验" in body["message"]

    def test_internal_error_default(self):
        """测试默认 500 响应"""
        response = ApiErrorHandler.internal_error()

        assert response.status_code == 500
        import json
        body = json.loads(response.body.decode())
        assert "内部" in body["message"]

    def test_service_unavailable_default(self):
        """测试默认 503 响应"""
        response = ApiErrorHandler.service_unavailable()

        assert response.status_code == 503
        import json
        body = json.loads(response.body.decode())
        assert "不可用" in body["message"]

    def test_service_unavailable_custom(self):
        """测试自定义服务 503 响应"""
        response = ApiErrorHandler.service_unavailable(service="数据库")

        assert response.status_code == 503
        import json
        body = json.loads(response.body.decode())
        assert "数据库" in body["message"]

    def test_gateway_timeout(self):
        """测试 504 响应"""
        response = ApiErrorHandler.gateway_timeout()

        assert response.status_code == 504
        import json
        body = json.loads(response.body.decode())
        assert "超时" in body["message"]


class TestProxyErrorHandler:
    """测试代理服务错误处理工具类"""

    def test_service_error_seatunnel(self):
        """测试 SeaTunnel 服务错误"""
        response = ProxyErrorHandler.service_error("seatunnel", "Connection failed")

        # SEATUNNEL_ERROR (42100) is not in HTTP_STATUS_MAP, defaults to 200
        assert response.status_code == 200
        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.SEATUNNEL_ERROR

    def test_service_error_datahub(self):
        """测试 DataHub 服务错误"""
        response = ProxyErrorHandler.service_error("datahub")

        # DATAHUB_ERROR (42101) is not in HTTP_STATUS_MAP, defaults to 200
        assert response.status_code == 200
        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.DATAHUB_ERROR

    def test_service_error_dolphinscheduler(self):
        """测试 DolphinScheduler 服务错误"""
        response = ProxyErrorHandler.service_error("dolphinscheduler")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.DOLPHINSCHEDULER_ERROR

    def test_service_error_superset(self):
        """测试 Superset 服务错误"""
        response = ProxyErrorHandler.service_error("superset")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.SUPERSET_ERROR

    def test_service_error_shardingsphere(self):
        """测试 ShardingSphere 服务错误"""
        response = ProxyErrorHandler.service_error("shardingsphere")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.SHARDINGSPHERE_ERROR

    def test_service_error_hop(self):
        """测试 Hop 服务错误"""
        response = ProxyErrorHandler.service_error("hop")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.HOP_ERROR

    def test_service_error_cube_studio(self):
        """测试 CubeStudio 服务错误"""
        response = ProxyErrorHandler.service_error("cube-studio")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.CUBE_STUDIO_ERROR

    def test_service_error_unknown(self):
        """测试未知服务错误"""
        response = ProxyErrorHandler.service_error("unknown-service")

        import json
        body = json.loads(response.body.decode())
        assert body["code"] == ErrorCode.EXTERNAL_SERVICE_ERROR

    def test_service_unavailable(self):
        """测试服务不可用"""
        response = ProxyErrorHandler.service_unavailable("SeaTunnel")

        assert response.status_code == 503
        import json
        body = json.loads(response.body.decode())
        assert "SeaTunnel" in body["message"]

    def test_connection_failed(self):
        """测试连接失败"""
        response = ProxyErrorHandler.connection_failed("DataHub")

        assert response.status_code == 503
        import json
        body = json.loads(response.body.decode())
        assert "无法连接" in body["message"]
        assert "DataHub" in body["message"]


class TestHandleProxyError:
    """测试代理服务异常处理函数"""

    def test_handle_timeout_exception(self):
        """测试超时异常"""
        exc = httpx.TimeoutException("Request timeout")

        response = handle_proxy_error("SeaTunnel", exc)

        assert response.status_code == 504
        import json
        body = json.loads(response.body.decode())
        assert "超时" in body["message"]
        assert body["code"] == ErrorCode.GATEWAY_TIMEOUT

    def test_handle_connect_error(self):
        """测试连接错误"""
        exc = httpx.ConnectError("Connection refused")

        response = handle_proxy_error("DataHub", exc)

        assert response.status_code == 503
        import json
        body = json.loads(response.body.decode())
        assert "无法连接" in body["message"]

    def test_handle_http_status_error(self):
        """测试 HTTP 状态错误"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        exc = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )

        response = handle_proxy_error("DolphinScheduler", exc)

        assert response.status_code == 500
        import json
        body = json.loads(response.body.decode())
        assert "500" in body["message"]

    def test_handle_generic_exception(self):
        """测试普通异常"""
        exc = ValueError("Unexpected error")

        response = handle_proxy_error("Superset", exc)

        # EXTERNAL_SERVICE_ERROR (42000) is not in HTTP_STATUS_MAP, defaults to 200
        assert response.status_code == 200
        import json
        body = json.loads(response.body.decode())
        assert "Superset" in body["message"]
