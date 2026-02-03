"""DolphinScheduler 代理路由 - 任务调度"""


import httpx
from fastapi import APIRouter, Depends, Request, Response

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

router = APIRouter(prefix="/api/proxy/dolphinscheduler", tags=["DolphinScheduler"])


async def _ds_request(
    path: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None,
) -> ApiResponse:
    """发起 DolphinScheduler 请求并返回统一格式响应

    Args:
        path: 请求路径（不含 /dolphinscheduler 前缀）
        method: HTTP 方法
        json_data: POST 请求体
        params: 查询参数

    Returns:
        统一格式的 API 响应
    """
    base_url = f"{settings.DOLPHINSCHEDULER_URL}/dolphinscheduler"
    url = f"{base_url}/{path.lstrip('/')}"
    headers = {}
    if settings.DOLPHINSCHEDULER_TOKEN:
        headers["token"] = settings.DOLPHINSCHEDULER_TOKEN

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data or {})
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers, params=params)
            else:
                return error(message="不支持的 HTTP 方法", code=ErrorCode.INVALID_PARAMS)

            # DolphinScheduler 返回格式：{"code": 0, "data": ..., "msg": "..."}
            ds_data = resp.json()
            if ds_data.get("code") == 0 or resp.status_code == 200:
                return success(data=ds_data.get("data"), message=ds_data.get("msg", "success"))
            else:
                return error(
                    message=ds_data.get("msg", f"DolphinScheduler 请求失败: {resp.status_code}"),
                    code=ErrorCode.DOLPHINSCHEDULER_ERROR,
                )
    except Exception as e:
        return error(
            message=f"DolphinScheduler 服务异常: {str(e)}",
            code=ErrorCode.DOLPHINSCHEDULER_ERROR,
        )


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/projects", response_model=ApiResponse)
async def get_projects_v1(
    pageNo: int = 1,
    pageSize: int = 100,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取项目列表（v1 API）"""
    return await _ds_request(
        path="projects",
        method="GET",
        params={"pageNo": pageNo, "pageSize": pageSize},
    )


@router.get("/v1/projects/{project_code}/process-definition", response_model=ApiResponse)
async def get_process_definitions_v1(
    project_code: str,
    pageNo: int = 1,
    pageSize: int = 20,
    searchVal: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取流程定义列表（v1 API）"""
    return await _ds_request(
        path=f"projects/{project_code}/process-definition",
        method="GET",
        params={"pageNo": pageNo, "pageSize": pageSize, "searchVal": searchVal},
    )


@router.get("/v1/projects/{project_code}/schedules", response_model=ApiResponse)
async def get_schedules_v1(
    project_code: str,
    processDefinitionCode: int | None = None,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取调度列表（v1 API）"""
    params = {}
    if processDefinitionCode is not None:
        params["processDefinitionCode"] = processDefinitionCode
    return await _ds_request(
        path=f"projects/{project_code}/schedules",
        method="GET",
        params=params if params else None,
    )


@router.post("/v1/projects/{project_code}/schedules/{schedule_id}/online", response_model=ApiResponse)
async def update_schedule_state_v1(
    project_code: str,
    schedule_id: int,
    releaseState: str = "ONLINE",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """上线/下线调度（v1 API）"""
    if releaseState not in ("ONLINE", "OFFLINE"):
        return error(message="releaseState 必须是 ONLINE 或 OFFLINE", code=ErrorCode.INVALID_PARAMS)
    return await _ds_request(
        path=f"projects/{project_code}/schedules/{schedule_id}/online",
        method="POST",
        params={"releaseState": releaseState},
    )


@router.get("/v1/projects/{project_code}/task-instances", response_model=ApiResponse)
async def get_task_instances_v1(
    project_code: str,
    pageNo: int = 1,
    pageSize: int = 20,
    stateType: str = "",
    searchVal: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取任务实例列表（v1 API）"""
    return await _ds_request(
        path=f"projects/{project_code}/task-instances",
        method="GET",
        params={"pageNo": pageNo, "pageSize": pageSize, "stateType": stateType, "searchVal": searchVal},
    )


@router.get("/v1/projects/{project_code}/task-instances/{task_instance_id}/log", response_model=ApiResponse)
async def get_task_log_v1(
    project_code: str,
    task_instance_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取任务实例日志（v1 API）"""
    return await _ds_request(
        path=f"projects/{project_code}/task-instances/{task_instance_id}/log",
        method="GET",
    )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ds_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 DolphinScheduler API 请求（旧版 API，向后兼容）"""
    extra_headers = {}
    if settings.DOLPHINSCHEDULER_TOKEN:
        extra_headers["token"] = settings.DOLPHINSCHEDULER_TOKEN
    return await proxy_request(
        request=request,
        target_base_url=f"{settings.DOLPHINSCHEDULER_URL}/dolphinscheduler",
        target_path=path,
        extra_headers=extra_headers if extra_headers else None,
    )
