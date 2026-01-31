"""NL2SQL 代理路由 - 自然语言查询"""

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

# 服务间通信密钥
SERVICE_SECRET = os.environ.get("SERVICE_SECRET", "internal-service-secret-dev-do-not-use-in-prod")

router = APIRouter(prefix="/api/proxy/nl2sql", tags=["NL2SQL"])


# ============================================================
# 请求模型
# ============================================================

class QueryRequest(BaseModel):
    query: str
    database: Optional[str] = None
    context: Optional[str] = None


class ExplainRequest(BaseModel):
    sql: str
    database: Optional[str] = None


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.post("/v1/query", response_model=ApiResponse)
async def query_v1(
    request: QueryRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """自然语言查询（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.NL2SQL_URL}/api/nl2sql/query",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"NL2SQL 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"NL2SQL 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/explain", response_model=ApiResponse)
async def explain_v1(
    request: ExplainRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """SQL 解释（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.NL2SQL_URL}/api/nl2sql/explain",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"NL2SQL 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"NL2SQL 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/tables", response_model=ApiResponse)
async def get_tables_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取表列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.NL2SQL_URL}/api/nl2sql/tables",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"NL2SQL 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"NL2SQL 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def nl2sql_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 NL2SQL 服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.NL2SQL_URL,
        target_path=path,
    )
