"""
SSO (Single Sign-On) Authentication Service

Supports multiple SSO providers:
- OAuth 2.0 / OpenID Connect (Google, GitHub, Azure AD, etc.)
- SAML 2.0 (Enterprise IdP)
- LDAP / Active Directory
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.core.config import settings
from app.models.user import User
from app.database import get_db


class SSOProvider(str, Enum):
    """SSO provider types"""

    OAUTH2 = "oauth2"
    SAML = "saml"
    LDAP = "ldap"
    CAS = "cas"


class OAuth2Provider(str, Enum):
    """Pre-configured OAuth2 providers"""

    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    AZURE_AD = "azure_ad"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class SSOConfig:
    """SSO configuration for providers"""

    # OAuth2 Providers Configuration
    OAUTH2_PROVIDERS = {
        OAuth2Provider.GOOGLE: {
            "display_name": "Google",
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scope": "openid email profile",
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": f"{settings.APP_URL}/api/v1/auth/sso/callback/google",
        },
        OAuth2Provider.GITHUB: {
            "display_name": "GitHub",
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scope": "read:user user:email",
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "redirect_uri": f"{settings.APP_URL}/api/v1/auth/sso/callback/github",
        },
        OAuth2Provider.MICROSOFT: {
            "display_name": "Microsoft",
            "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me",
            "scope": "openid profile email",
            "client_id": settings.MICROSOFT_OAUTH_CLIENT_ID,
            "client_secret": settings.MICROSOFT_OAUTH_CLIENT_SECRET,
            "redirect_uri": f"{settings.APP_URL}/api/v1/auth/sso/callback/microsoft",
            "tenant_id": settings.MICROSOFT_OAUTH_TENANT_ID,
        },
    }

    # LDAP Configuration
    LDAP_CONFIG = {
        "server": settings.LDAP_SERVER,
        "port": settings.LDAP_PORT or 389,
        "use_ssl": settings.LDAP_USE_SSL or False,
        "bind_dn": settings.LDAP_BIND_DN,
        "bind_password": settings.LDAP_BIND_PASSWORD,
        "search_base": settings.LDAP_SEARCH_BASE,
        "user_search_filter": settings.LDAP_USER_SEARCH_FILTER or "(uid={username})",
        "email_attribute": "mail",
        "first_name_attribute": "givenName",
        "last_name_attribute": "sn",
    }

    # SAML Configuration
    SAML_CONFIG = {
        "sp_entity_id": f"{settings.APP_URL}/metadata",
        "acs_url": f"{settings.APP_URL}/api/v1/auth/sso/acs",
        "slo_url": f"{settings.APP_URL}/api/v1/auth/sso/slo",
        "idp_metadata_url": settings.SAML_IDP_METADATA_URL,
        "idp_sso_url": settings.SAML_IDP_SSO_URL,
        "idp_slo_url": settings.SAML_IDP_SLO_URL,
        "idp_issuer": settings.SAML_IDP_ISSUER,
        "idp_certificate": settings.SAML_IDP_CERTIFICATE,
    }


class OAuth2State:
    """OAuth2 state management for CSRF protection"""

    def __init__(self, state: str, provider: str, redirect_uri: str):
        self.state = state
        self.provider = provider
        self.redirect_uri = redirect_uri
        self.created_at = datetime.utcnow()

    def is_valid(self) -> bool:
        """Check if state is valid (not expired)"""
        return datetime.utcnow() - self.created_at < timedelta(minutes=10)


class SSOUserService:
    """Service for syncing SSO users with local users"""

    def __init__(self):
        pass

    async def get_or_create_user_from_oauth(
        self,
        db: AsyncSession,
        provider: str,
        user_info: Dict[str, Any],
    ) -> User:
        """
        Get or create a user from OAuth2 user info.

        Args:
            db: Database session
            provider: OAuth2 provider name
            user_info: User info from OAuth2 provider

        Returns:
            User object
        """
        # Try to find existing user by OAuth2 identity
        from app.models.user import SSOIdentity

        result = await db.execute(
            select(SSOIdentity).where(
                (SSOIdentity.provider == provider)
                & (SSOIdentity.provider_user_id == user_info.get("id"))
            )
        )
        identity = result.scalar_one_or_none()

        if identity:
            # Existing user, update info
            user = await db.get(User, identity.user_id)
            if user:
                # Update user info if changed
                if user_info.get("email") and user.email != user_info.get("email"):
                    user.email = user_info["email"]
                if user_info.get("name") and user.full_name != user_info.get("name"):
                    user.full_name = user_info["name"]
                db.add(user)
                await db.commit()
                await db.refresh(user)
            return user

        # Create new user
        username = self._generate_username(
            user_info.get("email"),
            user_info.get("name")
        )
        email = user_info.get("email")
        full_name = user_info.get("name")

        # Check if username already exists
        existing = await db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            username = f"{username}_{uuid.uuid4().hex[:8]}"

        # Create user with random password (SSO only)
        import secrets
        random_password = secrets.token_urlsafe(32)

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=random_password,  # Will be hashed by User model
            is_active=True,
            is_verified=True,  # SSO users are pre-verified
        )
        db.add(user)
        await db.flush()

        # Create SSO identity
        identity = SSOIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=str(user_info.get("id")),
            provider_data=user_info,
        )
        db.add(identity)
        await db.commit()
        await db.refresh(user)

        return user

    async def get_or_create_user_from_ldap(
        self,
        db: AsyncSession,
        username: str,
        ldap_user_info: Dict[str, Any],
    ) -> User:
        """
        Get or create a user from LDAP.

        Args:
            db: Database session
            username: LDAP username
            ldap_user_info: User info from LDAP

        Returns:
            User object
        """
        # Try to find existing user
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if user:
            return user

        # Create new user
        email = ldap_user_info.get("mail", [f"{username}@local"])[0]
        full_name = " ".join(filter(None, [
            ldap_user_info.get("givenName"),
            ldap_user_info.get("sn")
        ]))

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    def _generate_username(self, email: Optional[str], name: Optional[str]) -> str:
        """Generate a unique username from email or name"""
        if email:
            username = email.split("@")[0]
            # Sanitize
            username = "".join(c if c.isalnum() or c in "._-" else "_" for c in username)
            return username.lower()
        if name:
            return name.lower().replace(" ", ".")
        return f"user_{uuid.uuid4().hex[:8]}"


class SSOService:
    """
    Main SSO service handling authentication flows.
    """

    def __init__(self):
        self.config = SSOConfig()
        self.user_service = SSOUserService()
        self.states: Dict[str, OAuth2State] = {}

    def generate_state(self, provider: str, redirect_uri: str) -> str:
        """Generate a state for OAuth2 CSRF protection"""
        state = str(uuid.uuid4())
        self.states[state] = OAuth2State(state, provider, redirect_uri)
        return state

    def validate_state(self, state: str, provider: str) -> bool:
        """Validate OAuth2 state"""
        oauth_state = self.states.get(state)
        if not oauth_state or oauth_state.provider != provider:
            return False
        if not oauth_state.is_valid():
            return False
        # Consume state
        del self.states[state]
        return True

    def get_authorization_url(
        self, provider: OAuth2Provider, redirect_uri: Optional[str] = None
    ) -> str:
        """
        Get OAuth2 authorization URL.

        Args:
            provider: OAuth2 provider
            redirect_uri: Override redirect URI

        Returns:
            Authorization URL
        """
        config = self.config.OAUTH2_PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"Provider {provider} not configured")

        state = self.generate_state(provider.value, redirect_uri or config["redirect_uri"])

        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri or config["redirect_uri"],
            "response_type": "code",
            "scope": config["scope"],
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{config['authorization_url']}?{param_string}"

    async def exchange_code_for_token(
        self, provider: OAuth2Provider, code: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            provider: OAuth2 provider
            code: Authorization code from callback
            redirect_uri: Redirect URI used in authorization

        Returns:
            Token response
        """
        import httpx

        config = self.config.OAUTH2_PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"Provider {provider} not configured")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data=data,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(
        self, provider: OAuth2Provider, access_token: str
    ) -> Dict[str, Any]:
        """
        Get user info from OAuth2 provider.

        Args:
            provider: OAuth2 provider
            access_token: Access token

        Returns:
            User info
        """
        import httpx

        config = self.config.OAUTH2_PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"Provider {provider} not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    async def authenticate_oauth2(
        self,
        db: AsyncSession,
        provider: OAuth2Provider,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> tuple[str, User]:
        """
        Complete OAuth2 authentication flow.

        Args:
            db: Database session
            provider: OAuth2 provider
            code: Authorization code
            state: OAuth2 state
            redirect_uri: Redirect URI

        Returns:
            Tuple of (access_token, user)
        """
        # Validate state
        if not self.validate_state(state, provider.value):
            raise ValueError("Invalid or expired state")

        # Exchange code for token
        token_data = await self.exchange_code_for_token(provider, code, redirect_uri)
        access_token = token_data.get("access_token")

        # Get user info
        user_info = await self.get_user_info(provider, access_token)

        # Get or create user
        user = await self.user_service.get_or_create_user_from_oauth(
            db, provider.value, user_info
        )

        return access_token, user

    async def authenticate_ldap(
        self,
        db: AsyncSession,
        username: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate via LDAP.

        Args:
            db: Database session
            username: LDAP username
            password: User password

        Returns:
            User if authentication successful, None otherwise
        """
        try:
            import ldap3

            config = self.config.LDAP_CONFIG
            server = ldap3.Server(
                f"{config['server']}:{config['port']}",
                use_ssl=config['use_ssl'],
            )

            conn = ldap3.Connection(server)
            conn.bind(
                config['bind_dn'],
                config['bind_password']
            )

            # Search for user
            search_filter = config['user_search_filter'].format(username=username)
            conn.search(
                config['search_base'],
                search_filter,
                attributes=[
                    config['email_attribute'],
                    config['first_name_attribute'],
                    config['last_name_attribute'],
                ]
            )

            user_info = {}
            if conn.entries:
                _, entry = conn.entries[0]
                if entry:
                    attributes = entry.attributes
                    dn = entry_dn = entry DN

                    # Verify password by binding as user
                    try:
                        conn.bind(dn, password)
                    except ldap3.INVALID_CREDENTIALS:
                        return None

                    if attributes:
                        user_info["mail"] = attributes.get(config['email_attribute'], [None])[0]
                        user_info["givenName"] = attributes.get(config['first_name_attribute'], [b""])[0].decode()
                        user_info["sn"] = attributes.get(config['last_name_attribute'], [b""])[0].decode()

            # Sync or create user
            user = await self.user_service.get_or_create_user_from_ldap(
                db, username, user_info
            )

            return user

        except Exception as e:
            # Log error but don't expose details
            return None

    def generate_saml_metadata(self) -> str:
        """
        Generate SAML SP metadata.

        Returns:
            SAML metadata XML
        """
        config = self.config.SAML_CONFIG

        metadata = f"""<?xml version="1.0"?>
<EntityDescriptor entityID="{config['sp_entity_id']}" xmlns="urn:oasis:names:tc:SAML:2.0:metadata:SPSSODescriptor">
  <SPSSODescriptor>
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</NameIDFormat>
    <AssertionConsumerService binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                          Location="{config['acs_url']}"
                          index="0"/>
    <SingleLogoutService binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                      Location="{config['slo_url']}"
                      index="0"/>
  </SPSSODescriptor>
</EntityDescriptor>
"""
        return metadata

    def validate_saml_response(self, saml_response: str) -> Optional[Dict[str, Any]]:
        """
        Validate SAML response from IdP.

        Args:
            saml_response: SAML response XML

        Returns:
            Parsed attributes if valid, None otherwise
        """
        # In production, use python3-saml or similar library
        # This is a placeholder
        return None


# Global service instance
sso_service = SSOService()
