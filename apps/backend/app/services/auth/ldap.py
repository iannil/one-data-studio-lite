"""
LDAP Authentication Service

Provides LDAP/Active Directory authentication and user synchronization.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
    from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPSocketOpenError
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    LDAPException = Exception
    LDAPBindError = Exception
    LDAPSocketOpenError = Exception
    # Type stub for when ldap3 is not available
    Connection = Any  # type: ignore

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.sso import SSOConfig
from app.models.tenant import Tenant, TenantUser
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


@dataclass
class LDAPUser:
    """LDAP user information"""
    username: str
    email: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    dn: Optional[str] = None
    groups: List[str] = None

    def __post_init__(self):
        if self.groups is None:
            self.groups = []


@dataclass
class LDAPTestResult:
    """Result of LDAP connection test"""
    success: bool
    message: str
    can_bind: bool = False
    can_search: bool = False
    user_count: int = 0


class LDAPAuthenticationError(Exception):
    """LDAP authentication failed"""
    pass


class LDAPConnectionError(Exception):
    """Failed to connect to LDAP server"""
    pass


class LDAPService:
    """
    LDAP Authentication Service

    Handles LDAP/Active Directory authentication and user provisioning.
    """

    def __init__(self, config: SSOConfig):
        if not LDAP_AVAILABLE:
            raise ImportError("ldap3 package is required for LDAP support")

        self.config = config

        # Build server URL
        protocol = "ldaps" if config.ldap_use_ssl else "ldap"
        self.server_url = f"{protocol}://{config.ldap_server}:{config.ldap_port}"

    def test_connection(self) -> LDAPTestResult:
        """Test LDAP connection and configuration"""
        try:
            # Test server connection
            server = Server(self.server_url, use_ssl=self.config.ldap_use_ssl, get_info=ALL)

            # Test bind
            if self.config.ldap_bind_dn and self.config.ldap_bind_password:
                try:
                    conn = Connection(
                        server,
                        user=self.config.ldap_bind_dn,
                        password=self.config.ldap_bind_password,
                        auto_bind=True,
                    )
                    can_bind = True
                except (LDAPBindError, LDAPException) as e:
                    return LDAPTestResult(
                        success=False,
                        message=f"Bind failed: {str(e)}",
                        can_bind=False,
                    )
            else:
                # Anonymous bind for testing
                try:
                    conn = Connection(server, auto_bind=True)
                    can_bind = True
                except Exception:
                    can_bind = False
                    conn = Connection(server)

            # Test search
            user_count = 0
            can_search = False

            if self.config.ldap_base_dn and self.config.ldap_search_filter:
                try:
                    conn.search(
                        search_base=self.config.ldap_base_dn,
                        search_filter=self.config.ldap_search_filter.replace("{username}", "*"),
                        search_scope=SUBTREE,
                        attributes=["cn", "uid", "mail", "dn"],
                        size_limit=1,
                    )
                    user_count = len(conn.entries)
                    can_search = True
                except Exception as e:
                    logger.warning(f"LDAP search test failed: {e}")

            conn.unbind()

            return LDAPTestResult(
                success=True,
                message="LDAP connection successful",
                can_bind=can_bind,
                can_search=can_search,
                user_count=user_count,
            )

        except LDAPSocketOpenError as e:
            return LDAPTestResult(
                success=False,
                message=f"Could not connect to LDAP server: {str(e)}",
            )
        except Exception as e:
            return LDAPTestResult(
                success=False,
                message=f"LDAP test failed: {str(e)}",
            )

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[LDAPUser]]:
        """
        Authenticate user against LDAP.

        Returns:
            Tuple of (success, ldap_user)
        """
        try:
            server = Server(self.server_url, use_ssl=self.config.ldap_use_ssl, get_info=ALL)

            # First, bind with service account if configured
            if self.config.ldap_bind_dn and self.config.ldap_bind_password:
                try:
                    conn = Connection(
                        server,
                        user=self.config.ldap_bind_dn,
                        password=self.config.ldap_bind_password,
                        auto_bind=True,
                    )
                except (LDAPBindError, LDAPException) as e:
                    logger.error(f"LDAP bind failed: {e}")
                    raise LDAPConnectionError(f"Failed to bind to LDAP server: {str(e)}")
            else:
                conn = Connection(server)
                if not conn.bind():
                    raise LDAPConnectionError("Anonymous bind failed")

            # Search for user
            user_dn = None
            search_filter = self.config.ldap_search_filter.replace("{username}", username)

            conn.search(
                search_base=self.config.ldap_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn", "uid", "mail", "givenName", "sn", "telephoneNumber", "department", "title", "memberOf", "dn"],
            )

            if not conn.entries:
                conn.unbind()
                return False, None

            user_entry = conn.entries[0]
            user_dn = user_entry.dn.value if hasattr(user_entry.dn, 'value') else str(user_entry.dn)

            # Try to authenticate as the user
            try:
                user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
                user_conn.unbind()
            except (LDAPBindError, LDAPException):
                conn.unbind()
                return False, None

            # Extract user attributes
            ldap_user = self._parse_ldap_user(user_entry, username, user_dn)

            # Get user groups if configured
            if self.config.sync_groups:
                ldap_user.groups = self._get_user_groups(conn, user_dn)

            conn.unbind()

            return True, ldap_user

        except LDAPSocketOpenError as e:
            logger.error(f"LDAP connection error: {e}")
            raise LDAPConnectionError(f"Could not connect to LDAP server: {str(e)}")
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            raise LDAPAuthenticationError(f"LDAP authentication failed: {str(e)}")

    def _parse_ldap_user(self, user_entry: Any, username: str, user_dn: str) -> LDAPUser:
        """Parse LDAP entry into LDAPUser"""
        def get_attr(attr_name: str) -> Optional[str]:
            if hasattr(user_entry, attr_name):
                value = getattr(user_entry, attr_name)
                if value:
                    if isinstance(value, list) and len(value) > 0:
                        return str(value[0])
                    return str(value)
            return None

        mappings = self.config.attribute_mappings or {}

        # Extract attributes with fallbacks
        email = get_attr(mappings.get("email", "mail")) or f"{username}@local"
        full_name = get_attr(mappings.get("full_name", "cn")) or username
        first_name = get_attr(mappings.get("first_name", "givenName"))
        last_name = get_attr(mappings.get("last_name", "sn"))
        phone = get_attr(mappings.get("phone", "telephoneNumber"))
        department = get_attr(mappings.get("department", "department"))
        title = get_attr(mappings.get("title", "title"))

        return LDAPUser(
            username=username,
            email=email,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            department=department,
            title=title,
            dn=user_dn,
        )

    def _get_user_groups(self, conn: Connection, user_dn: str) -> List[str]:
        """Get user's group memberships"""
        groups = []

        try:
            # Check if memberOf is available
            conn.search(
                search_base=self.config.ldap_base_dn,
                search_filter=f"(&(objectClass=group)(member={user_dn}))",
                search_scope=SUBTREE,
                attributes=["cn", "dn"],
            )

            for entry in conn.entries:
                if hasattr(entry, "cn"):
                    groups.append(str(entry.cn))
                elif hasattr(entry, "dn"):
                    groups.append(str(entry.dn))

        except Exception as e:
            logger.warning(f"Failed to fetch user groups: {e}")

        return groups

    def search_users(self, search_filter: Optional[str] = None, limit: int = 100) -> List[LDAPUser]:
        """Search for users in LDAP"""
        try:
            server = Server(self.server_url, use_ssl=self.config.ldap_use_ssl, get_info=ALL)

            # Bind
            if self.config.ldap_bind_dn and self.config.ldap_bind_password:
                conn = Connection(
                    server,
                    user=self.config.ldap_bind_dn,
                    password=self.config.ldap_bind_password,
                    auto_bind=True,
                )
            else:
                conn = Connection(server)
                if not conn.bind():
                    raise LDAPConnectionError("Failed to bind")

            # Build filter
            if search_filter:
                filter_str = f"(&(|(uid=*{search_filter}*)(cn=*{search_filter}*)(mail=*{search_filter}*)){self.config.ldap_search_filter.replace('{username}', '*')})"
            else:
                filter_str = self.config.ldap_search_filter.replace("{username}", "*")

            conn.search(
                search_base=self.config.ldap_base_dn,
                search_filter=filter_str,
                search_scope=SUBTREE,
                attributes=["cn", "uid", "mail", "givenName", "sn", "telephoneNumber", "department", "title", "dn"],
                size_limit=limit,
            )

            users = []
            for entry in conn.entries:
                username = get_attr(entry, "uid") or get_attr(entry, "cn") or ""
                user_dn = str(entry.dn)
                users.append(self._parse_ldap_user(entry, username, user_dn))

            conn.unbind()
            return users

        except Exception as e:
            logger.error(f"LDAP search failed: {e}")
            raise LDAPConnectionError(f"Failed to search LDAP: {str(e)}")

    def sync_user_to_db(
        self,
        ldap_user: LDAPUser,
        db: Session,
        tenant_id: Optional[int] = None,
    ) -> User:
        """Create or update user from LDAP data"""
        # Find existing user
        user = db.query(User).filter(User.email == ldap_user.email).first()

        if not user:
            # Create new user
            user = User(
                email=ldap_user.email,
                username=ldap_user.username,
                full_name=ldap_user.full_name,
                first_name=ldap_user.first_name,
                last_name=ldap_user.last_name,
                phone=ldap_user.phone,
                department=ldap_user.department,
                title=ldap_user.title,
                is_active=True,
                auth_provider="ldap",
                sso_provider_id=str(self.config.id),
                external_id=ldap_user.username,
            )
            db.add(user)
            db.flush()
            logger.info(f"Created new user from LDAP: {ldap_user.email}")
        else:
            # Update existing user
            if self.config.auto_update_users:
                user.username = ldap_user.username
                user.full_name = ldap_user.full_name
                user.first_name = ldap_user.first_name
                user.last_name = ldap_user.last_name
                user.phone = ldap_user.phone
                user.department = ldap_user.department
                user.title = ldap_user.title
                user.updated_at = datetime.utcnow()
                logger.info(f"Updated user from LDAP: {ldap_user.email}")

        # Add to tenant if specified
        if tenant_id:
            from app.services.tenant import TenantService

            tenant_service = TenantService(db)
            tenant_users = db.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user.id,
            ).first()

            if not tenant_users:
                # Determine role from mappings
                role = self._map_user_to_role(ldap_user)

                tenant_service.add_user(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=role,
                )

        db.commit()
        db.refresh(user)

        return user

    def _map_user_to_role(self, ldap_user: LDAPUser) -> str:
        """Map LDAP user groups to internal role"""
        if not self.config.role_mappings:
            return self.config.default_role or "member"

        role_mappings = self.config.role_mappings

        # Check group memberships
        for role, group_patterns in role_mappings.items():
            for pattern in group_patterns:
                if pattern == "*":
                    return role

                for group in ldap_user.groups or []:
                    if group == pattern or group.endswith(pattern):
                        return role

        return self.config.default_role or "member"


def get_ldap_service(config: SSOConfig) -> Optional[LDAPService]:
    """Get LDAP service instance"""
    if config.provider != "ldap":
        return None
    try:
        return LDAPService(config)
    except ImportError:
        logger.error("ldap3 package not installed")
        return None


def get_attr(entry: Any, attr_name: str) -> Optional[str]:
    """Helper to get LDAP attribute value"""
    if hasattr(entry, attr_name):
        value = getattr(entry, attr_name)
        if value:
            if isinstance(value, list) and len(value) > 0:
                return str(value[0])
            return str(value)
    return None
