"""
Tenant Models

Multi-tenant data models for resource isolation and quota management.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, JSON, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TenantStatus(str, Enum):
    """Tenant status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class TenantTier(str, Enum):
    """Tenant subscription tier"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ResourceQuota(Base):
    """
    Resource Quota Model

    Defines resource limits for a tenant.
    """
    __tablename__ = "resource_quotas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Compute quotas
    max_cpu_cores = Column(Integer, nullable=False, default=16)
    max_memory_gb = Column(Integer, nullable=False, default=64)
    max_gpu_count = Column(Integer, nullable=False, default=0)

    # Storage quotas
    max_storage_gb = Column(Integer, nullable=False, default=1000)
    max_object_storage_gb = Column(Integer, nullable=False, default=500)

    # Service quotas
    max_notebooks = Column(Integer, nullable=False, default=5)
    max_training_jobs = Column(Integer, nullable=False, default=10)
    max_inference_services = Column(Integer, nullable=False, default=3)
    max_workflows = Column(Integer, nullable=False, default=20)

    # Data quotas
    max_data_sources = Column(Integer, nullable=False, default=10)
    max_etl_pipelines = Column(Integer, nullable=False, default=15)
    max_data_assets = Column(Integer, nullable=False, default=100)

    # User quotas
    max_users = Column(Integer, nullable=False, default=10)

    # API quotas
    max_api_requests_per_minute = Column(Integer, nullable=False, default=1000)
    max_api_requests_per_day = Column(Integer, nullable=False, default=100000)

    # Concurrency quotas
    max_concurrent_jobs = Column(Integer, nullable=False, default=5)
    max_concurrent_notebooks = Column(Integer, nullable=False, default=3)

    # Additional limits (JSON for flexibility)
    custom_limits = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    tenant = relationship("Tenant", back_populates="resource_quota")


class Tenant(Base):
    """
    Tenant Model

    Represents an organization or team in a multi-tenant system.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Status and tier
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.PENDING, nullable=False)
    tier = Column(SQLEnum(TenantTier), default=TenantTier.BASIC, nullable=False)

    # Contact information
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Billing
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True)

    # Settings
    settings = Column(JSON, nullable=True, default={})
    allowed_ip_ranges = Column(JSON, nullable=True, default=[])  # IP whitelist
    enable_sso = Column(Boolean, default=False)
    sso_provider = Column(String(50), nullable=True)  # saml, oidc, ldap

    # Network isolation
    network_isolated = Column(Boolean, default=False)
    vpc_id = Column(String(100), nullable=True)
    subnet_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    suspended_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)

    # Trial period
    trial_ends_at = Column(DateTime, nullable=True)
    is_trial = Column(Boolean, default=False)

    # Relationships
    resource_quota = relationship("ResourceQuota", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    quota_usage = relationship("QuotaUsage", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("TenantAuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}', status={self.status.value})>"


class TenantUser(Base):
    """
    Tenant User Association

    Links users to tenants with specific roles.
    """
    __tablename__ = "tenant_users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Role within this tenant
    role = Column(String(50), nullable=False, default="member")  # owner, admin, member, viewer

    # Is this the user's primary tenant?
    is_primary = Column(Boolean, default=False)

    # Invited by
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Invitation status
    invitation_status = Column(String(50), default="accepted")  # pending, accepted, declined
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", foreign_keys=[user_id])

    # Unique constraint
    __table_args__ = (
        Index("ix_tenant_users_tenant_user", "tenant_id", "user_id", unique=True),
    )

    def __repr__(self):
        return f"<TenantUser(tenant_id={self.tenant_id}, user_id={self.user_id}, role='{self.role}')>"


class QuotaUsage(Base):
    """
    Quota Usage Tracking

    Tracks current resource usage for a tenant.
    """
    __tablename__ = "quota_usage"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Compute usage
    cpu_cores_used = Column(Integer, nullable=False, default=0)
    memory_gb_used = Column(Numeric(10, 2), nullable=False, default=0)
    gpu_count_used = Column(Integer, nullable=False, default=0)

    # Storage usage
    storage_gb_used = Column(Numeric(10, 2), nullable=False, default=0)
    object_storage_gb_used = Column(Numeric(10, 2), nullable=False, default=0)

    # Service usage
    notebooks_used = Column(Integer, nullable=False, default=0)
    training_jobs_used = Column(Integer, nullable=False, default=0)
    inference_services_used = Column(Integer, nullable=False, default=0)
    workflows_used = Column(Integer, nullable=False, default=0)

    # Data usage
    data_sources_used = Column(Integer, nullable=False, default=0)
    etl_pipelines_used = Column(Integer, nullable=False, default=0)
    data_assets_used = Column(Integer, nullable=False, default=0)

    # User count
    users_count = Column(Integer, nullable=False, default=1)

    # API usage
    api_requests_today = Column(Integer, nullable=False, default=0)
    api_requests_this_minute = Column(Integer, nullable=False, default=0)
    last_api_request_at = Column(DateTime, nullable=True)

    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="quota_usage")

    def __repr__(self):
        return f"<QuotaUsage(tenant_id={self.tenant_id}, cpu={self.cpu_cores_used}, memory={self.memory_gb_used})>"


class TenantAuditLog(Base):
    """
    Tenant Audit Log

    Tracks all actions within a tenant for compliance and debugging.
    """
    __tablename__ = "tenant_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Action info
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # notebook, job, etc.
    resource_id = Column(String(100), nullable=True)

    # User info
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), nullable=True)
    user_name = Column(String(255), nullable=True)

    # Request info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Change details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="success")  # success, failure
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")

    def __repr__(self):
        return f"<TenantAuditLog(tenant_id={self.tenant_id}, action='{self.action}', resource_type='{self.resource_type}')>"


class TenantApiKey(Base):
    """
    Tenant API Key

    API keys for tenant authentication.
    """
    __tablename__ = "tenant_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Key info
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # First few chars for identification

    # Permissions
    scopes = Column(JSON, nullable=True, default=[])  # List of allowed scopes

    # Constraints
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)

    # Created by
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<TenantApiKey(id={self.id}, tenant_id={self.tenant_id}, name='{self.name}', prefix='{self.key_prefix}')>"


class TenantNetworkPolicy(Base):
    """
    Tenant Network Policy

    Defines network isolation and access rules for a tenant.
    """
    __tablename__ = "tenant_network_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Network isolation
    enable_isolation = Column(Boolean, default=False)

    # Allowed inbound/outbound
    allowed_cidr_blocks = Column(JSON, nullable=True, default=[])  # e.g., ["10.0.0.0/8"]
    blocked_cidr_blocks = Column(JSON, nullable=True, default=[])

    # Service mesh
    enable_service_mesh = Column(Boolean, default=False)
    mesh_namespace = Column(String(100), nullable=True)

    # DNS
    custom_dns_servers = Column(JSON, nullable=True, default=[])
    dns_search_domains = Column(JSON, nullable=True, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TenantNetworkPolicy(tenant_id={self.tenant_id}, isolated={self.enable_isolation})>"
