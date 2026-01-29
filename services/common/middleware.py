"""请求日志中间件 - 将操作日志发送到审计日志服务"""

import time
import logging
from typing import Optional

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("one-data-studio")

AUDIT_LOG_URL = "http://localhost:8016/api/audit/log"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录所有 API 调用到审计日志"""

    def __init__(self, app, service_name: str, audit_url: Optional[str] = None):
        super().__init__(app)
        self.service_name = service_name
        self.audit_url = audit_url or AUDIT_LOG_URL

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000

        # 忽略健康检查
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return response

        # 异步发送审计日志（不阻塞响应）
        try:
            await self._send_audit_log(request, response, duration_ms)
        except Exception as e:
            logger.warning(f"发送审计日志失败: {e}")

        return response

    async def _send_audit_log(self, request: Request, response: Response, duration_ms: float):
        """发送审计日志到审计服务"""
        # 提取用户信息
        user = "anonymous"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from services.common.auth import verify_token
                payload = verify_token(auth_header[7:])
                user = payload.username
            except Exception as e:
                logger.debug(f"解析认证令牌失败: {e}")

        log_entry = {
            "subsystem": self.service_name,
            "event_type": "api_call",
            "user": user,
            "action": f"{request.method} {request.url.path}",
            "resource": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent", ""),
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(self.audit_url, json=log_entry)
        except Exception:
            # 审计服务不可用时仅记录本地日志
            logger.info(f"[AUDIT] {log_entry['action']} by {user} -> {response.status_code}")
