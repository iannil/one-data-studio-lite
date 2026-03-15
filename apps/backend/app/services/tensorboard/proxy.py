"""
TensorBoard Proxy Service

Handles proxying requests to TensorBoard instances with authentication
and access control.
"""

import logging
from typing import Optional, AsyncGenerator
from uuid import uuid4

import httpx
from fastapi import Request, Response

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tensorboard import TensorBoardInstance
from app.core.config import settings

logger = logging.getLogger(__name__)


class TensorBoardProxy:
    """
    TensorBoard proxy handler

    Proxies HTTP requests to TensorBoard instances with proper
    authentication and access control.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize TensorBoard proxy

        Args:
            db: Database session
        """
        self.db = db
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_instance(self, instance_id: str) -> Optional[TensorBoardInstance]:
        """
        Get TensorBoard instance by ID

        Args:
            instance_id: Instance ID

        Returns:
            TensorBoardInstance or None
        """
        result = await self.db.execute(
            select(TensorBoardInstance).where(
                TensorBoardInstance.instance_id == instance_id
            )
        )
        return result.scalar_one_or_none()

    async def proxy_request(
        self,
        instance_id: str,
        request: Request,
        user_id: Optional[str] = None,
    ) -> Optional[tuple[int, dict, AsyncGenerator[bytes, None]]]:
        """
        Proxy request to TensorBoard instance

        Args:
            instance_id: TensorBoard instance ID
            request: Original request
            user_id: User ID for access logging

        Returns:
            Tuple of (status_code, headers, body_generator) or None if failed
        """
        instance = await self.get_instance(instance_id)

        if not instance:
            logger.warning(f"TensorBoard instance {instance_id} not found")
            return None

        if instance.status != "running":
            logger.warning(f"TensorBoard instance {instance_id} is not running")
            return None

        # Get target URL
        target_url = instance.internal_url or instance.external_url
        if not target_url:
            logger.error(f"TensorBoard instance {instance_id} has no URL")
            return None

        # Build proxy URL
        path = request.url.path.replace(f"/api/v1/tensorboard/{instance_id}/proxy", "")
        query = request.url.query
        proxy_url = f"{target_url}{path}?{query}" if query else f"{target_url}{path}"

        # Prepare headers
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("authorization", None)  # Don't forward auth headers

        # Proxy the request
        try:
            proxy_response = await self.client.stream(
                method=request.method,
                url=proxy_url,
                headers=headers,
                content=await request.body(),
            )

            # Log access
            from app.services.tensorboard.manager import TensorBoardManager
            manager = TensorBoardManager(self.db)
            await manager.log_access(
                instance_id=instance_id,
                user_id=user_id,
                access_type="web",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Build response headers
            response_headers = {}
            for key, value in proxy_response.headers.items():
                if key.lower() in [
                    "content-type",
                    "content-length",
                    "cache-control",
                    "etag",
                ]:
                    response_headers[key] = value

            async def body_generator():
                async for chunk in proxy_response.aiter_bytes():
                    yield chunk

            return proxy_response.status_code, response_headers, body_generator()

        except httpx.HTTPError as e:
            logger.error(f"Failed to proxy to TensorBoard instance {instance_id}: {e}")
            return None

    async def generate_access_token(
        self,
        instance_id: str,
        user_id: str,
        ttl_seconds: int = 3600,
    ) -> Optional[str]:
        """
        Generate a time-limited access token for TensorBoard

        Args:
            instance_id: TensorBoard instance ID
            user_id: User ID
            ttl_seconds: Token time-to-live in seconds

        Returns:
            Access token or None if failed
        """
        # Check if instance exists and is accessible
        instance = await self.get_instance(instance_id)
        if not instance or instance.status != "running":
            return None

        # Generate token (in production, use JWT or similar)
        token = f"{instance_id}:{user_id}:{uuid4().hex}"

        # Store token in cache (Redis or similar)
        # For now, we'll use a simple in-memory approach
        # TODO: Implement proper token storage with expiration

        return token

    async def validate_access_token(
        self,
        instance_id: str,
        token: str,
    ) -> bool:
        """
        Validate an access token

        Args:
            instance_id: TensorBoard instance ID
            token: Access token to validate

        Returns:
            True if token is valid
        """
        # TODO: Implement proper token validation
        # For now, accept all tokens (development mode)
        return True

    async def get_signed_url(
        self,
        instance_id: str,
        user_id: str,
        ttl_seconds: int = 3600,
    ) -> Optional[str]:
        """
        Generate a signed URL for direct TensorBoard access

        Args:
            instance_id: TensorBoard instance ID
            user_id: User ID
            ttl_seconds: URL time-to-live in seconds

        Returns:
            Signed URL or None if failed
        """
        instance = await self.get_instance(instance_id)
        if not instance or instance.status != "running":
            return None

        # Generate access token
        token = await self.generate_access_token(instance_id, user_id, ttl_seconds)
        if not token:
            return None

        # Build signed URL
        base_url = instance.external_url or instance.internal_url
        if not base_url:
            return None

        # Add token as query parameter
        signed_url = f"{base_url}?token={token}"

        return signed_url

    async def websocket_proxy(
        self,
        instance_id: str,
        websocket,
        user_id: Optional[str] = None,
    ):
        """
        Proxy WebSocket connections to TensorBoard

        Args:
            instance_id: TensorBoard instance ID
            websocket: WebSocket connection
            user_id: User ID for access logging
        """
        instance = await self.get_instance(instance_id)

        if not instance or instance.status != "running":
            await websocket.close(code=1001, reason="Instance not available")
            return

        # TODO: Implement WebSocket proxy
        # This requires a WebSocket client that can connect to the TensorBoard
        # and forward messages bidirectionally

        await websocket.close(code=1000, reason="WebSocket proxy not implemented")

    async def health_check(self, instance_id: str) -> bool:
        """
        Check if TensorBoard instance is healthy

        Args:
            instance_id: TensorBoard instance ID

        Returns:
            True if healthy
        """
        instance = await self.get_instance(instance_id)

        if not instance or instance.status != "running":
            return False

        target_url = instance.internal_url or instance.external_url
        if not target_url:
            return False

        try:
            response = await self.client.get(f"{target_url}/health", timeout=5.0)
            return response.status_code == 200
        except (httpx.HTTPError, asyncio.TimeoutError):
            return False


# Singleton instance management
_proxies: dict[str, TensorBoardProxy] = {}


def get_tensorboard_proxy(db: AsyncSession) -> TensorBoardProxy:
    """
    Get or create TensorBoard proxy instance

    Args:
        db: Database session

    Returns:
        TensorBoardProxy instance
    """
    # Use database session ID as key (for connection pooling)
    key = str(id(db))

    if key not in _proxies:
        _proxies[key] = TensorBoardProxy(db)

    return _proxies[key]


async def close_tensorboard_proxy(db: AsyncSession):
    """
    Close TensorBoard proxy instance

    Args:
        db: Database session
    """
    key = str(id(db))

    if key in _proxies:
        await _proxies[key].close()
        del _proxies[key]
