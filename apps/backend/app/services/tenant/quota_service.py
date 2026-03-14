"""
Tenant Quota Service

Manages resource quotas and usage tracking for tenants.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.tenant import (
    Tenant,
    ResourceQuota,
    QuotaUsage,
    TenantStatus,
    TenantTier,
)
from app.models.user import User
from app.core.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class QuotaCheckResult:
    """Result of a quota check"""
    allowed: bool
    resource_type: str
    requested: int
    limit: int
    current: int
    remaining: int
    reason: Optional[str] = None


@dataclass
class QuotaSummary:
    """Summary of tenant quota status"""
    tenant_id: int
    tenant_name: str
    tier: str
    status: str

    # Compute
    cpu_cores: Dict[str, int]
    memory_gb: Dict[str, int]
    gpu_count: Dict[str, int]

    # Storage
    storage_gb: Dict[str, int]
    object_storage_gb: Dict[str, int]

    # Services
    notebooks: Dict[str, int]
    training_jobs: Dict[str, int]
    inference_services: Dict[str, int]
    workflows: Dict[str, int]

    # Data
    data_sources: Dict[str, int]
    etl_pipelines: Dict[str, int]
    data_assets: Dict[str, int]

    # Users
    users: Dict[str, int]

    # API
    api_requests_per_minute: Dict[str, int]
    api_requests_per_day: Dict[str, int]

    # Percentage usage
    overall_usage_percent: float


class QuotaExceededError(Exception):
    """Raised when quota would be exceeded"""

    def __init__(self, resource_type: str, limit: int, current: int, requested: int):
        self.resource_type = resource_type
        self.limit = limit
        self.current = current
        self.requested = requested
        super().__init__(
            f"Quota exceeded for {resource_type}: "
            f"current={current}, requested={requested}, limit={limit}"
        )


class QuotaService:
    """
    Quota Management Service

    Handles quota checking, enforcement, and usage tracking.
    """

    # Default quotas by tier
    DEFAULT_QUOTAS = {
        TenantTier.BASIC: {
            "max_cpu_cores": 8,
            "max_memory_gb": 32,
            "max_gpu_count": 1,
            "max_storage_gb": 500,
            "max_object_storage_gb": 200,
            "max_notebooks": 2,
            "max_training_jobs": 5,
            "max_inference_services": 1,
            "max_workflows": 10,
            "max_data_sources": 5,
            "max_etl_pipelines": 5,
            "max_data_assets": 50,
            "max_users": 5,
            "max_api_requests_per_minute": 100,
            "max_api_requests_per_day": 10000,
            "max_concurrent_jobs": 2,
            "max_concurrent_notebooks": 1,
        },
        TenantTier.STANDARD: {
            "max_cpu_cores": 32,
            "max_memory_gb": 128,
            "max_gpu_count": 4,
            "max_storage_gb": 2000,
            "max_object_storage_gb": 1000,
            "max_notebooks": 10,
            "max_training_jobs": 20,
            "max_inference_services": 5,
            "max_workflows": 50,
            "max_data_sources": 20,
            "max_etl_pipelines": 20,
            "max_data_assets": 500,
            "max_users": 25,
            "max_api_requests_per_minute": 500,
            "max_api_requests_per_day": 100000,
            "max_concurrent_jobs": 10,
            "max_concurrent_notebooks": 5,
        },
        TenantTier.PREMIUM: {
            "max_cpu_cores": 128,
            "max_memory_gb": 512,
            "max_gpu_count": 16,
            "max_storage_gb": 10000,
            "max_object_storage_gb": 5000,
            "max_notebooks": 50,
            "max_training_jobs": 100,
            "max_inference_services": 20,
            "max_workflows": 200,
            "max_data_sources": 100,
            "max_etl_pipelines": 100,
            "max_data_assets": 5000,
            "max_users": 100,
            "max_api_requests_per_minute": 2000,
            "max_api_requests_per_day": 1000000,
            "max_concurrent_jobs": 50,
            "max_concurrent_notebooks": 25,
        },
        TenantTier.ENTERPRISE: {
            "max_cpu_cores": 1024,
            "max_memory_gb": 4096,
            "max_gpu_count": 128,
            "max_storage_gb": 100000,
            "max_object_storage_gb": 50000,
            "max_notebooks": -1,  # Unlimited
            "max_training_jobs": -1,
            "max_inference_services": -1,
            "max_workflows": -1,
            "max_data_sources": -1,
            "max_etl_pipelines": -1,
            "max_data_assets": -1,
            "max_users": -1,
            "max_api_requests_per_minute": 10000,
            "max_api_requests_per_day": 10000000,
            "max_concurrent_jobs": 200,
            "max_concurrent_notebooks": 100,
        },
    }

    def __init__(self, db: Session):
        self.db = db

    def get_tenant_quota(self, tenant_id: int) -> Optional[ResourceQuota]:
        """Get quota definition for a tenant"""
        return (
            self.db.query(ResourceQuota)
            .filter(ResourceQuota.tenant_id == tenant_id)
            .first()
        )

    def get_tenant_usage(self, tenant_id: int) -> Optional[QuotaUsage]:
        """Get current usage for a tenant"""
        return (
            self.db.query(QuotaUsage)
            .filter(QuotaUsage.tenant_id == tenant_id)
            .first()
        )

    def get_quota_summary(self, tenant_id: int) -> QuotaSummary:
        """Get complete quota summary for a tenant"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        quota = self.get_tenant_quota(tenant_id)
        if not quota:
            quota = self._create_default_quota(tenant)

        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            usage = self._create_default_usage(tenant_id)

        def make_dict(limit: int, current: int) -> Dict[str, int]:
            return {
                "limit": -1 if limit == -1 else limit,  # -1 means unlimited
                "current": current,
                "remaining": -1 if limit == -1 else max(0, limit - current),
                "percent": (current / limit * 100) if limit > 0 else 0,
            }

        # Calculate overall usage (average of all limited resources)
        limited_resources = [
            (q.max_cpu_cores, usage.cpu_cores_used),
            (q.max_memory_gb, int(usage.memory_gb_used)),
            (q.max_storage_gb, int(usage.storage_gb_used)),
            (q.max_notebooks, usage.notebooks_used),
            (q.max_training_jobs, usage.training_jobs_used),
            (q.max_inference_services, usage.inference_services_used),
        ]
        overall_percent = (
            sum(cur / lim * 100 for lim, cur in limited_resources if lim > 0)
            / len([lim for lim, _ in limited_resources if lim > 0])
            if any(lim > 0 for lim, _ in limited_resources)
            else 0
        )

        return QuotaSummary(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tier=tenant.tier.value,
            status=tenant.status.value,
            cpu_cores=make_dict(quota.max_cpu_cores, usage.cpu_cores_used),
            memory_gb=make_dict(quota.max_memory_gb, int(usage.memory_gb_used)),
            gpu_count=make_dict(quota.max_gpu_count, usage.gpu_count_used),
            storage_gb=make_dict(quota.max_storage_gb, int(usage.storage_gb_used)),
            object_storage_gb=make_dict(quota.max_object_storage_gb, int(usage.object_storage_gb_used)),
            notebooks=make_dict(quota.max_notebooks, usage.notebooks_used),
            training_jobs=make_dict(quota.max_training_jobs, usage.training_jobs_used),
            inference_services=make_dict(quota.max_inference_services, usage.inference_services_used),
            workflows=make_dict(quota.max_workflows, usage.workflows_used),
            data_sources=make_dict(quota.max_data_sources, usage.data_sources_used),
            etl_pipelines=make_dict(quota.max_etl_pipelines, usage.etl_pipelines_used),
            data_assets=make_dict(quota.max_data_assets, usage.data_assets_used),
            users=make_dict(quota.max_users, usage.users_count),
            api_requests_per_minute=make_dict(quota.max_api_requests_per_minute, usage.api_requests_this_minute),
            api_requests_per_day=make_dict(quota.max_api_requests_per_day, usage.api_requests_today),
            overall_usage_percent=overall_percent,
        )

    def check_quota(
        self,
        tenant_id: int,
        resource_type: str,
        count: int = 1,
    ) -> QuotaCheckResult:
        """
        Check if a quota request can be satisfied.

        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource (e.g., 'notebooks', 'cpu_cores')
            count: Number of units requested

        Returns:
            QuotaCheckResult with allowance status
        """
        quota = self.get_tenant_quota(tenant_id)
        if not quota:
            raise ValueError(f"No quota found for tenant {tenant_id}")

        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            # Create usage record if it doesn't exist
            usage = self._create_default_usage(tenant_id)

        # Map resource type to quota field
        quota_fields = {
            "cpu_cores": ("max_cpu_cores", "cpu_cores_used"),
            "memory_gb": ("max_memory_gb", "memory_gb_used"),
            "gpu_count": ("max_gpu_count", "gpu_count_used"),
            "storage_gb": ("max_storage_gb", "storage_gb_used"),
            "object_storage_gb": ("max_object_storage_gb", "object_storage_gb_used"),
            "notebooks": ("max_notebooks", "notebooks_used"),
            "training_jobs": ("max_training_jobs", "training_jobs_used"),
            "inference_services": ("max_inference_services", "inference_services_used"),
            "workflows": ("max_workflows", "workflows_used"),
            "data_sources": ("max_data_sources", "data_sources_used"),
            "etl_pipelines": ("max_etl_pipelines", "etl_pipelines_used"),
            "data_assets": ("max_data_assets", "data_assets_used"),
            "users": ("max_users", "users_count"),
        }

        if resource_type not in quota_fields:
            raise ValueError(f"Unknown resource type: {resource_type}")

        limit_field, usage_field = quota_fields[resource_type]
        limit = getattr(quota, limit_field)
        current = int(getattr(usage, usage_field)) if isinstance(getattr(usage, usage_field), float) else getattr(usage, usage_field)

        # -1 means unlimited
        if limit == -1:
            return QuotaCheckResult(
                allowed=True,
                resource_type=resource_type,
                requested=count,
                limit=-1,
                current=current,
                remaining=-1,
            )

        remaining = limit - current
        allowed = remaining >= count

        return QuotaCheckResult(
            allowed=allowed,
            resource_type=resource_type,
            requested=count,
            limit=limit,
            current=current,
            remaining=remaining,
            reason="Quota exceeded" if not allowed else None,
        )

    def require_quota(
        self,
        tenant_id: int,
        resource_type: str,
        count: int = 1,
    ) -> None:
        """
        Require quota, raise exception if not available.

        Raises:
            QuotaExceededError: If quota would be exceeded
        """
        result = self.check_quota(tenant_id, resource_type, count)
        if not result.allowed:
            raise QuotaExceededError(
                resource_type=result.resource_type,
                limit=result.limit,
                current=result.current,
                requested=result.requested,
            )

    def allocate_resource(
        self,
        tenant_id: int,
        resource_type: str,
        count: int = 1,
    ) -> bool:
        """
        Allocate resources from tenant quota.

        Returns:
            True if allocated, False if quota exceeded
        """
        result = self.check_quota(tenant_id, resource_type, count)
        if not result.allowed:
            return False

        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            usage = self._create_default_usage(tenant_id)

        quota_fields = {
            "cpu_cores": "cpu_cores_used",
            "memory_gb": "memory_gb_used",
            "gpu_count": "gpu_count_used",
            "storage_gb": "storage_gb_used",
            "object_storage_gb": "object_storage_gb_used",
            "notebooks": "notebooks_used",
            "training_jobs": "training_jobs_used",
            "inference_services": "inference_services_used",
            "workflows": "workflows_used",
            "data_sources": "data_sources_used",
            "etl_pipelines": "etl_pipelines_used",
            "data_assets": "data_assets_used",
            "users": "users_count",
        }

        if resource_type not in quota_fields:
            raise ValueError(f"Unknown resource type: {resource_type}")

        usage_field = quota_fields[resource_type]
        current = getattr(usage, usage_field)

        if isinstance(current, float):
            setattr(usage, usage_field, current + count)
        else:
            setattr(usage, usage_field, current + count)

        usage.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Allocated {count} {resource_type} for tenant {tenant_id}")
        return True

    def release_resource(
        self,
        tenant_id: int,
        resource_type: str,
        count: int = 1,
    ) -> bool:
        """
        Release resources back to tenant quota.
        """
        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            logger.warning(f"No usage record found for tenant {tenant_id}")
            return False

        quota_fields = {
            "cpu_cores": "cpu_cores_used",
            "memory_gb": "memory_gb_used",
            "gpu_count": "gpu_count_used",
            "storage_gb": "storage_gb_used",
            "object_storage_gb": "object_storage_gb_used",
            "notebooks": "notebooks_used",
            "training_jobs": "training_jobs_used",
            "inference_services": "inference_services_used",
            "workflows": "workflows_used",
            "data_sources": "data_sources_used",
            "etl_pipelines": "etl_pipelines_used",
            "data_assets": "data_assets_used",
            "users": "users_count",
        }

        if resource_type not in quota_fields:
            raise ValueError(f"Unknown resource type: {resource_type}")

        usage_field = quota_fields[resource_type]
        current = getattr(usage, usage_field)

        # Don't go below zero
        new_value = max(0, current - count)

        if isinstance(current, float):
            setattr(usage, usage_field, float(new_value))
        else:
            setattr(usage, usage_field, new_value)

        usage.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Released {count} {resource_type} for tenant {tenant_id}")
        return True

    def record_api_request(self, tenant_id: int) -> None:
        """Record an API request for rate limiting"""
        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            usage = self._create_default_usage(tenant_id)

        now = datetime.utcnow()

        # Reset counters if needed
        if usage.last_api_request_at:
            # Check if we're in a new minute
            if (now - usage.last_api_request_at).total_seconds() >= 60:
                usage.api_requests_this_minute = 0
            # Check if we're in a new day
            if (now.date() - usage.last_api_request_at.date()).days >= 1:
                usage.api_requests_today = 0

        usage.api_requests_this_minute += 1
        usage.api_requests_today += 1
        usage.last_api_request_at = now
        usage.updated_at = now
        self.db.commit()

    def check_api_rate_limit(self, tenant_id: int) -> QuotaCheckResult:
        """Check if tenant is within API rate limits"""
        quota = self.get_tenant_quota(tenant_id)
        if not quota:
            raise ValueError(f"No quota found for tenant {tenant_id}")

        usage = self.get_tenant_usage(tenant_id)
        if not usage:
            return QuotaCheckResult(
                allowed=True,
                resource_type="api_requests",
                requested=1,
                limit=quota.max_api_requests_per_minute,
                current=0,
                remaining=quota.max_api_requests_per_minute,
            )

        # Reset counters if needed
        now = datetime.utcnow()
        if usage.last_api_request_at:
            if (now - usage.last_api_request_at).total_seconds() >= 60:
                usage.api_requests_this_minute = 0
                usage.updated_at = now
                self.db.commit()
            if (now.date() - usage.last_api_request_at.date()).days >= 1:
                usage.api_requests_today = 0
                usage.updated_at = now
                self.db.commit()

        # Check per-minute limit
        if usage.api_requests_this_minute >= quota.max_api_requests_per_minute:
            return QuotaCheckResult(
                allowed=False,
                resource_type="api_requests_per_minute",
                requested=1,
                limit=quota.max_api_requests_per_minute,
                current=usage.api_requests_this_minute,
                remaining=0,
                reason="Rate limit exceeded (per minute)",
            )

        # Check per-day limit
        if usage.api_requests_today >= quota.max_api_requests_per_day:
            return QuotaCheckResult(
                allowed=False,
                resource_type="api_requests_per_day",
                requested=1,
                limit=quota.max_api_requests_per_day,
                current=usage.api_requests_today,
                remaining=0,
                reason="Rate limit exceeded (per day)",
            )

        return QuotaCheckResult(
            allowed=True,
            resource_type="api_requests",
            requested=1,
            limit=quota.max_api_requests_per_minute,
            current=usage.api_requests_this_minute,
            remaining=quota.max_api_requests_per_minute - usage.api_requests_this_minute,
        )

    def _create_default_quota(self, tenant: Tenant) -> ResourceQuota:
        """Create default quota for a tenant based on tier"""
        defaults = self.DEFAULT_QUOTAS.get(tenant.tier, self.DEFAULT_QUOTAS[TenantTier.BASIC])

        quota = ResourceQuota(tenant_id=tenant.id, **defaults)
        self.db.add(quota)
        self.db.commit()
        self.db.refresh(quota)

        logger.info(f"Created default quota for tenant {tenant.id} (tier={tenant.tier.value})")
        return quota

    def _create_default_usage(self, tenant_id: int) -> QuotaUsage:
        """Create default usage record for a tenant"""
        usage = QuotaUsage(tenant_id=tenant_id)
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)

        logger.info(f"Created default usage record for tenant {tenant_id}")
        return usage

    def update_tier(self, tenant_id: int, new_tier: TenantTier) -> ResourceQuota:
        """Update tenant tier and adjust quota"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        tenant.tier = new_tier

        # Update quota
        quota = self.get_tenant_quota(tenant_id)
        if not quota:
            quota = self._create_default_quota(tenant)
        else:
            # Apply new tier defaults
            defaults = self.DEFAULT_QUOTAS[new_tier]
            for field, value in defaults.items():
                setattr(quota, field, value)
            quota.updated_at = datetime.utcnow()
            self.db.commit()

        logger.info(f"Updated tenant {tenant_id} to tier {new_tier.value}")
        return quota

    def get_overage_tenants(self) -> List[Dict[str, Any]]:
        """Get tenants that are over their quota limits"""
        overages = []

        tenants = self.db.query(Tenant).filter(Tenant.status == TenantStatus.ACTIVE).all()

        for tenant in tenants:
            summary = self.get_quota_summary(tenant.id)

            # Check for overages (where remaining < 0 or percent > 100)
            overage_fields = []
            if summary.cpu_cores["remaining"] < 0:
                overage_fields.append("cpu_cores")
            if summary.memory_gb["remaining"] < 0:
                overage_fields.append("memory_gb")
            if summary.notebooks["remaining"] < 0:
                overage_fields.append("notebooks")
            if summary.training_jobs["remaining"] < 0:
                overage_fields.append("training_jobs")

            if overage_fields:
                overages.append({
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "tier": tenant.tier.value,
                    "overage_fields": overage_fields,
                    "summary": summary,
                })

        return overages


def get_quota_service(db: Session) -> QuotaService:
    """Get quota service instance"""
    return QuotaService(db)
