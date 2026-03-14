"""
SSO (Single Sign-On) Configuration Models

Models for SSO provider configurations and mappings.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base


class SSOProvider(str, Enum):
    """SSO provider types"""
    LDAP = "ldap"
    SAML = "saml"
    OIDC = "oidc"  # OpenID Connect
    OAUTH2 = "oauth2"


class SSOMapping(str, Enum):
    """Attribute mapping types"""
    EMAIL = "email"
    USERNAME = "username"
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    PHONE = "phone"
    DEPARTMENT = "department"
    TITLE = "title"
    GROUPS = "groups"
    ROLES = "roles"


class SSOConfig(Base):
    """
    SSO Configuration Model

    Stores configuration for various SSO providers.
    """
    __tablename__ = "sso_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    # Provider info
    provider = Column(SQLEnum(SSOProvider), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Company LDAP", "Okta"
    is_enabled = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # LDAP Configuration
    ldap_server = Column(String(255), nullable=True)
    ldap_port = Column(Integer, nullable=True, default=389)
    ldap_use_ssl = Column(Boolean, default=True)
    ldap_use_tls = Column(Boolean, default=False)
    ldap_bind_dn = Column(String(500), nullable=True)
    ldap_bind_password = Column(String(255), nullable=True)  # Encrypted
    ldap_base_dn = Column(String(500), nullable=True)
    ldap_search_filter = Column(String(500), nullable=True)  # e.g., "(uid={username})"
    ldap_user_dn_pattern = Column(String(500), nullable=True)  # e.g., "uid={username},ou=users,dc=example,dc=com"

    # OIDC/OAuth2 Configuration
    oidc_discovery_url = Column(String(500), nullable=True)
    oidc_client_id = Column(String(255), nullable=True)
    oidc_client_secret = Column(String(255), nullable=True)  # Encrypted
    oidc_scope = Column(String(500), nullable=True)  # "openid email profile"
    oidc_redirect_uri = Column(String(500), nullable=True)
    oidc_authorization_endpoint = Column(String(500), nullable=True)
    oidc_token_endpoint = Column(String(500), nullable=True)
    oidc_userinfo_endpoint = Column(String(500), nullable=True)
    oidc_jwks_uri = Column(String(500), nullable=True)

    # SAML Configuration
    saml_idp_entity_id = Column(String(500), nullable=True)
    saml_idp_sso_url = Column(String(500), nullable=True)
    saml_idp_certificate = Column(Text, nullable=True)
    saml_sp_entity_id = Column(String(500), nullable=True)
    saml_sp_acs_url = Column(String(500), nullable=True)  # Assertion Consumer Service
    saml_sp_slo_url = Column(String(500), nullable=True)  # Single Logout Service
    saml_name_id_format = Column(String(100), nullable=True)
    saml_sp_certificate = Column(Text, nullable=True)
    saml_sp_private_key = Column(Text, nullable=True)

    # Attribute mappings
    attribute_mappings = Column(JSON, nullable=True, default={})
    # Example: {"email": "mail", "full_name": "cn", "groups": "memberOf"}

    # Role mappings
    role_mappings = Column(JSON, nullable=True, default={})
    # Example: {"admin": ["cn=admins,ou=groups,dc=example,dc=com"], "user": ["*"]}

    # Group mappings
    group_mappings = Column(JSON, nullable=True, default={})
    # Map external groups to internal roles

    # Options
    auto_create_users = Column(Boolean, default=True)
    auto_update_users = Column(Boolean, default=True)
    default_role = Column(String(50), nullable=True, default="member")
    allowed_domains = Column(JSON, nullable=True, default=[])  # Restrict to specific email domains
    deny_domains = Column(JSON, nullable=True, default=[])

    # Advanced
    sync_groups = Column(Boolean, default=False)
    group_sync_interval_minutes = Column(Integer, nullable=True, default=60)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)

    # Test connection result
    last_test_result = Column(String(20), nullable=True)  # "success", "failure"
    last_test_message = Column(Text, nullable=True)
    last_test_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<SSOConfig(id={self.id}, provider={self.provider.value}, name='{self.name}', enabled={self.is_enabled})>"


class SSOSession(Base):
    """
    SSO Session Model

    Tracks SSO login sessions for single logout.
    """
    __tablename__ = "sso_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    sso_config_id = Column(Integer, ForeignKey("sso_configs.id", ondelete="CASCADE"), nullable=False)

    # SSO session info
    session_index = Column(String(255), nullable=True)  # SAML session index
    name_id = Column(String(255), nullable=True)  # SAML name ID
    subject_id = Column(String(255), nullable=True)  # OIDC subject

    # Token info
    access_token_hash = Column(String(255), nullable=True)
    refresh_token_hash = Column(String(255), nullable=True)
    id_token_hash = Column(String(255), nullable=True)

    # Expiry
    expires_at = Column(DateTime, nullable=True)

    # Logout
    logged_out = Column(Boolean, default=False)
    logged_out_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sso_config = relationship("SSOConfig")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<SSOSession(id={self.id}, user_id={self.user_id}, sso_config_id={self.sso_config_id})>"


class UserGroupMapping(Base):
    """
    User Group Mapping Model

    Maps external groups (from LDAP/SAML) to internal roles.
    """
    __tablename__ = "user_group_mappings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    sso_config_id = Column(Integer, ForeignKey("sso_configs.id", ondelete="CASCADE"), nullable=True)

    # External group info
    external_group_name = Column(String(255), nullable=False)
    external_group_dn = Column(String(500), nullable=True)

    # Internal role
    internal_role = Column(String(50), nullable=False)  # owner, admin, member, viewer

    # Auto-assign to tenant
    auto_assign = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserGroupMapping(external='{self.external_group_name}', internal='{self.internal_role}')>"
