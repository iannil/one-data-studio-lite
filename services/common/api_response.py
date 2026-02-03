"""统一 API 响应格式

定义统一的 API 响应结构和错误码，确保前后端 API 一致性。

响应格式:
    {
        "code": 200,           # 业务状态码
        "message": "success",  # 提示信息
        "data": {...},         # 业务数据
        "timestamp": 1706659200  # 时间戳
    }

错误响应格式:
    {
        "code": 40001,
        "message": "参数校验失败",
        "data": null,
        "timestamp": 1706659200
    }

使用示例:
    from services.common.api_response import ApiResponse, success, error
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/users", response_model=ApiResponse)
    async def list_users():
        users = await get_users()
        return success(data=users)

    @router.post("/users", response_model=ApiResponse)
    async def create_user(user: UserCreate):
        if not user.email:
            return error(code=40001, message="邮箱不能为空")
        result = await create_user(user)
        return success(data=result, message="创建成功")
"""

import time
from enum import IntEnum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


class ErrorCode(IntEnum):
    """统一错误码定义

    规则:
    - 2xxxx: 成功/信息类
    - 4xxxx: 客户端错误
    - 5xxxx: 服务端错误

    细分:
    - 20000-20999: 成功相关
    - 40000-40999: 参数/权限错误
    - 41000-41999: 业务规则错误
    - 42000-42999: 外部服务错误
    - 50000-59999: 系统错误
    """

    # 成功
    SUCCESS = 20000
    CREATED = 20001
    ACCEPTED = 20002
    NO_CONTENT = 20003

    # 参数错误 (40001-40099)
    INVALID_PARAMS = 40001
    MISSING_PARAM = 40002
    INVALID_FORMAT = 40003
    VALIDATION_FAILED = 40004

    # 认证/授权 (40100-40199)
    UNAUTHORIZED = 40100
    TOKEN_EXPIRED = 40101
    TOKEN_INVALID = 40102
    PERMISSION_DENIED = 40300

    # 资源错误 (40400-40499)
    NOT_FOUND = 40400
    RESOURCE_NOT_FOUND = 40401
    USER_NOT_FOUND = 40402
    CONFIG_NOT_FOUND = 40403

    # 业务规则 (41000-41999)
    DUPLICATE_RESOURCE = 41001
    OPERATION_NOT_ALLOWED = 41002
    INVALID_STATE = 41003
    QUOTA_EXCEEDED = 41004

    # 外部服务 (42000-42999)
    EXTERNAL_SERVICE_ERROR = 42000
    DATABASE_ERROR = 42001
    CACHE_ERROR = 42002
    MESSAGE_QUEUE_ERROR = 42003

    # 上游子系统错误
    SEATUNNEL_ERROR = 42100
    DATAHUB_ERROR = 42101
    DOLPHINSCHEDULER_ERROR = 42102
    SUPERSET_ERROR = 42103
    SHARDINGSPHERE_ERROR = 42104
    HOP_ERROR = 42105
    CUBE_STUDIO_ERROR = 42106

    # 系统错误 (50000-59999)
    INTERNAL_ERROR = 50000
    SERVICE_UNAVAILABLE = 50300
    GATEWAY_TIMEOUT = 50400


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应模型

    Attributes:
        code: 业务状态码，默认 20000 表示成功
        message: 提示信息
        data: 业务数据，可选
        timestamp: Unix 时间戳
    """

    code: int = Field(default=ErrorCode.SUCCESS, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="业务数据")
    timestamp: int = Field(
        default_factory=lambda: int(time.time()),
        description="响应时间戳"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 20000,
                    "message": "操作成功",
                    "data": {"id": 1, "name": "test"},
                    "timestamp": 1706659200,
                }
            ]
        }
    }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型

    Attributes:
        code: 业务状态码
        message: 提示信息
        data: 分页数据
        timestamp: 响应时间戳
    """

    code: int = Field(default=ErrorCode.SUCCESS, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: Optional["PageData"] = Field(default=None, description="分页数据")
    timestamp: int = Field(
        default_factory=lambda: int(time.time()),
        description="响应时间戳"
    )


class PageData(BaseModel, Generic[T]):
    """分页数据结构"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=10, description="每页大小")
    pages: int = Field(default=0, description="总页数")


# 便捷函数

def success(
    data: Any = None,
    message: str = "success",
    code: int = ErrorCode.SUCCESS,
) -> ApiResponse:
    """构造成功响应

    Args:
        data: 业务数据
        message: 提示信息
        code: 状态码

    Returns:
        API 响应对象
    """
    return ApiResponse(code=code, message=message, data=data)


def error(
    message: str,
    code: int = ErrorCode.INTERNAL_ERROR,
    data: Any = None,
) -> ApiResponse:
    """构造错误响应

    Args:
        message: 错误信息
        code: 错误码
        data: 附加数据

    Returns:
        API 响应对象
    """
    return ApiResponse(code=code, message=message, data=data)


def paginated(
    items: list[Any],
    total: int,
    page: int = 1,
    page_size: int = 10,
    message: str = "success",
) -> PaginatedResponse:
    """构造分页响应

    Args:
        items: 数据列表
        total: 总数
        page: 当前页码
        page_size: 每页大小
        message: 提示信息

    Returns:
        分页响应对象
    """
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedResponse(
        code=ErrorCode.SUCCESS,
        message=message,
        data=PageData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        ),
    )


# HTTP 状态码映射
HTTP_STATUS_MAP: dict[int, int] = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.CREATED: 201,
    ErrorCode.ACCEPTED: 202,
    ErrorCode.NO_CONTENT: 204,

    ErrorCode.INVALID_PARAMS: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.NOT_FOUND: 404,

    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.GATEWAY_TIMEOUT: 504,
}


def get_http_status(code: int) -> int:
    """获取业务状态码对应的 HTTP 状态码

    Args:
        code: 业务状态码

    Returns:
        HTTP 状态码
    """
    return HTTP_STATUS_MAP.get(code, 200)


# 错误信息映射
ERROR_MESSAGES: dict[int, str] = {
    ErrorCode.SUCCESS: "操作成功",
    ErrorCode.CREATED: "创建成功",
    ErrorCode.ACCEPTED: "请求已接受",
    ErrorCode.NO_CONTENT: "无数据",

    ErrorCode.INVALID_PARAMS: "参数错误",
    ErrorCode.MISSING_PARAM: "缺少必要参数",
    ErrorCode.INVALID_FORMAT: "格式错误",
    ErrorCode.VALIDATION_FAILED: "参数校验失败",

    ErrorCode.UNAUTHORIZED: "未授权",
    ErrorCode.TOKEN_EXPIRED: "Token 已过期",
    ErrorCode.TOKEN_INVALID: "Token 无效",
    ErrorCode.PERMISSION_DENIED: "权限不足",

    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.RESOURCE_NOT_FOUND: "资源不存在",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.CONFIG_NOT_FOUND: "配置不存在",

    ErrorCode.DUPLICATE_RESOURCE: "资源已存在",
    ErrorCode.OPERATION_NOT_ALLOWED: "操作不允许",
    ErrorCode.INVALID_STATE: "状态无效",
    ErrorCode.QUOTA_EXCEEDED: "超出配额",

    ErrorCode.EXTERNAL_SERVICE_ERROR: "外部服务错误",
    ErrorCode.DATABASE_ERROR: "数据库错误",
    ErrorCode.CACHE_ERROR: "缓存错误",
    ErrorCode.MESSAGE_QUEUE_ERROR: "消息队列错误",

    ErrorCode.SEATUNNEL_ERROR: "SeaTunnel 服务错误",
    ErrorCode.DATAHUB_ERROR: "DataHub 服务错误",
    ErrorCode.DOLPHINSCHEDULER_ERROR: "DolphinScheduler 服务错误",
    ErrorCode.SUPERSET_ERROR: "Superset 服务错误",
    ErrorCode.SHARDINGSPHERE_ERROR: "ShardingSphere 服务错误",
    ErrorCode.HOP_ERROR: "Hop 服务错误",
    ErrorCode.CUBE_STUDIO_ERROR: "Cube-Studio 服务错误",

    ErrorCode.INTERNAL_ERROR: "内部服务错误",
    ErrorCode.SERVICE_UNAVAILABLE: "服务不可用",
    ErrorCode.GATEWAY_TIMEOUT: "网关超时",
}


def get_error_message(code: int) -> str:
    """获取错误码对应的默认错误信息

    Args:
        code: 错误码

    Returns:
        错误信息
    """
    return ERROR_MESSAGES.get(code, "未知错误")
