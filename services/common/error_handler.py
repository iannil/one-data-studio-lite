"""统一错误处理中间件

提供统一的错误响应格式，适用于所有 API 路由。
支持将异常转换为 ApiResponse 格式。
"""

import logging
import time
import traceback
from typing import Any, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from services.common.api_response import ApiResponse, ErrorCode, error, get_http_status

logger = logging.getLogger(__name__)


class UnifiedErrorMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件

    功能:
    - 捕获所有异常，转换为统一格式
    - 记录错误日志
    - 支持开发环境详细错误信息
    - 隐藏敏感信息（生产环境）
    """

    def __init__(
        self,
        app: ASGIApp,
        debug: bool = False,
        hide_traceback: bool = True,
    ) -> None:
        """初始化中间件

        Args:
            app: ASGI 应用
            debug: 是否为调试模式
            hide_traceback: 是否隐藏堆栈信息
        """
        super().__init__(app)
        self.debug = debug
        self.hide_traceback = hide_traceback

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并捕获异常"""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """处理异常并返回统一格式响应

        Args:
            request: 请求对象
            exc: 异常对象

        Returns:
            JSON 格式的错误响应
        """
        # 记录错误
        self._log_error(request, exc)

        # 解析异常
        error_code, message, detail = self._parse_exception(exc)

        # 构建响应
        http_status = get_http_status(error_code)
        response_data = {
            "code": error_code,
            "message": message,
            "data": None,
            "timestamp": int(time.time()),
        }

        # 开发环境添加详细信息
        if self.debug and not self.hide_traceback:
            response_data["detail"] = detail or str(exc)
            response_data["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=http_status,
            content=response_data,
        )

    def _log_error(self, request: Request, exc: Exception) -> None:
        """记录错误日志

        Args:
            request: 请求对象
            exc: 异常对象
        """
        logger.error(
            f"API 错误: {request.method} {request.url.path}",
            exc_info=exc,
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )

    def _parse_exception(self, exc: Exception) -> tuple[int, str, str]:
        """解析异常为错误码和消息

        Args:
            exc: 异常对象

        Returns:
            (错误码, 消息, 详情)
        """
        # 自定义应用异常
        from services.common.exceptions import AppException

        if isinstance(exc, AppException):
            return exc.code, exc.message, exc.detail or ""

        # FastAPI HTTPException
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            status_code = exc.status_code
            if status_code == 401:
                return ErrorCode.UNAUTHORIZED, "未授权，请先登录", ""
            elif status_code == 403:
                return ErrorCode.PERMISSION_DENIED, "权限不足", ""
            elif status_code == 404:
                return ErrorCode.NOT_FOUND, "请求的资源不存在", ""
            elif status_code == 422:
                return ErrorCode.VALIDATION_FAILED, exc.detail or "参数校验失败", ""
            else:
                return ErrorCode.INTERNAL_ERROR, f"请求失败: {exc.detail}", ""

        # 其他异常
        return ErrorCode.INTERNAL_ERROR, "内部服务错误", str(exc)


class ApiErrorHandler:
    """API 错误处理工具类

    提供便捷的错误响应创建方法。
    """

    @staticmethod
    def not_found(resource: str = "资源") -> JSONResponse:
        """返回 404 响应"""
        response = error(
            message=f"{resource}不存在",
            code=ErrorCode.NOT_FOUND
        )
        return JSONResponse(status_code=404, content=response.model_dump())

    @staticmethod
    def unauthorized(message: str = "未授权") -> JSONResponse:
        """返回 401 响应"""
        response = error(
            message=message,
            code=ErrorCode.UNAUTHORIZED
        )
        return JSONResponse(status_code=401, content=response.model_dump())

    @staticmethod
    def forbidden(message: str = "权限不足") -> JSONResponse:
        """返回 403 响应"""
        response = error(
            message=message,
            code=ErrorCode.PERMISSION_DENIED
        )
        return JSONResponse(status_code=403, content=response.model_dump())

    @staticmethod
    def validation_error(message: str = "参数校验失败") -> JSONResponse:
        """返回 422 响应"""
        response = error(
            message=message,
            code=ErrorCode.VALIDATION_FAILED
        )
        return JSONResponse(status_code=422, content=response.model_dump())

    @staticmethod
    def internal_error(message: str = "内部服务错误") -> JSONResponse:
        """返回 500 响应"""
        response = error(
            message=message,
            code=ErrorCode.INTERNAL_ERROR
        )
        return JSONResponse(status_code=500, content=response.model_dump())

    @staticmethod
    def service_unavailable(service: str = "服务") -> JSONResponse:
        """返回 503 响应"""
        response = error(
            message=f"{service}不可用",
            code=ErrorCode.SERVICE_UNAVAILABLE
        )
        return JSONResponse(status_code=503, content=response.model_dump())

    @staticmethod
    def gateway_timeout() -> JSONResponse:
        """返回 504 响应"""
        response = error(
            message="网关超时",
            code=ErrorCode.GATEWAY_TIMEOUT
        )
        return JSONResponse(status_code=504, content=response.model_dump())


class ProxyErrorHandler:
    """代理服务错误处理工具类

    用于处理上游服务（DataHub、SeaTunnel 等）的错误。
    """

    @staticmethod
    def service_error(service_name: str, detail: str = "") -> JSONResponse:
        """返回上游服务错误"""
        error_code_map = {
            "seatunnel": ErrorCode.SEATUNNEL_ERROR,
            "datahub": ErrorCode.DATAHUB_ERROR,
            "dolphinscheduler": ErrorCode.DOLPHINSCHEDULER_ERROR,
            "superset": ErrorCode.SUPERSET_ERROR,
            "shardingsphere": ErrorCode.SHARDINGSPHERE_ERROR,
            "hop": ErrorCode.HOP_ERROR,
            "cube-studio": ErrorCode.CUBE_STUDIO_ERROR,
        }

        code = error_code_map.get(service_name.lower(), ErrorCode.EXTERNAL_SERVICE_ERROR)
        message = f"{service_name} 服务错误"
        if detail:
            message += f": {detail}"

        response = error(message=message, code=code)
        return JSONResponse(status_code=get_http_status(code), content=response.model_dump())

    @staticmethod
    def service_unavailable(service_name: str) -> JSONResponse:
        """返回服务不可用错误"""
        return ApiErrorHandler.service_unavailable(f"{service_name} 服务")

    @staticmethod
    def connection_failed(service_name: str) -> JSONResponse:
        """返回连接失败错误"""
        response = error(
            message=f"无法连接 {service_name} 服务",
            code=ErrorCode.SERVICE_UNAVAILABLE
        )
        return JSONResponse(status_code=503, content=response.model_dump())


# 便捷函数
def handle_proxy_error(service_name: str, exc: Exception) -> JSONResponse:
    """处理代理服务异常

    Args:
        service_name: 服务名称
        exc: 异常对象

    Returns:
        JSON 错误响应
    """
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        response = error(message=f"{service_name} 请求超时", code=ErrorCode.GATEWAY_TIMEOUT)
        return JSONResponse(status_code=504, content=response.model_dump())
    elif isinstance(exc, httpx.ConnectError):
        return ProxyErrorHandler.connection_failed(service_name)
    elif isinstance(exc, httpx.HTTPStatusError):
        response = error(
            message=f"{service_name} 返回错误: {exc.response.status_code}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR
        )
        return JSONResponse(status_code=exc.response.status_code, content=response.model_dump())
    else:
        return ProxyErrorHandler.service_error(service_name, str(exc))
