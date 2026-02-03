"""Apache Hop 代理路由 - ETL 工作流与管道管理

通过 Hop Server REST API 管理和执行 ETL 任务。

API 规范:
    GET  /api/proxy/hop/v1/workflows                    # 获取工作流列表
    GET  /api/proxy/hop/v1/workflows/{name}             # 获取工作流详情
    POST /api/proxy/hop/v1/workflows/{name}/run         # 执行工作流
    GET  /api/proxy/hop/v1/workflows/{name}/status/{id} # 获取工作流状态
    POST /api/proxy/hop/v1/workflows/{name}/stop/{id}   # 停止工作流
    GET  /api/proxy/hop/v1/pipelines                    # 获取管道列表
    GET  /api/proxy/hop/v1/pipelines/{name}             # 获取管道详情
    POST /api/proxy/hop/v1/pipelines/{name}/run         # 执行管道
    GET  /api/proxy/hop/v1/pipelines/{name}/status/{id} # 获取管道状态
    POST /api/proxy/hop/v1/pipelines/{name}/stop/{id}   # 停止管道
    GET  /api/proxy/hop/v1/server/status                # 获取服务器状态
    GET  /api/proxy/hop/v1/server/info                   # 获取服务器信息
    GET  /api/proxy/hop/v1/run-configurations           # 获取运行配置

认证: 需要 Bearer Token（通过 get_current_user 依赖）
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.common.api_response import (
    ApiResponse,
    ErrorCode,
    error,
    success,
)
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy/hop", tags=["ApacheHop"])


class RunRequest(BaseModel):
    """执行请求"""
    run_configuration: str = "local"
    parameters: dict | None = None
    variables: dict | None = None


class PipelineRequest(BaseModel):
    """管道执行请求"""
    name: str
    run_configuration: str = "local"
    parameters: dict | None = None


async def fetch_hop(
    path: str,
    method: str = "GET",
    data: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    """向 Hop Server REST API 发请求

    Args:
        path: API 路径
        method: HTTP 方法
        data: 请求体数据
        params: 查询参数

    Returns:
        HTTP 响应
    """
    url = f"{settings.HOP_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if method == "GET":
                return await client.get(url, params=params)
            elif method == "POST":
                return await client.post(url, json=data, params=params)
            elif method == "DELETE":
                return await client.delete(url, params=params)
            else:
                return await client.request(method, url, json=data, params=params)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Hop 请求超时")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接 Hop Server")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Hop 请求失败: {str(e)}")


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

# ------------------------------------------------------------
# 工作流管理
# ------------------------------------------------------------

@router.get(
    "/v1/workflows",
    response_model=ApiResponse,
    summary="获取工作流列表",
    description="列出所有工作流"
)
async def list_workflows_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出所有工作流"""
    try:
        resp = await fetch_hop("/hop/api/workflows")
        if resp.status_code == 200:
            data = resp.json()
            workflows = data if isinstance(data, list) else []
            return success(data={"workflows": workflows, "total": len(workflows)})
        return error(message="获取工作流列表失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.get(
    "/v1/workflows/{name}",
    response_model=ApiResponse,
    summary="获取工作流详情",
    description="获取指定工作流的详细信息"
)
async def get_workflow_v1(
    name: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取工作流详情"""
    try:
        resp = await fetch_hop(f"/hop/api/workflows/{name}")
        if resp.status_code == 200:
            return success(data={"name": name, "detail": resp.json()})
        return error(message="工作流不存在", code=ErrorCode.NOT_FOUND)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.post(
    "/v1/workflows/{name}/run",
    response_model=ApiResponse,
    summary="执行工作流",
    description="执行指定的工作流"
)
async def run_workflow_v1(
    name: str,
    req: RunRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """执行工作流"""
    try:
        data = {"runConfigurationName": req.run_configuration}
        if req.parameters:
            data["parameters"] = req.parameters
        if req.variables:
            data["variables"] = req.variables

        resp = await fetch_hop(f"/hop/api/workflows/{name}/run", method="POST", data=data)
        if resp.status_code == 200:
            result = resp.json()
            execution_id = result.get("id") or result.get("executionId")
            return success(
                data={"name": name, "execution_id": execution_id, "details": result},
                message=f"工作流 {name} 已启动"
            )
        return error(message="执行工作流失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.get(
    "/v1/workflows/{name}/status/{execution_id}",
    response_model=ApiResponse,
    summary="获取工作流执行状态",
    description="获取工作流的执行状态"
)
async def get_workflow_status_v1(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取工作流执行状态"""
    try:
        resp = await fetch_hop(f"/hop/api/workflows/{name}/status/{execution_id}")
        if resp.status_code == 200:
            return success(data={"name": name, "execution_id": execution_id, "status": resp.json()})
        return error(message="获取状态失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.post(
    "/v1/workflows/{name}/stop/{execution_id}",
    response_model=ApiResponse,
    summary="停止工作流执行",
    description="停止正在执行的工作流"
)
async def stop_workflow_v1(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """停止工作流执行"""
    try:
        resp = await fetch_hop(f"/hop/api/workflows/{name}/stop/{execution_id}", method="POST")
        if resp.status_code == 200:
            return success(
                data={"name": name, "execution_id": execution_id},
                message=f"工作流执行 {execution_id} 已停止"
            )
        return error(message="停止工作流失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


# ------------------------------------------------------------
# 管道管理
# ------------------------------------------------------------

@router.get(
    "/v1/pipelines",
    response_model=ApiResponse,
    summary="获取管道列表",
    description="列出所有管道"
)
async def list_pipelines_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出所有管道"""
    try:
        resp = await fetch_hop("/hop/api/pipelines")
        if resp.status_code == 200:
            data = resp.json()
            pipelines = data if isinstance(data, list) else []
            return success(data={"pipelines": pipelines, "total": len(pipelines)})
        return error(message="获取管道列表失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.get(
    "/v1/pipelines/{name}",
    response_model=ApiResponse,
    summary="获取管道详情",
    description="获取指定管道的详细信息"
)
async def get_pipeline_v1(
    name: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取管道详情"""
    try:
        resp = await fetch_hop(f"/hop/api/pipelines/{name}")
        if resp.status_code == 200:
            return success(data={"name": name, "detail": resp.json()})
        return error(message="管道不存在", code=ErrorCode.NOT_FOUND)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.post(
    "/v1/pipelines/{name}/run",
    response_model=ApiResponse,
    summary="执行管道",
    description="执行指定的管道"
)
async def run_pipeline_v1(
    name: str,
    req: RunRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """执行管道"""
    try:
        data = {"runConfigurationName": req.run_configuration}
        if req.parameters:
            data["parameters"] = req.parameters
        if req.variables:
            data["variables"] = req.variables

        resp = await fetch_hop(f"/hop/api/pipelines/{name}/run", method="POST", data=data)
        if resp.status_code == 200:
            result = resp.json()
            execution_id = result.get("id") or result.get("executionId")
            return success(
                data={"name": name, "execution_id": execution_id, "details": result},
                message=f"管道 {name} 已启动"
            )
        return error(message="执行管道失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.get(
    "/v1/pipelines/{name}/status/{execution_id}",
    response_model=ApiResponse,
    summary="获取管道执行状态",
    description="获取管道的执行状态"
)
async def get_pipeline_status_v1(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取管道执行状态"""
    try:
        resp = await fetch_hop(f"/hop/api/pipelines/{name}/status/{execution_id}")
        if resp.status_code == 200:
            return success(data={"name": name, "execution_id": execution_id, "status": resp.json()})
        return error(message="获取状态失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


@router.post(
    "/v1/pipelines/{name}/stop/{execution_id}",
    response_model=ApiResponse,
    summary="停止管道执行",
    description="停止正在执行的管道"
)
async def stop_pipeline_v1(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """停止管道执行"""
    try:
        resp = await fetch_hop(f"/hop/api/pipelines/{name}/stop/{execution_id}", method="POST")
        if resp.status_code == 200:
            return success(
                data={"name": name, "execution_id": execution_id},
                message=f"管道执行 {execution_id} 已停止"
            )
        return error(message="停止管道失败", code=ErrorCode.HOP_ERROR)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return error(message=f"Hop Server 连接失败: {str(e)}", code=ErrorCode.HOP_ERROR)


# ------------------------------------------------------------
# 服务器状态
# ------------------------------------------------------------

@router.get(
    "/v1/server/status",
    response_model=ApiResponse,
    summary="获取服务器状态",
    description="获取 Hop Server 的状态信息"
)
async def server_status_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Hop Server 状态"""
    try:
        resp = await fetch_hop("/hop/api/status")
        if resp.status_code == 200:
            return success(data={"status": "online", "detail": resp.json()})
        return success(data={"status": "unknown"}, message="无法获取服务器状态")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return success(data={"status": "offline", "error": str(e)})


@router.get(
    "/v1/server/info",
    response_model=ApiResponse,
    summary="获取服务器信息",
    description="获取 Hop Server 的版本和配置信息"
)
async def server_info_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Hop Server 信息"""
    try:
        resp = await fetch_hop("/hop/api/info")
        if resp.status_code == 200:
            return success(data=resp.json())
        return success(data={"version": "unknown"}, message="无法获取服务器信息")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return success(data={"version": "unknown", "error": str(e)})


# ------------------------------------------------------------
# 运行配置
# ------------------------------------------------------------

@router.get(
    "/v1/run-configurations",
    response_model=ApiResponse,
    summary="获取运行配置",
    description="列出可用的运行配置"
)
async def list_run_configurations_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出可用的运行配置"""
    try:
        resp = await fetch_hop("/hop/api/run-configurations")
        if resp.status_code == 200:
            data = resp.json()
            configs = data if isinstance(data, list) else []
            return success(data={"configurations": configs})
        # 返回默认配置
        return success(data={
            "configurations": [{"name": "local", "description": "本地执行"}]
        })
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Hop 连接失败: {e}")
        return success(data={
            "configurations": [{"name": "local", "description": "本地执行"}],
            "error": str(e),
        })


# ============================================================
# 旧版 API（向后兼容，逐步废弃）
# ============================================================

@router.get("/workflows")
async def list_workflows_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取工作流列表"""
    result = await list_workflows_v1(user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "workflows": result.data.get("workflows", []),
            "total": result.data.get("total", 0)
        }
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/workflows/{name}")
async def get_workflow_legacy(name: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取工作流详情"""
    result = await get_workflow_v1(name=name, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data.get("detail")
    raise HTTPException(status_code=404, detail=result.message)


@router.post("/workflows/{name}/run")
async def run_workflow_legacy(name: str, req: RunRequest, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 执行工作流"""
    result = await run_workflow_v1(name=name, req=req, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": True,
            "message": result.message,
            "execution_id": result.data.get("execution_id"),
            "details": result.data.get("details"),
        }
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/workflows/{name}/status/{execution_id}")
async def get_workflow_status_legacy(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 获取工作流执行状态"""
    result = await get_workflow_status_v1(name=name, execution_id=execution_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data.get("status")
    raise HTTPException(status_code=500, detail=result.message)


@router.post("/workflows/{name}/stop/{execution_id}")
async def stop_workflow_legacy(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 停止工作流执行"""
    result = await stop_workflow_v1(name=name, execution_id=execution_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {"success": True, "message": result.message}
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/pipelines")
async def list_pipelines_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取管道列表"""
    result = await list_pipelines_v1(user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "pipelines": result.data.get("pipelines", []),
            "total": result.data.get("total", 0)
        }
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/pipelines/{name}")
async def get_pipeline_legacy(name: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取管道详情"""
    result = await get_pipeline_v1(name=name, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data.get("detail")
    raise HTTPException(status_code=404, detail=result.message)


@router.post("/pipelines/{name}/run")
async def run_pipeline_legacy(name: str, req: RunRequest, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 执行管道"""
    result = await run_pipeline_v1(name=name, req=req, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": True,
            "message": result.message,
            "execution_id": result.data.get("execution_id"),
            "details": result.data.get("details"),
        }
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/pipelines/{name}/status/{execution_id}")
async def get_pipeline_status_legacy(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 获取管道执行状态"""
    result = await get_pipeline_status_v1(name=name, execution_id=execution_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data.get("status")
    raise HTTPException(status_code=500, detail=result.message)


@router.post("/pipelines/{name}/stop/{execution_id}")
async def stop_pipeline_legacy(
    name: str,
    execution_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 停止管道执行"""
    result = await stop_pipeline_v1(name=name, execution_id=execution_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {"success": True, "message": result.message}
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/server/status")
async def server_status_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取服务器状态"""
    result = await server_status_v1(user=user)
    return result.data


@router.get("/server/info")
async def server_info_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取服务器信息"""
    result = await server_info_v1(user=user)
    return result.data


@router.get("/run-configurations")
async def list_run_configurations_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取运行配置"""
    result = await list_run_configurations_v1(user=user)
    return result.data
