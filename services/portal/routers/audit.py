"""Audit Log 代理路由 - 审计日志"""

import os

import httpx
from fastapi import APIRouter, Depends, Request, Response

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

# 服务间通信密钥
SERVICE_SECRET = os.environ.get("SERVICE_SECRET", "internal-service-secret-dev-do-not-use-in-prod")

router = APIRouter(prefix="/api/proxy/audit", tags=["Audit Log"])


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/logs", response_model=ApiResponse)
async def get_logs_v1(
    subsystem: str = "",
    event_type: str = "",
    user: str = "",
    page: int = 1,
    page_size: int = 50,
    user_info: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """查询审计日志（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.AUDIT_LOG_URL}/api/audit/logs",
                params={
                    "subsystem": subsystem,
                    "event_type": event_type,
                    "user": user,
                    "page": page,
                    "page_size": page_size,
                },
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"审计日志服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"审计日志服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/logs/{log_id}", response_model=ApiResponse)
async def get_log_v1(
    log_id: str,
    user_info: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取单条审计日志（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.AUDIT_LOG_URL}/api/audit/logs/{log_id}",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"审计日志服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"审计日志服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/stats", response_model=ApiResponse)
async def get_stats_v1(
    user_info: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取审计统计（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.AUDIT_LOG_URL}/api/audit/stats",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"审计日志服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"审计日志服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/export", response_model=ApiResponse)
async def export_logs_v1(
    format: str = "csv",
    subsystem: str = "",
    event_type: str = "",
    user: str = "",
    user_info: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """导出审计日志（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AUDIT_LOG_URL}/api/audit/export",
                json={
                    "format": format,
                    "query": {
                        "subsystem": subsystem,
                        "event_type": event_type,
                        "user": user,
                    },
                },
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"审计日志服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"审计日志服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def audit_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理审计日志服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.AUDIT_LOG_URL,
        target_path=path,
    )
