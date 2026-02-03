"""Superset 代理路由 - BI 分析

使用会话认证（Session Cookie）通过表单登录获取会话。
"""

import asyncio
import re
import time

import httpx
from fastapi import APIRouter, Depends, Request, Response

from services.common.api_response import ApiResponse, ErrorCode, error, success
from services.common.auth import TokenPayload, get_current_user
from services.portal.config import settings
from services.portal.routers.proxy import proxy_request

router = APIRouter(prefix="/api/proxy/superset", tags=["Superset"])


class SupersetSessionManager:
    """Superset 会话管理器

    通过表单登录获取会话 Cookie，并自动保持会话活跃。
    """

    def __init__(self):
        self._cookies: dict | None = None
        self._csrf_token: str | None = None
        self._session_expire: float = 0
        self._lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()

    async def get_session(self) -> tuple[dict, str] | None:
        """获取有效的会话 Cookie 和 CSRF Token

        Returns:
            (Cookie 字典, CSRF Token) 或 None
        """
        # 快速路径：会话有效直接返回
        if self._is_session_valid():
            return self._cookies, self._csrf_token

        # 慢路径：需要创建会话
        async with self._refresh_lock:
            # 双重检查：可能其他协程已经刷新了
            if self._is_session_valid():
                return self._cookies, self._csrf_token

            # 创建新会话
            return await self._create_session()

    def _is_session_valid(self) -> bool:
        """检查会话是否有效（提前 5 分钟刷新）"""
        return (
            self._cookies is not None
            and self._csrf_token is not None
            and time.time() < self._session_expire - 300  # 5 min buffer
        )

    async def _create_session(self) -> tuple[dict, str] | None:
        """创建新的 Superset 会话"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Step 1: 访问登录页面获取初始 CSRF token
                resp = await client.get(f"{settings.SUPERSET_URL}/login/")
                if resp.status_code != 200:
                    return None

                # 提取 CSRF token (从HTML中)
                csrf_token = self._extract_csrf_token(resp.text)

                # Step 2: 提交登录表单
                form_data = {
                    "username": settings.SUPERSET_ADMIN_USER,
                    "password": settings.SUPERSET_ADMIN_PASSWORD,
                    "csrf_token": csrf_token or "",
                }

                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"{settings.SUPERSET_URL}/login/",
                }

                resp = await client.post(
                    f"{settings.SUPERSET_URL}/login/",
                    data=form_data,
                    headers=headers,
                )

                # 登录成功后，从 cookies 中提取 session
                cookies = {}
                for cookie_name, cookie_value in client.cookies.items():
                    cookies[cookie_name] = cookie_value

                if not cookies:
                    return None

                # Step 3: 访问一个需要认证的页面来获取新的 CSRF token
                resp = await client.get(f"{settings.SUPERSET_URL}/profile/?username={settings.SUPERSET_ADMIN_USER}")

                # 尝试从响应中提取新的 CSRF token
                new_csrf = self._extract_csrf_token(resp.text)

                async with self._lock:
                    self._cookies = cookies
                    self._csrf_token = new_csrf or csrf_token
                    # 会话有效期 1 小时
                    self._session_expire = time.time() + 3600

                return self._cookies, self._csrf_token

        except Exception as e:
            import logging
            logging.warning(f"Superset 会话创建失败: {e}")
        return None, None

    def _extract_csrf_token(self, html: str) -> str | None:
        """从 HTML 中提取 CSRF token"""
        patterns = [
            r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"',
            r'<input[^>]*csrf_token[^>]*value="([^"]+)"',
            r'"csrfToken":"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    def invalidate(self):
        """使当前会话失效"""
        self._cookies = None
        self._csrf_token = None
        self._session_expire = 0


# 全局会话管理器实例
_session_manager = SupersetSessionManager()


async def _get_superset_session() -> tuple[dict, str] | None:
    """获取 Superset 会话 Cookie 和 CSRF Token"""
    return await _session_manager.get_session()


async def _superset_request(
    path: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None,
) -> ApiResponse:
    """发起 Superset 请求并返回统一格式响应"""
    session_cookies, csrf_token = await _get_superset_session()

    if not session_cookies:
        return error(
            message="无法获取 Superset 会话",
            code=ErrorCode.SUPERSET_ERROR,
        )

    url = f"{settings.SUPERSET_URL}/{path.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 添加 cookies 到客户端
            for cookie_name, cookie_value in session_cookies.items():
                client.cookies[cookie_name] = cookie_value

            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data or {})
            elif method.upper() == "PUT":
                resp = await client.put(url, headers=headers, json=json_data or {})
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers, params=params)
            elif method.upper() == "PATCH":
                resp = await client.patch(url, headers=headers, json=json_data or {})
            else:
                return error(message="不支持的 HTTP 方法", code=ErrorCode.INVALID_PARAMS)

            if resp.status_code in (200, 201):
                return success(data=resp.json())
            elif resp.status_code == 401:
                # 会话可能失效，强制刷新
                _session_manager.invalidate()
                return error(message="Superset 认证失败，请重试", code=ErrorCode.SUPERSET_ERROR)
            elif resp.status_code == 403:
                # 权限不足
                return error(message="Superset 权限不足", code=ErrorCode.SUPERSET_ERROR)
            elif resp.status_code == 404:
                # 资源不存在，返回空结果而不是错误
                return success(data={"result": [], "count": 0})
            else:
                return error(
                    message=f"Superset 请求失败: {resp.status_code}",
                    code=ErrorCode.SUPERSET_ERROR,
                )
    except Exception as e:
        return error(
            message=f"Superset 服务异常: {str(e)}",
            code=ErrorCode.SUPERSET_ERROR,
        )


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get("/v1/dashboards", response_model=ApiResponse)
async def get_dashboards_v1(
    page: int = 1,
    page_size: int = 20,
    q: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取仪表板列表（v1 API）"""
    return await _superset_request(
        path="api/v1/dashboard/",
        method="GET",
        params={"page": page, "page_size": page_size, "q": q},
    )


@router.get("/v1/dashboards/{dashboard_id}", response_model=ApiResponse)
async def get_dashboard_v1(
    dashboard_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取仪表板详情（v1 API）"""
    return await _superset_request(
        path=f"api/v1/dashboard/{dashboard_id}",
        method="GET",
    )


@router.get("/v1/charts", response_model=ApiResponse)
async def get_charts_v1(
    page: int = 1,
    page_size: int = 20,
    q: str = "",
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取图表列表（v1 API）"""
    return await _superset_request(
        path="api/v1/chart/",
        method="GET",
        params={"page": page, "page_size": page_size, "q": q},
    )


@router.get("/v1/charts/{chart_id}", response_model=ApiResponse)
async def get_chart_v1(
    chart_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取图表详情（v1 API）"""
    return await _superset_request(
        path=f"api/v1/chart/{chart_id}",
        method="GET",
    )


@router.get("/v1/datasets", response_model=ApiResponse)
async def get_datasets_v1(
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据集列表（v1 API）"""
    return await _superset_request(
        path="api/v1/dataset/",
        method="GET",
        params={"page": page, "page_size": page_size},
    )


@router.get("/v1/datasets/{dataset_id}", response_model=ApiResponse)
async def get_dataset_v1(
    dataset_id: int,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据集详情（v1 API）"""
    return await _superset_request(
        path=f"api/v1/dataset/{dataset_id}",
        method="GET",
    )


@router.get("/v1/databases", response_model=ApiResponse)
async def get_databases_v1(
    page: int = 1,
    page_size: int = 20,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取数据库列表（v1 API）"""
    return await _superset_request(
        path="api/v1/database/",
        method="GET",
        params={"page": page, "page_size": page_size},
    )


@router.get("/v1/me", response_model=ApiResponse)
async def get_me_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取当前用户信息（v1 API）"""
    return await _superset_request(
        path="api/v1/me/",
        method="GET",
    )


# ============================================================
# 旧版 API（向后兼容，直接代理）
# ============================================================

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def superset_proxy(
    path: str,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Response:
    """代理 Superset API 请求（旧版 API，向后兼容）

    自动添加 Superset 会话 Cookie。
    """
    session_cookies, _ = await _get_superset_session()

    extra_headers = {}
    cookies_to_set = {}

    if session_cookies:
        # 将 cookies 转换为 Cookie header
        cookie_header = "; ".join([f"{k}={v}" for k, v in session_cookies.items()])
        extra_headers["Cookie"] = cookie_header

    return await proxy_request(
        request=request,
        target_base_url=settings.SUPERSET_URL,
        target_path=path,
        extra_headers=extra_headers if extra_headers else None,
    )
