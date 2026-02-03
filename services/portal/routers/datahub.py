"""DataHub 代理路由 - 元数据管理"""


import httpx
from fastapi import APIRouter, Depends, Request, Response

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

router = APIRouter(prefix="/api/proxy/datahub", tags=["DataHub"])


async def _datahub_request(
    path: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None,
) -> ApiResponse:
    """发起 DataHub 请求并返回统一格式响应

    Args:
        path: 请求路径
        method: HTTP 方法
        json_data: POST 请求体
        params: 查询参数

    Returns:
        统一格式的 API 响应
    """
    url = f"{settings.DATAHUB_GMS_URL}/{path.lstrip('/')}"
    headers = {
        "X-RestLi-Protocol-Version": "2.0.0",
    }
    if settings.DATAHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.DATAHUB_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data or {})
            else:
                return error(message="不支持的 HTTP 方法", code=ErrorCode.INVALID_PARAMS)

            if resp.status_code == 200:
                return success(data=resp.json())
            else:
                return error(
                    message=f"DataHub 请求失败: {resp.status_code}",
                    code=ErrorCode.DATAHUB_ERROR,
                )
    except Exception as e:
        return error(
            message=f"DataHub 服务异常: {str(e)}",
            code=ErrorCode.DATAHUB_ERROR,
        )


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/datasets", response_model=ApiResponse)
async def list_datasets_v1(
    query: str = "*",
    start: int = 0,
    count: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出数据集（v1 API）"""
    return await _datahub_request(
        path="entities?action=search",
        method="POST",
        json_data={
            "entity": "dataset",
            "input": query,
            "start": start,
            "count": count,
        },
    )


@router.get("/v1/entities", response_model=ApiResponse)
async def search_entities_v1(
    entity: str = "dataset",
    query: str = "*",
    start: int = 0,
    count: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """搜索 DataHub 实体（v1 API）"""
    return await _datahub_request(
        path="entities?action=search",
        method="POST",
        json_data={
            "entity": entity,
            "input": query,
            "start": start,
            "count": count,
        },
    )


@router.get("/v1/aspects", response_model=ApiResponse)
async def get_entity_aspect_v1(
    urn: str,
    aspect: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取实体详情（v1 API）"""
    return await _datahub_request(
        path="aspects/v1",
        method="GET",
        params={"urn": urn, "aspect": aspect},
    )


@router.get("/v1/relationships", response_model=ApiResponse)
async def get_lineage_v1(
    urn: str,
    direction: str = "OUTGOING",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取血缘关系（v1 API）"""
    if direction not in ("INCOMING", "OUTGOING"):
        return error(message="direction 必须是 INCOMING 或 OUTGOING", code=ErrorCode.INVALID_PARAMS)
    return await _datahub_request(
        path="relationships",
        method="GET",
        params={"urn": urn, "direction": direction},
    )


@router.post("/v1/tags", response_model=ApiResponse)
async def create_tag_v1(
    name: str,
    description: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建标签（v1 API）"""
    return await _datahub_request(
        path="entities?action=ingest",
        method="POST",
        json_data={
            "entity": {
                "value": {
                    "com.linkedin.tag.TagProperties": {
                        "name": name,
                        "description": description,
                    },
                },
            },
        },
    )


@router.get("/v1/tags/search", response_model=ApiResponse)
async def search_tags_v1(
    query: str = "*",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """搜索标签（v1 API）"""
    return await _datahub_request(
        path="entities?action=search",
        method="POST",
        json_data={
            "entity": "tag",
            "input": query,
            "start": 0,
            "count": 20,
        },
    )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def datahub_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 DataHub API 请求（旧版 API，向后兼容）"""
    extra_headers = {
        "X-RestLi-Protocol-Version": "2.0.0",
    }
    if settings.DATAHUB_TOKEN:
        extra_headers["Authorization"] = f"Bearer {settings.DATAHUB_TOKEN}"
    return await proxy_request(
        request=request,
        target_base_url=settings.DATAHUB_GMS_URL,
        target_path=path,
        extra_headers=extra_headers,
    )
