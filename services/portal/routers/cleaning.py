"""AI Cleaning 代理路由 - AI 清洗推荐"""

import os

import httpx
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

# 服务间通信密钥
SERVICE_SECRET = os.environ.get("SERVICE_SECRET", "internal-service-secret-dev-do-not-use-in-prod")

router = APIRouter(prefix="/api/proxy/cleaning", tags=["AI Cleaning"])


# ============================================================
# 请求模型
# ============================================================

class AnalyzeRequest(BaseModel):
    table_name: str
    database: str | None = None
    sample_size: int | None = 100


class RecommendRequest(BaseModel):
    table_name: str
    database: str | None = None


class GenerateConfigRequest(BaseModel):
    table_name: str
    rules: list[str]
    output_format: str | None = "seatunnel"


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.post("/v1/analyze", response_model=ApiResponse)
async def analyze_quality_v1(
    request: AnalyzeRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """分析数据质量（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AI_CLEANING_URL}/api/cleaning/analyze",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"AI 清洗服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"AI 清洗服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/recommend", response_model=ApiResponse)
async def recommend_rules_v1(
    request: RecommendRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """AI 推荐清洗规则（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AI_CLEANING_URL}/api/cleaning/recommend",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"AI 清洗服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"AI 清洗服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/v1/rules", response_model=ApiResponse)
async def get_cleaning_rules_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取清洗规则模板（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.AI_CLEANING_URL}/api/cleaning/rules",
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"AI 清洗服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"AI 清洗服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/v1/generate-config", response_model=ApiResponse)
async def generate_config_v1(
    request: GenerateConfigRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """生成 SeaTunnel Transform 配置（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_CLEANING_URL}/api/cleaning/generate-config",
                json=request.model_dump(),
                headers={"X-Service-Secret": SERVICE_SECRET},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"AI 清洗服务错误: {resp.status_code}",
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
    except Exception as e:
        return error(
            message=f"AI 清洗服务异常: {str(e)}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def cleaning_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 AI 清洗服务请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.AI_CLEANING_URL,
        target_path=path,
    )
