"""Sensitive Detect 代理路由 - 敏感数据检测"""

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

router = APIRouter(prefix="/api/proxy/sensitive", tags=["Sensitive Detect"])


# ============================================================
# 请求模型
# ============================================================

class ScanRequest(BaseModel):
    table_name: str
    database: Optional[str] = None
    sample_size: Optional[int] = 100


class ClassifyRequest(BaseModel):
    data_samples: list
    context: Optional[str] = None


class DetectionRuleBase(BaseModel):
    name: str
    pattern: str
    description: Optional[str] = None
    sensitive_type: str


class ScanAndApplyRequest(BaseModel):
    table_name: str
    database: Optional[str] = None
    sample_size: Optional[int] = 100
    auto_apply: bool = False


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.post("/v1/scan", response_model=ApiResponse)
async def scan_v1(
    request: ScanRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """扫描敏感数据（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/scan",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/classify", response_model=ApiResponse)
async def classify_v1(
    request: ClassifyRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """LLM 分类（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/classify",
                json=request.model_dump(),
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/rules", response_model=ApiResponse)
async def get_rules_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取检测规则列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/rules",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/rules/{rule_id}", response_model=ApiResponse)
async def get_rule_v1(
    rule_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取单个检测规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/rules/{rule_id}",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/rules", response_model=ApiResponse)
async def add_rule_v1(
    rule: DetectionRuleBase,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """添加检测规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/rules",
                json=rule.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.delete("/v1/rules/{rule_id}", response_model=ApiResponse)
async def delete_rule_v1(
    rule_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """删除检测规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/rules/{rule_id}",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/reports", response_model=ApiResponse)
async def get_reports_v1(
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取扫描报告列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/reports",
                params={"page": page, "page_size": page_size},
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/reports/{report_id}", response_model=ApiResponse)
async def get_report_v1(
    report_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取单个扫描报告（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/reports/{report_id}",
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/scan-and-apply", response_model=ApiResponse)
async def scan_and_apply_v1(
    request: ScanAndApplyRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """扫描敏感数据并自动应用脱敏规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.SENSITIVE_DETECT_URL}/api/sensitive/scan-and-apply",
                json=request.model_dump(),
            headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"敏感检测服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"敏感检测服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def sensitive_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理敏感检测服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.SENSITIVE_DETECT_URL,
        target_path=path,
    )
