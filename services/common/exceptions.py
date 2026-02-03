"""自定义异常与统一错误处理

提供统一的异常类和错误处理机制，确保所有服务返回一致的错误响应格式。
"""

import logging
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# 请求ID上下文变量
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class ErrorCode(str, Enum):
    """标准错误码

    格式: {服务缩写}_{错误类型}_{具体错误}
    """
    # 通用错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # 认证相关
    INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    PASSWORD_TOO_WEAK = "AUTH_PASSWORD_TOO_WEAK"
    ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
    ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"

    # 数据相关
    DATABASE_ERROR = "DATA_DATABASE_ERROR"
    RECORD_NOT_FOUND = "DATA_RECORD_NOT_FOUND"
    DUPLICATE_RECORD = "DATA_DUPLICATE_RECORD"
    INVALID_QUERY = "DATA_INVALID_QUERY"

    # 外部服务
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATAHUB_ERROR = "EXT_DATAHUB_ERROR"
    SUPERSET_ERROR = "EXT_SUPERSET_ERROR"
    DOLPHINSCHEDULER_ERROR = "EXT_DOLPHINSCHEDULER_ERROR"
    SEATUNNEL_ERROR = "EXT_SEATUNNEL_ERROR"
    LLM_ERROR = "EXT_LLM_ERROR"

    # 业务逻辑
    OPERATION_FAILED = "BIZ_OPERATION_FAILED"
    INVALID_STATE = "BIZ_INVALID_STATE"
    CONFLICT = "BIZ_CONFLICT"


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"           # 用户输入错误等
    MEDIUM = "medium"     # 业务逻辑错误
    HIGH = "high"         # 系统错误，需要关注
    CRITICAL = "critical"  # 严重错误，需要立即处理


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str,
        code: int = 500,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        detail: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.error_code = error_code
        self.detail = detail
        self.severity = severity
        self.context = context or {}
        self.request_id = request_id_ctx.get("")
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {
            "success": False,
            "code": self.error_code.value,
            "message": self.message,
            "timestamp": int(datetime.now().timestamp()),
        }
        if self.request_id:
            result["request_id"] = self.request_id
        if self.detail:
            result["detail"] = self.detail
        if self.context:
            result["context"] = self.context
        return result


# ============================================================
# 具体异常类
# ============================================================

class NotFoundError(AppException):
    """资源不存在"""

    def __init__(
        self,
        resource: str,
        resource_id: str | None = None,
        detail: str | None = None,
    ):
        msg = f"{resource} 不存在"
        if resource_id:
            msg = f"{resource} [{resource_id}] 不存在"
        super().__init__(
            message=msg,
            code=404,
            error_code=ErrorCode.NOT_FOUND,
            detail=detail,
            severity=ErrorSeverity.LOW,
        )


class AlreadyExistsError(AppException):
    """资源已存在"""

    def __init__(
        self,
        resource: str,
        resource_id: str | None = None,
        detail: str | None = None,
    ):
        msg = f"{resource} 已存在"
        if resource_id:
            msg = f"{resource} [{resource_id}] 已存在"
        super().__init__(
            message=msg,
            code=409,
            error_code=ErrorCode.ALREADY_EXISTS,
            detail=detail,
            severity=ErrorSeverity.LOW,
        )


class ValidationError(AppException):
    """参数校验失败"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        detail: str | None = None,
    ):
        context = {"field": field} if field else {}
        super().__init__(
            message=message,
            code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            detail=detail,
            severity=ErrorSeverity.LOW,
            context=context,
        )


class AuthenticationError(AppException):
    """认证失败"""

    def __init__(
        self,
        message: str = "认证失败",
        error_code: ErrorCode = ErrorCode.UNAUTHENTICATED,
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            code=401,
            error_code=error_code,
            detail=detail,
            severity=ErrorSeverity.LOW,
        )


class PermissionDeniedError(AppException):
    """权限不足"""

    def __init__(
        self,
        message: str = "权限不足",
        required_permission: str | None = None,
        detail: str | None = None,
    ):
        context = {"required_permission": required_permission} if required_permission else {}
        super().__init__(
            message=message,
            code=403,
            error_code=ErrorCode.PERMISSION_DENIED,
            detail=detail,
            severity=ErrorSeverity.LOW,
            context=context,
        )


class ServiceUnavailableError(AppException):
    """外部服务不可用"""

    def __init__(
        self,
        service: str,
        detail: str | None = None,
        error_code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
    ):
        super().__init__(
            message=f"服务暂时不可用: {service}",
            code=503,
            error_code=error_code,
            detail=detail,
            severity=ErrorSeverity.HIGH,
            context={"service": service},
        )


class DatabaseError(AppException):
    """数据库错误"""

    def __init__(
        self,
        message: str = "数据库操作失败",
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            code=500,
            error_code=ErrorCode.DATABASE_ERROR,
            detail=detail,
            severity=ErrorSeverity.HIGH,
        )


class ExternalServiceError(AppException):
    """外部服务调用错误"""

    def __init__(
        self,
        service: str,
        message: str = "外部服务调用失败",
        status_code: int | None = None,
        detail: str | None = None,
    ):
        context = {"service": service}
        if status_code:
            context["status_code"] = status_code
        super().__init__(
            message=f"{service}: {message}",
            code=500,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            detail=detail,
            severity=ErrorSeverity.MEDIUM,
            context=context,
        )


class RateLimitExceededError(AppException):
    """超过速率限制"""

    def __init__(
        self,
        limit: int,
        window: int,
        detail: str | None = None,
    ):
        super().__init__(
            message=f"请求过于频繁，每{window}秒最多{limit}次请求",
            code=429,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            detail=detail,
            severity=ErrorSeverity.LOW,
            context={"limit": limit, "window": window},
        )


class ConflictError(AppException):
    """资源冲突"""

    def __init__(
        self,
        message: str,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code=409,
            error_code=ErrorCode.CONFLICT,
            detail=detail,
            severity=ErrorSeverity.LOW,
            context=context,
        )


# ============================================================
# 错误处理装饰器
# ============================================================

T = TypeVar("T")


def handle_errors(
    default_message: str = "操作失败",
    reraise: bool = False,
):
    """统一错误处理装饰器

    Args:
        default_message: 默认错误消息
        reraise: 是否重新抛出异常（用于调试）

    Usage:
        @handle_errors("获取用户失败")
        async def get_user(user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppException:
                if reraise:
                    raise
                raise
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}")
                if reraise:
                    raise
                raise AppException(
                    message=default_message,
                    detail=str(e) if logger.isEnabledFor(logging.DEBUG) else None,
                ) from e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppException:
                if reraise:
                    raise
                raise
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}")
                if reraise:
                    raise
                raise AppException(
                    message=default_message,
                    detail=str(e) if logger.isEnabledFor(logging.DEBUG) else None,
                ) from e

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================
# 异常处理器注册
# ============================================================

def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """为每个请求添加唯一 ID"""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理应用异常"""
        # 记录错误日志
        log_method = logger.warning if exc.code < 500 else logger.error
        log_method(
            f"[{exc.error_code.value}] {exc.message}",
            extra={
                "request_id": exc.request_id,
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.error_code.value,
                "severity": exc.severity.value,
                "context": exc.context,
            },
        )

        return JSONResponse(
            status_code=exc.code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""

        request_id = request_id_ctx.get()

        # 记录完整错误信息
        logger.error(
            f"Unhandled exception: {exc.__class__.__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
        )

        # 开发环境返回详细信息
        is_debug = logger.isEnabledFor(logging.DEBUG)

        response_data = {
            "success": False,
            "code": ErrorCode.UNKNOWN_ERROR.value,
            "message": "服务暂时不可用，请稍后再试",
            "timestamp": int(datetime.now().timestamp()),
        }

        if request_id:
            response_data["request_id"] = request_id

        if is_debug:
            response_data["detail"] = str(exc)
            response_data["type"] = exc.__class__.__name__
            response_data["traceback"] = traceback.format_exc().split("\n")

        return JSONResponse(
            status_code=500,
            content=response_data,
        )


# ============================================================
# 响应工具函数
# ============================================================

def success_response(
    data: Any = None,
    message: str = "success",
    code: int = 20000,
) -> dict[str, Any]:
    """成功响应格式

    Args:
        data: 响应数据
        message: 响应消息
        code: 业务状态码（非HTTP状态码）

    Returns:
        标准响应字典
    """
    response = {
        "success": True,
        "code": code,
        "message": message,
        "timestamp": int(datetime.now().timestamp()),
    }
    if data is not None:
        response["data"] = data

    request_id = request_id_ctx.get()
    if request_id:
        response["request_id"] = request_id

    return response


def error_response(
    message: str,
    code: int = 50000,
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    detail: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """错误响应格式

    Args:
        message: 错误消息
        code: 业务状态码
        error_code: 错误码枚举
        detail: 详细信息
        context: 上下文信息

    Returns:
        标准错误响应字典
    """
    response = {
        "success": False,
        "code": error_code.value,
        "message": message,
        "timestamp": int(datetime.now().timestamp()),
    }

    request_id = request_id_ctx.get()
    if request_id:
        response["request_id"] = request_id
    if detail:
        response["detail"] = detail
    if context:
        response["context"] = context

    return response
