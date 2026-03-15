"""
Label Studio Authentication Integration

Integrates the platform's JWT authentication with Label Studio.
Provides seamless SSO between the main platform and Label Studio.
"""

import hashlib
import hmac
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import get_current_user, get_db
from app.models.user import User


class LabelStudioAuthConfig:
    """Label Studio authentication configuration"""

    # Shared secret for JWT signing between platform and Label Studio
    SHARED_SECRET_KEY = settings.LABEL_STUDIO_SHARED_SECRET

    # Label Studio JWT token lifetime
    TOKEN_LIFETIME = timedelta(hours=24)

    # Label Studio base URL
    LABEL_STUDIO_URL = settings.LABEL_STUDIO_URL


class LabelStudioTokenGenerator:
    """Generates Label Studio compatible JWT tokens"""

    def __init__(self, config: LabelStudioAuthConfig = None):
        self.config = config or LabelStudioAuthConfig()

    def generate_token(
        self,
        user: User,
        organization_id: int = 1
    ) -> Dict[str, Any]:
        """
        Generate a Label Studio JWT token for the user.

        Args:
            user: Platform user
            organization_id: Label Studio organization ID

        Returns:
            Dict with token and user info
        """
        now = datetime.utcnow()

        # Label Studio JWT payload structure
        payload = {
            # User identity
            "sub": str(user.id),
            "username": user.username,
            "email": user.email or f"{user.username}@one-data-studio.local",
            "name": user.full_name or user.username,

            # Organization context
            "org": str(organization_id),
            "org_role": self._map_user_role(user),

            # Token validity
            "iat": now,
            "exp": now + self.config.TOKEN_LIFETIME,

            # Additional claims
            "preferred_username": user.username,
            "given_name": user.full_name or user.username.split()[0] if user.full_name else user.username,
            "family_name": user.full_name.split()[-1] if user.full_name and " " in user.full_name else "",
        }

        # Sign with shared secret
        token = jwt.encode(
            payload,
            self.config.SHARED_SECRET_KEY,
            algorithm="HS256"
        )

        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.full_name or user.username,
                "role": self._map_user_role(user),
            },
            "label_studio_url": self.config.LABEL_STUDIO_URL,
        }

    def _map_user_role(self, user: User) -> str:
        """Map platform role to Label Studio role"""
        if user.is_superuser:
            return "administrator"
        elif hasattr(user, 'role') and user.role:
            role_map = {
                "admin": "administrator",
                "manager": "manager",
                "annotator": "annotator",
                "reviewer": "reviewer",
            }
            return role_map.get(user.role.lower(), "annotator")
        return "annotator"

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a Label Studio token.

        Args:
            token: JWT token to validate

        Returns:
            Decoded payload if valid

        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.config.SHARED_SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


class LabelStudioAuthMiddleware:
    """
    Middleware for Label Studio authentication proxy.

    This middleware intercepts requests to Label Studio and injects
    authentication headers.
    """

    def __init__(self):
        self.token_generator = LabelStudioTokenGenerator()

    async def process_request(
        self,
        request: Request,
        current_user: User
    ) -> Dict[str, str]:
        """
        Process incoming request and generate auth headers for Label Studio.

        Args:
            request: Incoming request
            current_user: Authenticated platform user

        Returns:
            Headers to forward to Label Studio
        """
        # Generate LS token
        token_data = self.token_generator.generate_token(current_user)

        # Return headers for proxying
        return {
            "Authorization": f"Bearer {token_data['token']}",
            "X-Label-Studio-User": current_user.username,
            "X-Label-Studio-Email": current_user.email or "",
        }

    async def create_webhook_signature(
        self,
        payload: Dict[str, Any]
    ) -> str:
        """
        Create signature for Label Studio webhook verification.

        Args:
            payload: Webhook payload

        Returns:
            HMAC signature
        """
        import json
        payload_str = json.dumps(payload, sort_keys=True)

        return hmac.new(
            self.token_generator.config.SHARED_SECRET_KEY.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

    async def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Verify Label Studio webhook signature.

        Args:
            payload: Webhook payload
            signature: Signature from webhook header

        Returns:
            True if signature is valid
        """
        expected = await self.create_webhook_signature(payload)
        return hmac.compare_digest(expected, signature)


class LabelStudioUserSync:
    """
    Synchronizes platform users with Label Studio.
    """

    def __init__(self):
        self.token_generator = LabelStudioTokenGenerator()

    async def get_user_projects(
        self,
        user: User
    ) -> list[Dict[str, Any]]:
        """
        Get projects accessible to user from Label Studio.

        Args:
            user: Platform user

        Returns:
            List of projects
        """
        # This would query Label Studio API
        # For now, return empty list
        return []

    async def sync_user_to_label_studio(
        self,
        user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Sync user to Label Studio via API.

        Args:
            user: Platform user
            db: Database session

        Returns:
            Sync result
        """
        # Generate auth token
        token_data = self.token_generator.generate_token(user)

        # In a real implementation, this would:
        # 1. Call Label Studio API to create/update user
        # 2. Assign user to appropriate organizations
        # 3. Set up user permissions

        return {
            "status": "synced",
            "user_id": user.id,
            "username": user.username,
            "ls_token": token_data["token"],
        }


# Dependency for getting Label Studio auth
async def get_label_studio_auth(
    current_user: User = Depends(get_current_user)
) -> LabelStudioTokenGenerator:
    """
    FastAPI dependency for Label Studio authentication.

    Args:
        current_user: Currently authenticated user

    Returns:
        Token generator instance
    """
    return LabelStudioTokenGenerator()


async def get_label_studio_token(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    FastAPI dependency for getting Label Studio token.

    Args:
        current_user: Currently authenticated user

    Returns:
        Token data dict
    """
    generator = LabelStudioTokenGenerator()
    return generator.generate_token(current_user)
