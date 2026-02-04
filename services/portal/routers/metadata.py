"""元数据代理路由 - OpenMetadata 适配

替代原 DataHub 接口，适配 OpenMetadata API。
保留原有接口签名以确保向后兼容。

OpenMetadata API 映射:
| 功能 | DataHub API | OpenMetadata API |
|------|-------------|------------------|
| 搜索实体 | POST /entities?action=search | GET /api/v1/search/query |
| 获取 Schema | GET /aspects/v1?aspect=schemaMetadata | GET /api/v1/tables/{fqn} |
| 获取血缘 | GET /relationships | GET /api/v1/lineage/{fqn} |
| 创建标签 | POST /entities?action=ingest | POST /api/v1/tags |
"""

from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Request, Response

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

router = APIRouter(prefix="/api/proxy/datahub", tags=["Metadata"])


def _get_openmetadata_headers() -> dict:
    """获取 OpenMetadata 请求头"""
    headers = {
        "Content-Type": "application/json",
    }
    token = getattr(settings, 'OPENMETADATA_JWT_TOKEN', '') or settings.DATAHUB_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_openmetadata_url() -> str:
    """获取 OpenMetadata API URL"""
    return getattr(settings, 'OPENMETADATA_API_URL', None) or settings.DATAHUB_GMS_URL


async def _openmetadata_request(
    path: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None,
) -> ApiResponse:
    """发起 OpenMetadata 请求并返回统一格式响应

    Args:
        path: 请求路径
        method: HTTP 方法
        json_data: POST 请求体
        params: 查询参数

    Returns:
        统一格式的 API 响应
    """
    base_url = _get_openmetadata_url()
    url = f"{base_url}/{path.lstrip('/')}"
    headers = _get_openmetadata_headers()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data or {})
            elif method.upper() == "PUT":
                resp = await client.put(url, headers=headers, json=json_data or {})
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers, params=params)
            else:
                return error(message="不支持的 HTTP 方法", code=ErrorCode.INVALID_PARAMS)

            if resp.status_code in (200, 201):
                return success(data=resp.json())
            elif resp.status_code == 404:
                return error(
                    message="资源不存在",
                    code=ErrorCode.NOT_FOUND,
                )
            else:
                return error(
                    message=f"元数据服务请求失败: {resp.status_code}",
                    code=ErrorCode.OPENMETADATA_ERROR,
                )
    except httpx.TimeoutException:
        return error(
            message="元数据服务请求超时",
            code=ErrorCode.GATEWAY_TIMEOUT,
        )
    except Exception as e:
        return error(
            message=f"元数据服务异常: {str(e)}",
            code=ErrorCode.OPENMETADATA_ERROR,
        )


def _convert_entity_type(entity: str) -> str:
    """将 DataHub 实体类型转换为 OpenMetadata 类型"""
    type_map = {
        "dataset": "table",
        "dataFlow": "pipeline",
        "dataJob": "pipeline",
        "dashboard": "dashboard",
        "chart": "chart",
        "tag": "tag",
        "glossaryTerm": "glossaryTerm",
    }
    return type_map.get(entity, entity)


def _convert_om_to_datahub_entity(om_entity: dict, entity_type: str) -> dict:
    """将 OpenMetadata 实体转换为 DataHub 格式（兼容前端）"""
    fqn = om_entity.get("fullyQualifiedName", "")
    name = om_entity.get("name", "")
    service_type = om_entity.get("serviceType", "")

    # 构造兼容 DataHub 的 URN 格式
    if entity_type == "table":
        platform = service_type.lower() if service_type else "unknown"
        urn = f"urn:li:dataset:(urn:li:dataPlatform:{platform},{fqn},PROD)"
    elif entity_type == "tag":
        urn = f"urn:li:tag:{name}"
    else:
        urn = f"urn:li:{entity_type}:{fqn}"

    return {
        "urn": urn,
        "type": entity_type,
        "name": name,
        "description": om_entity.get("description", ""),
        "platform": service_type.lower() if service_type else None,
        "status": "ACTIVE",
        # OpenMetadata 原始数据
        "_openmetadata": {
            "id": om_entity.get("id"),
            "fqn": fqn,
        },
    }


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
    """列出数据集（v1 API）

    使用 OpenMetadata Search API 搜索 tables。
    """
    return await search_entities_v1(
        entity="dataset",
        query=query,
        start=start,
        count=count,
        user=user,
    )


@router.get("/v1/entities", response_model=ApiResponse)
async def search_entities_v1(
    entity: str = "dataset",
    query: str = "*",
    start: int = 0,
    count: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """搜索实体（v1 API）

    OpenMetadata Search API:
    GET /api/v1/search/query?q=<query>&index=<entity>&from=<start>&size=<count>
    """
    om_entity_type = _convert_entity_type(entity)

    # 构造 OpenMetadata 搜索参数
    search_params = {
        "q": query if query != "*" else "",
        "index": f"{om_entity_type}_search_index",
        "from": start,
        "size": count,
    }

    result = await _openmetadata_request(
        path="search/query",
        method="GET",
        params=search_params,
    )

    if result.code != ErrorCode.SUCCESS:
        return result

    # 转换 OpenMetadata 响应为 DataHub 格式
    om_data = result.data or {}
    hits = om_data.get("hits", {}).get("hits", [])

    entities = []
    for hit in hits:
        source = hit.get("_source", {})
        entities.append(_convert_om_to_datahub_entity(source, om_entity_type))

    total = om_data.get("hits", {}).get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else total

    return success(data={
        "entities": entities,
        "results": entities,  # 兼容旧格式
        "start": start,
        "count": len(entities),
        "total": total_count,
    })


@router.get("/v1/aspects", response_model=ApiResponse)
async def get_entity_aspect_v1(
    urn: str,
    aspect: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取实体详情（v1 API）

    OpenMetadata:
    GET /api/v1/tables/{fqn}
    GET /api/v1/tables/{fqn}/columns
    """
    # 从 URN 解析 FQN
    fqn = _parse_fqn_from_urn(urn)
    if not fqn:
        return error(message="无效的 URN 格式", code=ErrorCode.INVALID_PARAMS)

    # 获取表信息（包含 schema）
    result = await _openmetadata_request(
        path=f"tables/name/{quote(fqn, safe='')}",
        method="GET",
        params={"fields": "columns,tags"},
    )

    if result.code != ErrorCode.SUCCESS:
        return result

    om_table = result.data or {}

    # 转换为 DataHub schemaMetadata 格式
    columns = om_table.get("columns", [])
    fields = []
    for col in columns:
        fields.append({
            "fieldPath": col.get("name", ""),
            "nativeDataType": col.get("dataType", ""),
            "type": col.get("dataType", ""),
            "description": col.get("description", ""),
            "nullable": col.get("constraint") != "NOT_NULL",
            "tags": [t.get("tagFQN", "") for t in col.get("tags", [])],
        })

    return success(data={
        "urn": urn,
        "aspect": aspect,
        "schemaMetadata": {
            "schemaName": om_table.get("name", ""),
            "platform": om_table.get("serviceType", "").lower(),
            "fields": fields,
        },
        "fields": fields,  # 兼容旧格式
    })


@router.get("/v1/relationships", response_model=ApiResponse)
async def get_lineage_v1(
    urn: str,
    direction: str = "OUTGOING",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取血缘关系（v1 API）

    OpenMetadata:
    GET /api/v1/lineage/{fqn}
    """
    if direction not in ("INCOMING", "OUTGOING"):
        return error(message="direction 必须是 INCOMING 或 OUTGOING", code=ErrorCode.INVALID_PARAMS)

    fqn = _parse_fqn_from_urn(urn)
    if not fqn:
        return error(message="无效的 URN 格式", code=ErrorCode.INVALID_PARAMS)

    # 获取血缘信息
    result = await _openmetadata_request(
        path=f"lineage/table/name/{quote(fqn, safe='')}",
        method="GET",
        params={"upstreamDepth": 3, "downstreamDepth": 3},
    )

    if result.code != ErrorCode.SUCCESS:
        # 如果没有血缘数据，返回空列表而不是错误
        if result.code == ErrorCode.NOT_FOUND:
            return success(data={
                "urn": urn,
                "relationships": [],
            })
        return result

    om_lineage = result.data or {}

    # 转换为 DataHub relationships 格式
    relationships = []
    nodes = om_lineage.get("nodes", [])
    edges = om_lineage.get("edges", [])

    # 构建节点 ID 到 FQN 的映射
    node_map = {node.get("id"): node for node in nodes}

    for edge in edges:
        from_node = edge.get("fromEntity", {})
        to_node = edge.get("toEntity", {})

        if direction == "INCOMING":
            # 上游依赖：找到指向当前节点的边
            if to_node.get("fqn") == fqn:
                from_fqn = from_node.get("fqn", "")
                relationships.append({
                    "entity": from_node.get("type", "table"),
                    "urn": f"urn:li:dataset:(urn:li:dataPlatform:unknown,{from_fqn},PROD)",
                    "type": "DownstreamOf",
                })
        else:  # OUTGOING
            # 下游影响：找到从当前节点出发的边
            if from_node.get("fqn") == fqn:
                to_fqn = to_node.get("fqn", "")
                relationships.append({
                    "entity": to_node.get("type", "table"),
                    "urn": f"urn:li:dataset:(urn:li:dataPlatform:unknown,{to_fqn},PROD)",
                    "type": "UpstreamOf",
                })

    return success(data={
        "urn": urn,
        "relationships": relationships,
    })


@router.post("/v1/tags", response_model=ApiResponse)
async def create_tag_v1(
    name: str,
    description: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建标签（v1 API）

    OpenMetadata:
    POST /api/v1/tags
    """
    # 首先获取或创建标签分类
    classification_name = "user_tags"  # 用户自定义标签分类

    # 创建标签
    result = await _openmetadata_request(
        path="tags",
        method="POST",
        json_data={
            "name": name,
            "description": description,
            "classification": classification_name,
        },
    )

    if result.code != ErrorCode.SUCCESS:
        return result

    return success(data={
        "urn": f"urn:li:tag:{name}",
        "name": name,
        "description": description,
    })


@router.get("/v1/tags/search", response_model=ApiResponse)
async def search_tags_v1(
    query: str = "*",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """搜索标签（v1 API）

    OpenMetadata:
    GET /api/v1/tags
    """
    params = {"limit": 100}
    if query and query != "*":
        params["fields"] = "name,description"

    result = await _openmetadata_request(
        path="tags",
        method="GET",
        params=params,
    )

    if result.code != ErrorCode.SUCCESS:
        return result

    om_tags = result.data or {}
    tags_list = om_tags.get("data", []) if isinstance(om_tags, dict) else []

    entities = []
    for tag in tags_list:
        tag_name = tag.get("name", "")
        # 简单过滤
        if query and query != "*" and query.lower() not in tag_name.lower():
            continue
        entities.append({
            "urn": f"urn:li:tag:{tag_name}",
            "type": "tag",
            "name": tag_name,
            "description": tag.get("description", ""),
        })

    return success(data={
        "entities": entities,
        "results": entities,
        "total": len(entities),
    })


# ============================================================
# 辅助函数
# ============================================================

def _parse_fqn_from_urn(urn: str) -> str | None:
    """从 DataHub URN 解析出 FQN

    URN 格式: urn:li:dataset:(urn:li:dataPlatform:<platform>,<fqn>,<env>)
    """
    if not urn or not urn.startswith("urn:li:"):
        return None

    # 简单解析：提取括号内的第二部分
    try:
        if "dataset:" in urn:
            # 提取 (platform,fqn,env) 部分
            inner = urn.split("(")[1].rstrip(")")
            parts = inner.split(",")
            if len(parts) >= 2:
                return parts[1]  # 返回 fqn 部分
        elif "tag:" in urn:
            return urn.split("tag:")[1]
    except (IndexError, ValueError):
        pass

    return None


# ============================================================
# 旧版 API（向后兼容，直接代理到 OpenMetadata）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def metadata_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理元数据 API 请求（旧版 API，向后兼容）

    直接代理到 OpenMetadata API。
    """
    return await proxy_request(
        request=request,
        target_base_url=_get_openmetadata_url(),
        target_path=path,
        extra_headers=_get_openmetadata_headers(),
    )
