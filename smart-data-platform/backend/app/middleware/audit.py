from __future__ import annotations

import json
import time
import uuid
from typing import Callable, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import AsyncSessionLocal
from app.models import AuditLog, AuditAction


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of API operations.

    Logs all write operations (POST, PUT, PATCH, DELETE) with:
    - Operation type
    - Target resource (from URL path)
    - User information (from JWT token)
    - Request body (for POST/PUT/PATCH)
    - Response status
    - Timestamp
    """

    # Routes to skip auditing (health checks, docs, etc.)
    SKIP_PATHS = {
        "/health",
        "/",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    }

    # Methods that are considered write operations
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Map HTTP methods to audit actions
    METHOD_TO_ACTION = {
        "POST": AuditAction.CREATE,
        "PUT": AuditAction.UPDATE,
        "PATCH": AuditAction.UPDATE,
        "DELETE": AuditAction.DELETE,
        "GET": AuditAction.READ,
    }

    # Routes with special action mappings
    SPECIAL_ROUTES = {
        "/auth/login": AuditAction.LOGIN,
        "/auth/logout": AuditAction.LOGOUT,
        "/run": AuditAction.EXECUTE,
        "/export": AuditAction.EXPORT,
        "/execute": AuditAction.EXECUTE,
    }

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and log audit information."""
        path = request.url.path

        if self._should_skip(path, request.method):
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start_time = time.time()

        request_body = None
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    request_body = json.loads(body_bytes.decode())
                    request_body = self._sanitize_body(request_body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_body = None

            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request = Request(request.scope, receive)

        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        if request.method in self.WRITE_METHODS:
            await self._log_operation(
                request=request,
                response=response,
                request_id=request_id,
                request_body=request_body,
                duration_ms=duration_ms,
            )

        return response

    def _should_skip(self, path: str, method: str) -> bool:
        """Check if the request should skip audit logging."""
        if path in self.SKIP_PATHS:
            return True

        for skip_path in self.SKIP_PATHS:
            if path.startswith(skip_path):
                return True

        if method == "OPTIONS":
            return True

        return False

    def _sanitize_body(self, body: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive fields from request body."""
        sensitive_fields = {"password", "secret", "token", "api_key", "apikey", "secret_key"}
        sanitized = {}

        for key, value in body.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_body(value)
            else:
                sanitized[key] = value

        return sanitized

    def _extract_resource_info(self, path: str) -> tuple[str, str | None]:
        """Extract resource type and ID from URL path."""
        parts = [p for p in path.split("/") if p]

        if len(parts) < 2:
            return "unknown", None

        api_index = -1
        for i, part in enumerate(parts):
            if part in {"v1", "v2", "api"}:
                api_index = i

        if api_index >= 0 and api_index + 1 < len(parts):
            resource_type = parts[api_index + 1]
            resource_id = parts[api_index + 2] if len(parts) > api_index + 2 else None
            return resource_type, resource_id

        return parts[-1] if parts else "unknown", None

    def _determine_action(self, method: str, path: str) -> AuditAction:
        """Determine the audit action based on method and path."""
        for route_part, action in self.SPECIAL_ROUTES.items():
            if route_part in path:
                return action

        return self.METHOD_TO_ACTION.get(method, AuditAction.READ)

    def _extract_user_info(self, request: Request) -> tuple[str | None, str | None]:
        """Extract user ID and email from request state or token."""
        if hasattr(request.state, "user"):
            user = request.state.user
            return str(user.id), user.email

        return None, None

    async def _log_operation(
        self,
        request: Request,
        response: Response,
        request_id: str,
        request_body: dict[str, Any] | None,
        duration_ms: int,
    ) -> None:
        """Log the operation to the audit log table."""
        try:
            resource_type, resource_id = self._extract_resource_info(request.url.path)
            action = self._determine_action(request.method, request.url.path)
            user_id, user_email = self._extract_user_info(request)

            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    user_id=user_id,
                    user_email=user_email,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    new_value=request_body,
                    description=f"{request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)",
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                    request_id=request_id,
                )
                db.add(audit_log)
                await db.commit()

        except Exception:
            pass
