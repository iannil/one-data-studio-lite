"""自定义异常与处理器"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: int = 500, detail: str | None = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppException):
    """资源不存在"""
    def __init__(self, resource: str, resource_id: str | None = None):
        msg = f"{resource} 不存在"
        if resource_id:
            msg = f"{resource} [{resource_id}] 不存在"
        super().__init__(message=msg, code=404)


class ValidationError(AppException):
    """参数校验失败"""
    def __init__(self, message: str):
        super().__init__(message=message, code=422)


class AuthenticationError(AppException):
    """认证失败"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message=message, code=401)


class PermissionDeniedError(AppException):
    """权限不足"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code=403)


class ServiceUnavailableError(AppException):
    """外部服务不可用"""
    def __init__(self, service: str):
        super().__init__(message=f"服务不可用: {service}", code=503)


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.code,
            content={
                "success": False,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "内部服务错误",
                "detail": str(exc),
            },
        )
