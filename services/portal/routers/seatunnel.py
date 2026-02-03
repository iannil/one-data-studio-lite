"""SeaTunnel 代理路由 - 数据同步

提供统一的 REST API 接口，屏蔽底层 Hazelcast REST API 的差异。

API 规范:
    GET  /api/proxy/seatunnel/v1/jobs              # 获取任务列表
    GET  /api/proxy/seatunnel/v1/jobs/{id}         # 获取任务详情
    GET  /api/proxy/seatunnel/v1/jobs/{id}/status  # 获取任务状态
    POST /api/proxy/seatunnel/v1/jobs              # 提交新任务
    DELETE /api/proxy/seatunnel/v1/jobs/{id}       # 取消任务
    GET  /api/proxy/seatunnel/v1/cluster           # 获取集群状态

认证:
    - Portal 侧: 需要 Bearer Token（通过 get_current_user 依赖）
    - SeaTunnel 侧: 可选配置 API Key (SEA_TUNNEL_API_KEY)
"""


import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from services.common.api_response import (
    ApiResponse,
    ErrorCode,
    error,
    success,
)
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings

router = APIRouter(prefix="/api/proxy/seatunnel", tags=["SeaTunnel"])

# SeaTunnel Hazelcast REST API 端点
HAZELCAST_RUNNING_JOBS = "/hazelcast/rest/maps/running-jobs"
HAZELCAST_FINISHED_JOBS = "/hazelcast/rest/maps/finished-jobs"
HAZELCAST_JOB_INFO = "/hazelcast/rest/maps/job-info"
HAZELCAST_SUBMIT_JOB = "/hazelcast/rest/maps/submit-job"
HAZELCAST_CANCEL_JOB = "/hazelcast/rest/maps/cancel-job"
HAZELCAST_CLUSTER = "/hazelcast/rest/cluster"


async def fetch_seatunnel(
    path: str,
    method: str = "GET",
    json_data: dict | None = None,
) -> httpx.Response:
    """向 SeaTunnel Hazelcast REST API 发送请求

    Args:
        path: API 路径
        method: HTTP 方法
        json_data: 请求体数据

    Returns:
        HTTP 响应对象

    Raises:
        HTTPException: 连接失败或请求超时
    """
    url = f"{settings.SEATUNNEL_URL}{path}"

    # 构建请求头
    headers = {"Content-Type": "application/json"}
    if settings.SEA_TUNNEL_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SEA_TUNNEL_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                return await client.get(url, headers=headers)
            elif method == "POST":
                return await client.post(url, json=json_data, headers=headers)
            elif method == "DELETE":
                return await client.delete(url, headers=headers)
            else:
                return await client.request(method, url, json=json_data, headers=headers)
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail=f"SeaTunnel 请求超时: {str(e)}"
        )
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=503,
            detail=f"无法连接 SeaTunnel 服务: {str(e)}"
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"SeaTunnel 请求失败: {str(e)}"
        )


def _normalize_job(job: dict, status: str) -> dict:
    """标准化任务数据格式

    Args:
        job: 原始任务数据
        status: 任务状态

    Returns:
        标准化后的任务数据
    """
    if not isinstance(job, dict):
        return {}

    # 提取 job_id（可能在不同的字段）
    job_id = job.get("jobId") or job.get("job_id") or job.get("id")

    # 构建标准格式
    return {
        "jobId": job_id,
        "jobStatus": status,
        "jobName": job.get("jobName") or job.get("job_name") or job_id,
        "createTime": job.get("createTime") or job.get("create_time"),
        "updateTime": job.get("updateTime") or job.get("update_time"),
        # 原始数据（保留完整信息）
        "raw": job,
    }


@router.get(
    "/v1/jobs",
    response_model=ApiResponse,
    summary="获取任务列表",
    description="获取所有运行中和已完成的 SeaTunnel 任务"
)
async def list_jobs(
    status: str | None = None,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取任务列表

    Args:
        status: 过滤状态 (running/finished)，为空则返回全部
        user: 当前用户（通过认证依赖注入）

    Returns:
        包含任务列表的 ApiResponse
    """
    jobs = []

    # 获取运行中的任务
    if status is None or status == "running":
        try:
            running_resp = await fetch_seatunnel(HAZELCAST_RUNNING_JOBS)
            if running_resp.status_code == 200:
                running_data = running_resp.json()
                if isinstance(running_data, list):
                    jobs.extend(_normalize_job(job, "RUNNING") for job in running_data)
                elif isinstance(running_data, dict):
                    for job_id, job_info in running_data.items():
                        normalized = _normalize_job(
                            {"jobId": job_id, **(job_info if isinstance(job_info, dict) else {})},
                            "RUNNING"
                        )
                        jobs.append(normalized)
        except HTTPException as e:
            if e.status_code >= 500:
                return error(message=f"获取运行中任务失败: {e.detail}", code=ErrorCode.SEATUNNEL_ERROR)

    # 获取已完成的任务
    if status is None or status == "finished":
        try:
            finished_resp = await fetch_seatunnel(HAZELCAST_FINISHED_JOBS)
            if finished_resp.status_code == 200:
                finished_data = finished_resp.json()
                if isinstance(finished_data, list):
                    for job in finished_data:
                        job_status = job.get("jobStatus", "FINISHED")
                        jobs.append(_normalize_job(job, job_status))
                elif isinstance(finished_data, dict):
                    for job_id, job_info in finished_data.items():
                        if isinstance(job_info, dict):
                            job_status = job_info.get("jobStatus", "FINISHED")
                        else:
                            job_status = "FINISHED"
                        normalized = _normalize_job(
                            {"jobId": job_id, **(job_info if isinstance(job_info, dict) else {})},
                            job_status
                        )
                        jobs.append(normalized)
        except HTTPException as e:
            if e.status_code >= 500:
                return error(message=f"获取已完成任务失败: {e.detail}", code=ErrorCode.SEATUNNEL_ERROR)

    return success(data={"jobs": jobs, "total": len(jobs)})


@router.get(
    "/v1/jobs/{job_id}",
    response_model=ApiResponse,
    summary="获取任务详情",
    description="获取指定任务的详细信息"
)
async def get_job_detail(
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取任务详情

    Args:
        job_id: 任务 ID
        user: 当前用户

    Returns:
        包含任务详情的 ApiResponse
    """
    try:
        resp = await fetch_seatunnel(f"{HAZELCAST_JOB_INFO}/{job_id}")
        if resp.status_code == 200:
            job_data = resp.json()
            # 标准化返回格式
            return success(data={"jobId": job_id, "raw": job_data})
        return error(message="任务不存在", code=ErrorCode.NOT_FOUND)
    except HTTPException as e:
        return error(message=e.detail, code=ErrorCode.SEATUNNEL_ERROR)


@router.get(
    "/v1/jobs/{job_id}/status",
    response_model=ApiResponse,
    summary="获取任务状态",
    description="获取指定任务的当前状态"
)
async def get_job_status(
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取任务状态

    Args:
        job_id: 任务 ID
        user: 当前用户

    Returns:
        包含任务状态的 ApiResponse
    """
    # 先检查运行中的任务
    try:
        running_resp = await fetch_seatunnel(HAZELCAST_RUNNING_JOBS)
        if running_resp.status_code == 200:
            running_data = running_resp.json()
            found = False

            if isinstance(running_data, dict) and job_id in running_data:
                found = True
            elif isinstance(running_data, list):
                for job in running_data:
                    if str(job.get("jobId")) == job_id:
                        found = True
                        break

            if found:
                return success(data={"jobId": job_id, "jobStatus": "RUNNING"})
    except HTTPException:
        pass

    # 检查已完成的任务
    try:
        finished_resp = await fetch_seatunnel(HAZELCAST_FINISHED_JOBS)
        if finished_resp.status_code == 200:
            finished_data = finished_resp.json()
            found = False
            status = "FINISHED"

            if isinstance(finished_data, dict) and job_id in finished_data:
                found = True
                job_info = finished_data[job_id]
                if isinstance(job_info, dict):
                    status = job_info.get("jobStatus", "FINISHED")
            elif isinstance(finished_data, list):
                for job in finished_data:
                    if str(job.get("jobId")) == job_id:
                        found = True
                        status = job.get("jobStatus", "FINISHED")
                        break

            if found:
                return success(data={"jobId": job_id, "jobStatus": status})
    except HTTPException:
        pass

    return error(message="任务不存在", code=ErrorCode.NOT_FOUND)


@router.post(
    "/v1/jobs",
    response_model=ApiResponse,
    summary="提交新任务",
    description="提交一个新的 SeaTunnel 任务"
)
async def submit_job(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """提交新任务

    Args:
        request: FastAPI 请求对象
        user: 当前用户

    Returns:
        提交结果的 ApiResponse
    """
    try:
        body = await request.json()
        resp = await fetch_seatunnel(HAZELCAST_SUBMIT_JOB, method="POST", json_data=body)

        if resp.status_code == 200:
            result = resp.json()
            return success(data=result, message="任务提交成功")

        return error(message=f"任务提交失败: {resp.text}", code=ErrorCode.SEATUNNEL_ERROR)

    except ValueError:
        return error(message="请求体格式错误", code=ErrorCode.INVALID_FORMAT)
    except HTTPException as e:
        return error(message=e.detail, code=ErrorCode.SEATUNNEL_ERROR)


@router.delete(
    "/v1/jobs/{job_id}",
    response_model=ApiResponse,
    summary="取消任务",
    description="取消指定的运行中任务"
)
async def cancel_job(
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """取消任务

    Args:
        job_id: 任务 ID
        user: 当前用户

    Returns:
        取消结果的 ApiResponse
    """
    try:
        resp = await fetch_seatunnel(
            f"{HAZELCAST_CANCEL_JOB}/{job_id}",
            method="POST"
        )

        if resp.status_code == 200:
            return success(data={"jobId": job_id}, message="任务已取消")

        return error(message=f"取消任务失败: {resp.text}", code=ErrorCode.SEATUNNEL_ERROR)

    except HTTPException as e:
        return error(message=e.detail, code=ErrorCode.SEATUNNEL_ERROR)


@router.get(
    "/v1/cluster",
    response_model=ApiResponse,
    summary="获取集群状态",
    description="获取 SeaTunnel Hazelcast 集群状态"
)
async def get_cluster_status(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取集群状态

    Args:
        user: 当前用户

    Returns:
        集群状态的 ApiResponse
    """
    try:
        resp = await fetch_seatunnel(HAZELCAST_CLUSTER)
        if resp.status_code == 200:
            cluster_data = resp.json()
            return success(data=cluster_data)

        return error(message="获取集群状态失败", code=ErrorCode.SEATUNNEL_ERROR)

    except HTTPException as e:
        return error(message=e.detail, code=ErrorCode.SEATUNNEL_ERROR)


# 兼容旧版 API（保持向后兼容）
@router.get("/api/v1/job/list")
async def list_jobs_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取任务列表"""
    result = await list_jobs(status=None, user=user)
    # 转换为旧格式
    if result.code == ErrorCode.SUCCESS:
        return {"jobs": result.data.get("jobs", []), "total": result.data.get("total", 0)}
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/api/v1/job/{job_id}")
async def get_job_detail_legacy(job_id: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取任务详情"""
    result = await get_job_detail(job_id=job_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=404 if result.code == ErrorCode.NOT_FOUND else 500, detail=result.message)


@router.get("/api/v1/job/{job_id}/status")
async def get_job_status_legacy(job_id: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取任务状态"""
    result = await get_job_status(job_id=job_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=404 if result.code == ErrorCode.NOT_FOUND else 500, detail=result.message)


@router.post("/api/v1/job/submit")
async def submit_job_legacy(request: Request, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 提交任务"""
    result = await submit_job(request=request, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=500, detail=result.message)


@router.delete("/api/v1/job/{job_id}")
async def cancel_job_legacy(job_id: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 取消任务"""
    result = await cancel_job(job_id=job_id, user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/api/v1/cluster/status")
async def cluster_status_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 集群状态"""
    result = await get_cluster_status(user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=500, detail=result.message)
