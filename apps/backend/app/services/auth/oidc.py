"""
OIDC (OpenID Connect) Authentication Service

Provides OpenID Connect/OAuth2 authentication for SSO.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlencode
import secrets
import json
import hashlib

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.sso import SSOConfig, SSOSession
from app.core.security import create_access_token
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OIDCConfig:
    """OIDC configuration"""
    client_id: str
    client_secret: str
    discovery_url: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    redirect_uri: str = ""
    scope: str = "openid email profile"


@dataclass
class OIDCUserInfo:
    """OIDC user information"""
    sub: str  # Subject (unique identifier)
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    groups: Optional[list] = None

    @property
    def full_name(self) -> str:
        if self.name:
            return self.name
        parts = []
        if self.given_name:
            parts.append(self.given_name)
        if self.family_name:
            parts.append(self.family_name)
        return " ".join(parts) if parts else self.email.split("@")[0]


@dataclass
class OIDCTokenResponse:
    """Response from OIDC token endpoint"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


class OIDCService:
    """
    OpenID Connect Authentication Service

    Handles OIDC/OAuth2 authentication flows.
    """

    def __init__(self, config: SSOConfig):
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx package is required for OIDC support")

        self.config = config
        self.oidc_config = OIDCConfig(
            client_id=config.oidc_client_id or "",
            client_secret=config.oidc_client_secret or "",
            discovery_url=config.oidc_discovery_url,
            authorization_endpoint=config.oidc_authorization_endpoint,
            token_endpoint=config.oidc_token_endpoint,
            userinfo_endpoint=config.oidc_userinfo_endpoint,
            jwks_uri=config.oidc_jwks_uri,
            redirect_uri=config.oidc_redirect_uri or "",
            scope=config.oidc_scope or "openid email profile",
        )

        self._discovered_config: Optional[Dict[str, Any]] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for OIDC requests"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def discover(self) -> Dict[str, Any]:
        """Discover OIDC configuration from provider"""
        if self._discovered_config:
            return self._discovered_config

        if not self.oidc_config.discovery_url:
            # Use manually configured endpoints
            self._discovered_config = {
                "authorization_endpoint": self.oidc_config.authorization_endpoint,
                "token_endpoint": self.oidc_config.token_endpoint,
                "userinfo_endpoint": self.oidc_config.userinfo_endpoint,
                "jwks_uri": self.oidc_config.jwks_uri,
            }
            return self._discovered_config

        try:
            client = await self._get_client()
            response = await client.get(self.oidc_config.discovery_url)
            response.raise_for_status()

            self._discovered_config = response.json()
            return self._discovered_config

        except Exception as e:
            logger.error(f"OIDC discovery failed: {e}")
            raise

    def get_authorization_url(
        self,
        state: str,
        nonce: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[str] = None,
    ) -> str:
        """Generate authorization URL for OIDC login"""
        # Use discovery or manual config
        auth_endpoint = self.oidc_config.authorization_endpoint
        if not auth_endpoint and self.oidc_config.discovery_url:
            # Will need to call discover first in async context
            pass

        params = {
            "client_id": self.oidc_config.client_id,
            "response_type": "code",
            "scope": scopes or self.oidc_config.scope,
            "redirect_uri": redirect_uri or self.oidc_config.redirect_uri,
            "state": state,
        }

        if nonce:
            params["nonce"] = nonce

        return f"{auth_endpoint}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> OIDCTokenResponse:
        """Exchange authorization code for tokens"""
        token_endpoint = self.oidc_config.token_endpoint
        if not token_endpoint:
            config = await self.discover()
            token_endpoint = config.get("token_endpoint")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or self.oidc_config.redirect_uri,
            "client_id": self.oidc_config.client_id,
            "client_secret": self.oidc_config.client_secret,
        }

        client = await self._get_client()

        # Some providers use Basic auth
        headers = {}
        # Use Basic auth if client secret is set
        if self.oidc_config.client_secret:
            # Both in body and headers for compatibility
            pass

        response = await client.post(
            token_endpoint,
            data=data,
            headers=headers,
        )
        response.raise_for_status()

        token_data = response.json()

        return OIDCTokenResponse(
            access_token=token_data.get("access_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token"),
            id_token=token_data.get("id_token"),
            scope=token_data.get("scope"),
        )

    async def get_user_info(
        self,
        access_token: str,
    ) -> OIDCUserInfo:
        """Get user info from OIDC provider"""
        userinfo_endpoint = self.oidc_config.userinfo_endpoint
        if not userinfo_endpoint:
            config = await self.discover()
            userinfo_endpoint = config.get("userinfo_endpoint")

        client = await self._get_client()

        response = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()

        user_data = response.json()

        return OIDCUserInfo(
            sub=user_data.get("sub", ""),
            email=user_data.get("email", ""),
            email_verified=user_data.get("email_verified", False),
            name=user_data.get("name"),
            given_name=user_data.get("given_name"),
            family_name=user_data.get("family_name"),
            picture=user_data.get("picture"),
            groups=user_data.get("groups"),
        )

    async def authenticate(
        self,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
        db: Optional[Session] = None,
        tenant_id: Optional[int] = None,
    ) -> tuple[User, str]:
        """
        Complete OIDC authentication flow.

        Returns:
            Tuple of (user, access_token)
        """
        # Exchange code for tokens
        token_response = await self.exchange_code_for_token(code, redirect_uri)

        # Get user info
        user_info = await self.get_user_info(token_response.access_token)

        # Sync to database
        user = await self.sync_user_to_db(user_info, db, tenant_id)

        # Create session
        if db:
            await self._create_sso_session(
                db=db,
                user_id=user.id,
                tenant_id=tenant_id,
                subject_id=user_info.sub,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                id_token=token_response.id_token,
                expires_in=token_response.expires_in,
            )

        # Create JWT access token
        jwt_token = create_access_token(data={"sub": str(user.id)})

        return user, jwt_token

    async def sync_user_to_db(
        self,
        user_info: OIDCUserInfo,
        db: Optional[Session] = None,
        tenant_id: Optional[int] = None,
    ) -> User:
        """Create or update user from OIDC data"""
        if not db:
            raise ValueError("Database session required")

        # Find existing user by email or external ID
        user = db.query(User).filter(
            (User.email == user_info.email) | (User.external_id == user_info.sub)
        ).first()

        if not user:
            # Create new user
            user = User(
                email=user_info.email,
                username=user_info.email.split("@")[0],
                full_name=user_info.full_name,
                first_name=user_info.given_name,
                last_name=user_info.family_name,
                avatar_url=user_info.picture,
                is_active=True,
                email_verified=user_info.email_verified,
                auth_provider="oidc",
                sso_provider_id=str(self.config.id),
                external_id=user_info.sub,
            )
            db.add(user)
            db.flush()
            logger.info(f"Created new user from OIDC: {user_info.email}")
        else:
            # Update existing user
            if self.config.auto_update_users:
                user.full_name = user_info.full_name
                user.first_name = user_info.given_name
                user.last_name = user_info.family_name
                user.avatar_url = user_info.picture
                user.email_verified = user_info.email_verified
                user.updated_at = datetime.utcnow()
                logger.info(f"Updated user from OIDC: {user_info.email}")

        # Add to tenant if specified
        if tenant_id:
            from app.services.tenant import TenantService

            tenant_service = TenantService(db)
            tenant_users = db.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user.id,
            ).first()

            if not tenant_users:
                role = self._map_user_to_role(user_info)
                tenant_service.add_user(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=role,
                )

        db.commit()
        db.refresh(user)

        return user

    async def _create_sso_session(
        self,
        db: Session,
        user_id: int,
        tenant_id: Optional[int],
        subject_id: str,
        access_token: str,
        refresh_token: Optional[str],
        id_token: Optional[str],
        expires_in: Optional[int],
    ) -> SSOSession:
        """Create SSO session for logout tracking"""
        # Hash tokens for storage (don't store raw tokens)
        access_hash = hashlib.sha256(access_token.encode()).hexdigest()
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest() if refresh_token else None
        id_hash = hashlib.sha256(id_token.encode()).hexdigest() if id_token else None

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        session = SSOSession(
            user_id=user_id,
            tenant_id=tenant_id,
            sso_config_id=self.config.id,
            subject_id=subject_id,
            access_token_hash=access_hash,
            refresh_token_hash=refresh_hash,
            id_token_hash=id_hash,
            expires_at=expires_at,
        )

        db.add(session)
        db.commit()

        return session

    def _map_user_to_role(self, user_info: OIDCUserInfo) -> str:
        """Map OIDC user groups to internal role"""
        if not self.config.role_mappings:
            return self.config.default_role or "member"

        role_mappings = self.config.role_mappings

        # Check group memberships
        for role, group_patterns in role_mappings.items():
            for pattern in group_patterns:
                if pattern == "*":
                    return role

                for group in user_info.groups or []:
                    if group == pattern or group.endswith(pattern):
                        return role

        return self.config.default_role or "member"

    async def refresh_token(self, refresh_token: str) -> Optional[OIDCTokenResponse]:
        """Refresh access token"""
        token_endpoint = self.oidc_config.token_endpoint
        if not token_endpoint:
            return None

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.oidc_config.client_id,
            "client_secret": self.oidc_config.client_secret,
        }

        client = await self._get_client()

        response = await client.post(token_endpoint, data=data)
        response.raise_for_status()

        token_data = response.json()

        return OIDCTokenResponse(
            access_token=token_data.get("access_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token", refresh_token),
            id_token=token_data.get("id_token"),
        )

    async def logout(self, user_id: int, db: Session) -> bool:
        """Perform SLO (Single Logout) for OIDC"""
        # Mark sessions as logged out
        sessions = db.query(SSOSession).filter(
            SSOSession.user_id == user_id,
            SSOSession.sso_config_id == self.config.id,
            SSOSession.logged_out == False,
        ).all()

        for session in sessions:
            session.logged_out = True
            session.logged_out_at = datetime.utcnow()

        db.commit()
        return len(sessions) > 0

    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def generate_oidc_state() -> str:
    """Generate secure state parameter for OIDC flow"""
    return secrets.token_urlsafe(32)


def generate_oidc_nonce() -> str:
    """Generate secure nonce parameter for OIDC flow"""
    return secrets.token_urlsafe(32)


def get_oidc_service(config: SSOConfig) -> Optional[OIDCService]:
    """Get OIDC service instance"""
    if config.provider != "oidc" and config.provider != "oauth2":
        return None
    try:
        return OIDCService(config)
    except ImportError:
        logger.error("httpx package not installed")
        return None
