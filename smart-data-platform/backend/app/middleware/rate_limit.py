# Rate limiting middleware for API protection

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from functools import wraps
from ipaddress import ip_address
from typing import Any, Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.observability import track_operation


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window: int,
        retry_after: int,
    ):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
            },
        )


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests: int  # Number of requests allowed
    window: int  # Time window in seconds


@dataclass
class RateLimitState:
    """Track rate limit state for a client."""

    count: int = 0
    window_start: float = field(default_factory=time.time)
    blocked_until: float | None = None


class RateLimiter:
    """Token-bucket style rate limiter."""

    def __init__(
        self,
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """
        Initialize the rate limiter.

        Args:
            default_limit: Default number of requests per window
            default_window: Default time window in seconds
        """
        self.default_limit = default_limit
        self.default_window = default_window
        self._states: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._endpoint_configs: dict[str, RateLimitConfig] = {}
        self._user_configs: dict[str, RateLimitConfig] = {}

    def configure_endpoint(
        self,
        endpoint: str,
        limit: int,
        window: int,
    ) -> None:
        """Configure rate limit for a specific endpoint."""
        self._endpoint_configs[endpoint] = RateLimitConfig(
            requests=limit,
            window=window,
        )

    def configure_user(
        self,
        user_id: str,
        limit: int,
        window: int,
    ) -> None:
        """Configure rate limit for a specific user."""
        self._user_configs[user_id] = RateLimitConfig(
            requests=limit,
            window=window,
        )

    def get_config(
        self,
        endpoint: str,
        user_id: str | None = None,
    ) -> RateLimitConfig:
        """Get rate limit config for endpoint/user."""
        if user_id and user_id in self._user_configs:
            return self._user_configs[user_id]
        if endpoint in self._endpoint_configs:
            return self._endpoint_configs[endpoint]
        return RateLimitConfig(
            requests=self.default_limit,
            window=self.default_window,
        )

    def check_rate_limit(
        self,
        key: str,
        endpoint: str,
        user_id: str | None = None,
    ) -> tuple[bool, int, int]:
        """
        Check if a request is within rate limits.

        Returns:
            Tuple of (is_allowed, retry_after, remaining_requests)
        """
        config = self.get_config(endpoint, user_id)
        state = self._states[key]
        now = time.time()

        # Reset if window has passed
        if now - state.window_start >= config.window:
            state.count = 0
            state.window_start = now

        # Check if currently blocked
        if state.blocked_until and now < state.blocked_until:
            retry_after = int(state.blocked_until - now)
            return False, retry_after, 0

        # Check limit
        if state.count >= config.requests:
            # Block until window resets
            state.blocked_until = state.window_start + config.window
            retry_after = int(state.blocked_until - now)
            return False, retry_after, 0

        # Allow request
        state.count += 1
        remaining = config.requests - state.count
        return True, 0, remaining

    def reset(self, key: str) -> None:
        """Reset rate limit state for a key."""
        if key in self._states:
            del self._states[key]

    def get_state(self, key: str) -> RateLimitState:
        """Get current state for a key."""
        return self._states[key]

    def cleanup_old_states(self, max_age: int = 3600) -> int:
        """Clean up states older than max_age seconds."""
        now = time.time()
        to_remove = [
            key
            for key, state in self._states.items()
            if now - state.window_start > max_age
        ]
        for key in to_remove:
            del self._states[key]
        return len(to_remove)


# Global rate limiter instance
_global_limiter = RateLimiter()


def get_rate_limit_config() -> dict[str, Any]:
    """Get current rate limit configuration."""
    return {
        "default": {
            "limit": _global_limiter.default_limit,
            "window": _global_limiter.default_window,
        },
        "endpoints": _global_limiter._endpoint_configs,
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for rate limiting requests."""

    def __init__(
        self,
        app: ASGIApp,
        limiter: RateLimiter | None = None,
        trust_headers: bool = False,
    ):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            limiter: Custom rate limiter instance (uses global if None)
            trust_headers: Whether to trust X-Forwarded-For headers
        """
        super().__init__(app)
        self.limiter = limiter or _global_limiter
        self.trust_headers = trust_headers

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request through rate limiting."""
        # Get client identifier
        client_id = self._get_client_id(request)

        # Get user ID if available
        user_id = self._get_user_id(request)

        # Check rate limit
        endpoint = request.url.path
        is_allowed, retry_after, remaining = self.limiter.check_rate_limit(
            key=client_id,
            endpoint=endpoint,
            user_id=user_id,
        )

        if not is_allowed:
            await track_operation(
                "rate_limit_blocked",
                client_id=client_id,
                endpoint=endpoint,
            )

            response = Response(
                content='{"error":"Rate limit exceeded","retry_after":' + str(retry_after) + '}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )
            response.headers["X-RateLimit-Limit"] = str(self.limiter.get_config(endpoint, user_id).requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))
            response.headers["Retry-After"] = str(retry_after)
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        config = self.limiter.get_config(endpoint, user_id)
        state = self.limiter.get_state(client_id)
        reset_time = int(state.window_start + config.window)

        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Check for authenticated user first
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # Use IP address
        ip = self._get_client_ip(request)
        return f"ip:{ip}"

    def _get_user_id(self, request: Request) -> str | None:
        """Get user ID from request state if available."""
        if hasattr(request.state, "user") and request.state.user:
            return str(request.state.user.id)
        return None

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies."""
        if self.trust_headers:
            # Check forwarded headers
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Get the first IP in the chain
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"


def rate_limit(
    limit: int,
    window: int,
    key_func: Callable[[Request], str] | None = None,
):
    """
    Decorator for rate limiting specific endpoints.

    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        key_func: Optional function to extract rate limit key from request

    Usage:
        @app.get("/api/expensive")
        @rate_limit(limit=10, window=60)
        async def expensive_endpoint():
            return {"data": "expensive"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to extract request from args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request and "request" in kwargs:
                request = kwargs["request"]

            if request:
                client_id = key_func(request) if key_func else _get_default_key(request)
                endpoint = request.url.path

                is_allowed, retry_after, _ = _global_limiter.check_rate_limit(
                    key=client_id,
                    endpoint=endpoint,
                )

                if not is_allowed:
                    raise RateLimitExceeded(
                        limit=limit,
                        window=window,
                        retry_after=retry_after,
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _get_default_key(request: Request) -> str:
    """Get default rate limit key from request."""
    # Check for authenticated user
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Use IP address
    if request.client:
        return f"ip:{request.client.host}"

    return "unknown"


# Configure default rate limits for common endpoints
def setup_default_rate_limits():
    """Set up default rate limits for API endpoints."""
    # Auth endpoints - more restrictive
    _global_limiter.configure_endpoint("/api/v1/auth/login", limit=5, window=60)
    _global_limiter.configure_endpoint("/api/v1/auth/register", limit=3, window=300)

    # Expensive AI endpoints
    _global_limiter.configure_endpoint("/api/v1/analysis/nl-query", limit=20, window=60)
    _global_limiter.configure_endpoint("/api/v1/analysis/predict", limit=10, window=60)

    # ETL endpoints
    _global_limiter.configure_endpoint("/api/v1/etl/pipelines", limit=50, window=60)

    # Data export
    _global_limiter.configure_endpoint("/api/v1/assets", limit=30, window=60)
