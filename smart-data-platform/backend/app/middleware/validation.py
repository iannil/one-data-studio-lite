# Input validation middleware for security

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# Patterns for detecting common attack vectors
SQL_INJECTION_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
    r"(\bor\b|\band\b).*?=\s*?\d\s*?(?:or|and)",
    r"exec(\s|\+)+(s|x)p\w+",
    r"union.*select",
    r"select.*from",
    r"insert\s+into",
    r"delete\s+from",
    r"drop\s+table",
    r"update.*set",
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"<embed",
    r"<object",
    r"eval\s*\(",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\" ,
    r"%2e%2e",
    r"~",
]


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating request input.

    Provides:
    - Max request body size enforcement
    - SQL injection detection
    - XSS detection
    - Path traversal detection
    """

    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB default
        enable_sql_check: bool = True,
        enable_xss_check: bool = True,
        enable_path_check: bool = True,
    ):
        """
        Initialize the validation middleware.

        Args:
            app: The ASGI application
            max_body_size: Maximum request body size in bytes
            enable_sql_check: Enable SQL injection detection
            enable_xss_check: Enable XSS detection
            enable_path_check: Enable path traversal detection
        """
        super().__init__(app)
        self.max_body_size = max_body_size
        self.enable_sql_check = enable_sql_check
        self.enable_xss_check = enable_xss_check
        self.enable_path_check = enable_path_check

        # Compile regex patterns
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]

    async def dispatch(
        self,
        request: Request,
        call_next: Any,
    ) -> Response:
        """Validate request before processing."""

        # Skip validation for file uploads (multipart/form-data)
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            return await call_next(request)

        # Skip validation for OCR endpoints (they handle file uploads)
        if request.url.path.startswith("/api/v1/ocr"):
            return await call_next(request)

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            logger.warning(
                "Request blocked: Request body too large",
                extra={"path": request.url.path, "content_length": content_length}
            )
            return Response(
                content='{"error":"Request body too large"}',
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                media_type="application/json",
            )

        # For POST/PUT/PATCH requests, validate body content
        if request.method in ("POST", "PUT", "PATCH"):
            body = await self._get_body(request)

            if body:
                # Validate for SQL injection
                if self.enable_sql_check:
                    if self._check_sql_injection(body):
                        logger.warning(
                            "Request blocked: SQL injection detected",
                            extra={"path": request.url.path, "method": request.method}
                        )
                        return Response(
                            content='{"error":"Invalid input detected"}',
                            status_code=status.HTTP_400_BAD_REQUEST,
                            media_type="application/json",
                        )

                # Validate for XSS
                if self.enable_xss_check:
                    if self._check_xss(body):
                        logger.warning(
                            "Request blocked: XSS detected",
                            extra={"path": request.url.path, "method": request.method}
                        )
                        return Response(
                            content='{"error":"Invalid input detected"}',
                            status_code=status.HTTP_400_BAD_REQUEST,
                            media_type="application/json",
                        )

        # Check query parameters
        query_string = str(request.url.query)
        if query_string:
            if self.enable_path_check:
                if self._check_path_traversal(query_string):
                    logger.warning(
                        "Request blocked: Path traversal detected in query",
                        extra={"path": request.url.path, "query": query_string[:100]}
                    )
                    return Response(
                        content='{"error":"Invalid input detected"}',
                        status_code=status.HTTP_400_BAD_REQUEST,
                        media_type="application/json",
                    )

        # Check path parameters
        path = request.url.path
        if self.enable_path_check:
            if self._check_path_traversal(path):
                logger.warning(
                    "Request blocked: Path traversal detected in URL path",
                    extra={"path": path[:200]}
                )
                return Response(
                    content='{"error":"Invalid path detected"}',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="application/json",
                )

        return await call_next(request)

    async def _get_body(self, request: Request) -> str:
        """Get request body as string."""
        try:
            body = await request.body()
            return body.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _check_sql_injection(self, text: str) -> bool:
        """Check text for SQL injection patterns."""
        for pattern in self.sql_patterns:
            if pattern.search(text):
                return True
        return False

    def _check_xss(self, text: str) -> bool:
        """Check text for XSS patterns."""
        for pattern in self.xss_patterns:
            if pattern.search(text):
                return True
        return False

    def _check_path_traversal(self, text: str) -> bool:
        """Check text for path traversal patterns."""
        for pattern in self.path_patterns:
            if pattern.search(text):
                return True
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Any,
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
