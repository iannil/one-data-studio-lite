"""通用代理函数 - 转发前端请求到后端子系统"""

import os

import httpx
from fastapi import HTTPException, Request, Response

# 服务间通信密钥
SERVICE_SECRET = os.environ.get("SERVICE_SECRET", "internal-service-secret-dev-do-not-use-in-prod")

# 不应该被转发的 hop-by-hop 响应头
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


async def proxy_request(
    request: Request,
    target_base_url: str,
    target_path: str,
    extra_headers: dict | None = None,
    timeout: float = 30.0,
) -> Response:
    """
    通用 HTTP 代理转发。

    - 透传 Authorization 头
    - 转发 query params、body
    - 超时返回 504，连接失败返回 503
    - extra_headers 用于注入子系统 service token
    """
    url = f"{target_base_url.rstrip('/')}/{target_path.lstrip('/')}"

    # 构建请求头：透传原始 Authorization，合并额外头，注入服务间认证
    headers = {"X-Service-Secret": SERVICE_SECRET}
    if request.headers.get("authorization"):
        headers["Authorization"] = request.headers["authorization"]
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    if extra_headers:
        headers.update(extra_headers)

    body = await request.body()
    params = dict(request.query_params)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=params,
                content=body if body else None,
            )
            # 过滤掉 hop-by-hop 头，避免冲突
            response_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in HOP_BY_HOP_HEADERS
            }
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=response_headers,
                media_type=resp.headers.get("content-type"),
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="上游服务请求超时")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接上游服务")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"代理请求失败: {str(e)}")
