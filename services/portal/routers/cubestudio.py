"""Cube-Studio 代理路由 - AI 平台

Cube-Studio 是腾讯音乐开源的 AI 平台，提供：
- Pipeline 管理：ETL 工作流编排
- 模型推理：LLM 模型服务
- 数据管理：数据集管理、版本控制
- Notebook：交互式开发
- 监控告警：Prometheus + Grafana
"""


import httpx
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

router = APIRouter(prefix="/api/proxy/cubestudio", tags=["Cube-Studio"])


# ============================================================
# 请求模型
# ============================================================

class PipelineRunRequest(BaseModel):
    run_configuration: str | None = "local"
    parameters: dict | None = None
    variables: dict | None = None


class ModelInferenceRequest(BaseModel):
    model_name: str
    prompt: str
    max_tokens: int | None = 2048
    temperature: float | None = 0.1
    top_p: float | None = 0.9
    stream: bool | None = False


class NotebookCreateRequest(BaseModel):
    name: str
    description: str | None = None
    kernel_type: str | None = "python3"
    parent_folder: str | None = "/"


class DataSourceRequest(BaseModel):
    name: str
    type: str  # mysql, postgres, hive, kafka, etc.
    connection_params: dict
    description: str | None = None


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

# ------------------------------------------------------------
# Pipeline API
# ------------------------------------------------------------

@router.get("/v1/pipelines", response_model=ApiResponse)
async def get_pipelines_v1(
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Pipeline 列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.CUBE_STUDIO_URL}/pipeline_modelview/api/",
                params={"page": page, "page_size": page_size},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Cube-Studio 服务错误: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Cube-Studio 服务异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.get("/v1/pipelines/{pipeline_id}", response_model=ApiResponse)
async def get_pipeline_v1(
    pipeline_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Pipeline 详情（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.CUBE_STUDIO_URL}/pipeline_modelview/api/{pipeline_id}",
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Cube-Studio 服务错误: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Cube-Studio 服务异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.post("/v1/pipelines/{pipeline_id}/run", response_model=ApiResponse)
async def run_pipeline_v1(
    pipeline_id: int,
    request: PipelineRunRequest = PipelineRunRequest(),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """运行 Pipeline（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.CUBE_STUDIO_URL}/pipeline_modelview/api/{pipeline_id}/run",
                json=request.model_dump(exclude_none=True),
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return error(
                message=f"Cube-Studio 服务错误: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Cube-Studio 服务异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.delete("/v1/pipelines/{pipeline_id}", response_model=ApiResponse)
async def delete_pipeline_v1(
    pipeline_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """删除 Pipeline（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{settings.CUBE_STUDIO_URL}/pipeline_modelview/api/{pipeline_id}",
            )
            if resp.status_code in (200, 204):
                return success(data={"message": "删除成功"})
            return error(
                message=f"Cube-Studio 服务错误: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Cube-Studio 服务异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


# ------------------------------------------------------------
# 模型推理 API (通过 Ollama)
# ------------------------------------------------------------

@router.get("/v1/models", response_model=ApiResponse)
async def list_models_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取可用模型列表（v1 API）

    通过 Cube-Studio 部署的 Ollama 服务获取模型列表。
    """
    try:
        # Cube-Studio 部署的 Ollama 服务端口
        ollama_url = settings.CUBE_STUDIO_URL.replace(":30080", ":31434")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                # 解析模型列表
                models = data.get("models", [])
                model_names = list(set(m.get("name", "").split(":")[0] for m in models))
                return success(data={"models": model_names, "details": models})
            return error(
                message=f"Ollama 服务错误: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"Ollama 服务异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.post("/v1/models/inference", response_model=ApiResponse)
async def model_inference_v1(
    request: ModelInferenceRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """模型推理（v1 API）

    通过 Cube-Studio 部署的 Ollama 服务进行模型推理。
    """
    try:
        ollama_url = settings.CUBE_STUDIO_URL.replace(":30080", ":31434")
        payload = {
            "model": request.model_name,
            "prompt": request.prompt,
            "stream": request.stream,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            if request.stream:
                # 流式响应处理
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json=payload,
                )
                if resp.status_code == 200:
                    return success(data=resp.json())
            else:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json=payload,
                )
                if resp.status_code == 200:
                    return success(data=resp.json())

            return error(
                message=f"模型推理失败: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"模型推理异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.post("/v1/models/chat", response_model=ApiResponse)
async def chat_completion_v1(
    request: ModelInferenceRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """对话补全（v1 API）

    类似 OpenAI ChatCompletion API 格式。
    """
    try:
        ollama_url = settings.CUBE_STUDIO_URL.replace(":30080", ":31434")
        payload = {
            "model": request.model_name,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": request.stream,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/chat",
                json=payload,
            )
            if resp.status_code == 200:
                return success(data=resp.json())

            return error(
                message=f"对话补全失败: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"对话补全异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


# ------------------------------------------------------------
# 数据管理 API
# ------------------------------------------------------------

@router.get("/v1/data-sources", response_model=ApiResponse)
async def list_data_sources_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据源列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.CUBE_STUDIO_URL}/data_integration/api/data-sources/",
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            # 如果端点不存在，返回空列表
            return success(data={"data_sources": []})
    except Exception as e:
        return success(data={"data_sources": [], "note": f"数据管理功能可能未启用: {str(e)}"})


@router.post("/v1/data-sources", response_model=ApiResponse)
async def create_data_source_v1(
    request: DataSourceRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建数据源（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.CUBE_STUDIO_URL}/data_integration/api/data-sources/",
                json=request.model_dump(),
            )
            if resp.status_code in (200, 201):
                return success(data=resp.json())
            return error(
                message=f"创建数据源失败: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"创建数据源异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


@router.get("/v1/datasets", response_model=ApiResponse)
async def list_datasets_v1(
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据集列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.CUBE_STUDIO_URL}/data_management/api/datasets/",
                params={"page": page, "page_size": page_size},
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return success(data={"datasets": []})
    except Exception as e:
        return success(data={"datasets": [], "note": f"数据管理功能可能未启用: {str(e)}"})


# ------------------------------------------------------------
# Notebook API
# ------------------------------------------------------------

@router.get("/v1/notebooks", response_model=ApiResponse)
async def list_notebooks_v1(
    path: str = "/",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Notebook 列表（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.CUBE_STUDIO_URL}/jupyter/api/contents/{path}",
            )
            if resp.status_code == 200:
                return success(data=resp.json())
            return success(data={"items": []})
    except Exception as e:
        return success(data={"items": [], "note": f"Notebook 功能可能未启用: {str(e)}"})


@router.post("/v1/notebooks", response_model=ApiResponse)
async def create_notebook_v1(
    request: NotebookCreateRequest,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建 Notebook（v1 API）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.CUBE_STUDIO_URL}/jupyter/api/contents/{request.parent_folder}",
                json={
                    "name": f"{request.name}.ipynb",
                    "type": "notebook",
                    "format": "json",
                },
            )
            if resp.status_code in (200, 201):
                return success(data=resp.json())
            return error(
                message=f"创建 Notebook 失败: {resp.status_code}",
                code=ErrorCode.CUBE_STUDIO_ERROR,
            )
    except Exception as e:
        return error(
            message=f"创建 Notebook 异常: {str(e)}",
            code=ErrorCode.CUBE_STUDIO_ERROR,
        )


# ------------------------------------------------------------
# 监控告警 API
# ------------------------------------------------------------

@router.get("/v1/metrics", response_model=ApiResponse)
async def get_metrics_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取监控指标（v1 API）

    通过 Prometheus 获取系统指标。
    """
    try:
        prometheus_url = settings.CUBE_STUDIO_URL.replace(":30080", ":30090")
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 获取节点指标
            resp = await client.get(f"{prometheus_url}/api/v1/query", params={"query": "up"})
            if resp.status_code == 200:
                return success(data=resp.json())
            return success(data={"metrics": [], "note": "Prometheus 可能未启用"})
    except Exception as e:
        return success(data={"metrics": [], "note": f"监控功能可能未启用: {str(e)}"})


@router.get("/v1/alerts", response_model=ApiResponse)
async def list_alerts_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取告警列表（v1 API）

    通过 AlertManager 获取告警信息。
    """
    try:
        alertmanager_url = settings.CUBE_STUDIO_URL.replace(":30080", ":30093")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{alertmanager_url}/api/v1/alerts")
            if resp.status_code == 200:
                return success(data=resp.json())
            return success(data={"alerts": [], "note": "AlertManager 可能未启用"})
    except Exception as e:
        return success(data={"alerts": [], "note": f"告警功能可能未启用: {str(e)}"})


@router.get("/v1/services/status", response_model=ApiResponse)
async def get_services_status_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取 Cube-Studio 各服务状态（v1 API）"""
    services_status = {
        "cube_studio": {"url": settings.CUBE_STUDIO_URL, "status": "unknown"},
        "ollama": {"url": settings.CUBE_STUDIO_URL.replace(":30080", ":31434"), "status": "unknown"},
        "prometheus": {"url": settings.CUBE_STUDIO_URL.replace(":30080", ":30090"), "status": "unknown"},
        "grafana": {"url": settings.CUBE_STUDIO_URL.replace(":30080", ":33000"), "status": "unknown"},
    }

    # 检查各服务状态
    for name, info in services_status.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                health_path = "/health" if name != "ollama" else "/api/tags"
                resp = await client.get(f"{info['url']}{health_path}")
                info["status"] = "online" if resp.status_code == 200 else "offline"
        except Exception:
            info["status"] = "offline"

    return success(data={"services": services_status})


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def cubestudio_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 Cube-Studio API 请求（旧版 API，向后兼容）"""
    return await proxy_request(
        request=request,
        target_base_url=settings.CUBE_STUDIO_URL,
        target_path=path,
    )
