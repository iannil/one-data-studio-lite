"""Metadata Sync 代理路由 - 元数据同步"""

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

router = APIRouter(prefix="/api/proxy/metadata-sync", tags=["Metadata Sync"])


# ============================================================
# 请求模型
# ============================================================

class ETLMappingBase(BaseModel):
    source_urn: str
    target_task_type: str  # dolphinscheduler, seatunnel, hop
    target_task_id: str
    trigger_on: list[str]  # CREATE, UPDATE, DELETE, SCHEMA_CHANGE
    auto_update_config: bool = True
    description: Optional[str] = None
    enabled: bool = True


class ETLMappingCreate(ETLMappingBase):
    pass


class ETLMappingUpdate(BaseModel):
    target_task_type: Optional[str] = None
    target_task_id: Optional[str] = None
    trigger_on: Optional[list[str]] = None
    auto_update_config: Optional[bool] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class MetadataChangeEvent(BaseModel):
    entity_urn: str
    change_type: str  # CREATE, UPDATE, DELETE, SCHEMA_CHANGE
    changed_fields: Optional[list[str]] = None
    new_schema: Optional[dict] = None


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/mappings", response_model=ApiResponse)
async def get_mappings_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取所有元数据映射规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.METADATA_SYNC_URL}/api/metadata/mappings",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/mappings/{mapping_id}", response_model=ApiResponse)
async def get_mapping_v1(
    mapping_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取单个映射规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.METADATA_SYNC_URL}/api/metadata/mappings/{mapping_id}",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/mappings", response_model=ApiResponse)
async def create_mapping_v1(
    mapping: ETLMappingCreate,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建映射规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.METADATA_SYNC_URL}/api/metadata/mappings",
                headers={"X-Service-Secret": SERVICE_SECRET},
                json=mapping.model_dump(),
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.put("/v1/mappings/{mapping_id}", response_model=ApiResponse)
async def update_mapping_v1(
    mapping_id: str,
    mapping: ETLMappingUpdate,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """更新映射规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{settings.METADATA_SYNC_URL}/api/metadata/mappings/{mapping_id}",
                headers={"X-Service-Secret": SERVICE_SECRET},
                json=mapping.model_dump(exclude_none=True),
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.delete("/v1/mappings/{mapping_id}", response_model=ApiResponse)
async def delete_mapping_v1(
    mapping_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """删除映射规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{settings.METADATA_SYNC_URL}/api/metadata/mappings/{mapping_id}",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/sync", response_model=ApiResponse)
async def trigger_sync_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """手动触发全量元数据同步（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.METADATA_SYNC_URL}/api/metadata/sync",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/webhook", response_model=ApiResponse)
async def send_metadata_event_v1(
    event: MetadataChangeEvent,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """发送元数据变更事件（模拟 DataHub Webhook）（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.METADATA_SYNC_URL}/api/metadata/webhook",
                headers={"X-Service-Secret": SERVICE_SECRET},
                json=event.model_dump(),
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"元数据同步服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"元数据同步服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def metadata_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理元数据同步服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.METADATA_SYNC_URL,
        target_path=path,
    )
