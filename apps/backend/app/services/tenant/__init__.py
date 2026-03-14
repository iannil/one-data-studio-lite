"""
Tenant Service Package

Provides multi-tenant isolation, quota management, and tenant administration.
"""

from .tenant_service import (
    TenantService,
    get_tenant_service,
    TenantAlreadyExistsError,
    TenantNotFoundError,
)

from .quota_service import (
    QuotaService,
    get_quota_service,
    QuotaCheckResult,
    QuotaSummary,
    QuotaExceededError,
)

from app.models.tenant import (
    Tenant,
    TenantUser,
    ResourceQuota,
    QuotaUsage,
    TenantAuditLog,
    TenantApiKey,
    TenantNetworkPolicy,
    TenantStatus,
    TenantTier,
)

__all__ = [
    # Tenant Service
    "TenantService",
    "get_tenant_service",
    "TenantAlreadyExistsError",
    "TenantNotFoundError",
    # Quota Service
    "QuotaService",
    "get_quota_service",
    "QuotaCheckResult",
    "QuotaSummary",
    "QuotaExceededError",
    # Models
    "Tenant",
    "TenantUser",
    "ResourceQuota",
    "QuotaUsage",
    "TenantAuditLog",
    "TenantApiKey",
    "TenantNetworkPolicy",
    "TenantStatus",
    "TenantTier",
]
