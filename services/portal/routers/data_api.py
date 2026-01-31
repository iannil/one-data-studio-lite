"""Data API 代理路由 - 数据资产 API 网关"""

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

router = APIRouter(prefix="/api/proxy/data-api", tags=["Data API"])


# ============================================================
# 请求模型
# ============================================================

class QueryDatasetRequest(BaseModel):
    sql: Optional[str] = None
    limit: Optional[int] = 100


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/assets/search", response_model=ApiResponse)
async def search_assets_v1(
    keyword: str = "",
    type: str = "",
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """搜索数据资产（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.DATA_API_URL}/api/assets/search",
                headers={"X-Service-Secret": SERVICE_SECRET},
                params={"keyword": keyword, "type": type, "page": page, "page_size": page_size},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/assets/{asset_id}", response_model=ApiResponse)
async def get_asset_detail_v1(
    asset_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取资产详情（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.DATA_API_URL}/api/assets/{asset_id}",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/data/{dataset_id}/schema", response_model=ApiResponse)
async def get_dataset_schema_v1(
    dataset_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据集 Schema（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.DATA_API_URL}/api/data/{dataset_id}/schema",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/data/{dataset_id}/query", response_model=ApiResponse)
async def query_dataset_v1(
    dataset_id: str,
    request: QueryDatasetRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """自定义查询（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.DATA_API_URL}/api/data/{dataset_id}/query",
                headers={"X-Service-Secret": SERVICE_SECRET},
                json=request.model_dump(),
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/data/{dataset_id}/subscribe", response_model=ApiResponse)
async def subscribe_dataset_v1(
    dataset_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """订阅数据集（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.DATA_API_URL}/api/data/{dataset_id}/subscribe",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/subscriptions", response_model=ApiResponse)
async def get_subscriptions_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取订阅列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.DATA_API_URL}/api/subscriptions",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Data API 服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Data API 服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def data_api_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 Data API 服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.DATA_API_URL,
        target_path=path,
    )
