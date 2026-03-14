"""
Multi-Tenant / Organization Management Service

Provides tenant isolation, organization management, and resource quotas.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.config import settings


class TenantPlan(str, Enum):
    """Tenant subscription plans"""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    """Tenant status"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


@dataclass
class ResourceQuota:
    """Resource quota limits"""

    # Compute resources
    max_cpu_cores: int
    max_memory_gb: int
    max_gpu: int

    # Storage
    max_storage_gb: int
    max_models: int
    max_documents_kb: int

    # API limits
    api_requests_per_day: int
    api_rate_limit_per_minute: int

    # Users
    max_users: int

    # MLOps resources
    max_experiments: int
    max_deployments: int
    max_concurrent_jobs: int


# Default quotas by plan
PLAN_QUOTAS: Dict[TenantPlan, ResourceQuota] = {
    TenantPlan.FREE: ResourceQuota(
        max_cpu_cores=4,
        max_memory_gb=16,
        max_gpu=0,
        max_storage_gb=10,
        max_models=5,
        max_documents_kb=100,
        api_requests_per_day=1000,
        api_rate_limit_per_minute=10,
        max_users=3,
        max_experiments=5,
        max_deployments=1,
        max_concurrent_jobs=1,
    ),
    TenantPlan.BASIC: ResourceQuota(
        max_cpu_cores=16,
        max_memory_gb=64,
        max_gpu=1,
        max_storage_gb=100,
        max_models=50,
        max_documents_kb=1000,
        api_requests_per_day=10000,
        api_rate_limit_per_minute=60,
        max_users=10,
        max_experiments=50,
        max_deployments=5,
        max_concurrent_jobs=3,
    ),
    TenantPlan.PROFESSIONAL: ResourceQuota(
        max_cpu_cores=64,
        max_memory_gb=256,
        max_gpu=4,
        max_storage_gb=500,
        max_models=200,
        max_documents_kb=10000,
        api_requests_per_day=100000,
        api_rate_limit_per_minute=300,
        max_users=50,
        max_experiments=200,
        max_deployments=20,
        max_concurrent_jobs=10,
    ),
    TenantPlan.ENTERPRISE: ResourceQuota(
        max_cpu_cores=256,
        max_memory_gb=1024,
        max_gpu=16,
        max_storage_gb=2048,
        max_models=1000,
        max_documents_kb=100000,
        api_requests_per_day=1000000,
        api_rate_limit_per_minute=1000,
        max_users=500,
        max_experiments=1000,
        max_deployments=100,
        max_concurrent_jobs=50,
    ),
}


class Tenant:
    """Tenant/Organization representation"""

    def __init__(
        self,
        id: str,
        name: str,
        slug: str,
        plan: TenantPlan,
        status: TenantStatus = TenantStatus.ACTIVE,
    ):
        self.id = id
        self.name = name
        self.slug = slug
        self.plan = plan
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.trial_ends_at: Optional[datetime] = None

        # Get quota for plan
        self.quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS[TenantPlan.FREE])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan.value,
            "status": self.status.value,
            "quota": {
                "max_cpu_cores": self.quota.max_cpu_cores,
                "max_memory_gb": self.quota.max_memory_gb,
                "max_gpu": self.quota.max_gpu,
                "max_storage_gb": self.quota.max_storage_gb,
                "max_models": self.quota.max_models,
                "max_documents_kb": self.quota.max_documents_kb,
                "api_requests_per_day": self.quota.api_requests_per_day,
                "api_rate_limit_per_minute": self.quota.api_rate_limit_per_minute,
                "max_users": self.quota.max_users,
                "max_experiments": self.quota.max_experiments,
                "max_deployments": self.quota.max_deployments,
                "max_concurrent_jobs": self.quota.max_concurrent_jobs,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
        }


class OrganizationMember:
    """Member of an organization"""

    def __init__(
        self,
        id: str,
        organization_id: str,
        user_id: str,
        role: str,
    ):
        self.id = id
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role  # owner, admin, member, viewer
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class OrganizationRole(str, Enum):
    """Organization roles with permission levels"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Role permissions
ROLE_PERMISSIONS: Dict[OrganizationRole, List[str]] = {
    OrganizationRole.OWNER: [
        "*",
        "users.invite",
        "users.remove",
        "users.manage",
        "billing.view",
        "billing.manage",
        "settings.edit",
        "resources.view",
        "resources.manage",
        "projects.create",
        "projects.delete",
        "deployments.create",
        "deployments.delete",
    ],
    OrganizationRole.ADMIN: [
        "users.invite",
        "users.remove",
        "billing.view",
        "settings.edit",
        "resources.view",
        "resources.manage",
        "projects.create",
        "deployments.create",
    ],
    OrganizationRole.MEMBER: [
        "resources.view",
        "projects.create",
        "deployments.create",
    ],
    OrganizationRole.VIEWER: [
        "resources.view",
    ],
}


class TenantService:
    """
    Service for managing tenants/organizations.
    """

    def __init__(self):
        # In production, load from database
        self.tenants: Dict[str, Tenant] = {}
        self.members: Dict[str, List[OrganizationMember]] = {}

    def create_tenant(
        self,
        name: str,
        slug: str,
        plan: TenantPlan = TenantPlan.FREE,
        trial_days: int = 0,
    ) -> Tenant:
        """Create a new tenant"""
        tenant_id = str(uuid.uuid4())

        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug,
            plan=plan,
        )

        if trial_days > 0:
            tenant.status = TenantStatus.TRIAL
            tenant.trial_ends_at = datetime.utcnow() + timedelta(days=trial_days)

        self.tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        for tenant in self.tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        plan: Optional[TenantPlan] = None,
    ) -> List[Tenant]:
        """List tenants with optional filters"""
        tenants = list(self.tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]
        if plan:
            tenants = [t for t in tenants if t.plan == plan]

        return tenants

    def update_tenant_plan(
        self, tenant_id: str, new_plan: TenantPlan
    ) -> Optional[Tenant]:
        """Update tenant plan"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None

        tenant.plan = new_plan
        tenant.quota = PLAN_QUOTAS[new_plan]
        tenant.updated_at = datetime.utcnow()
        return tenant

    def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend a tenant"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.utcnow()
        return True

    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()
        return True

    def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole = OrganizationRole.MEMBER,
    ) -> OrganizationMember:
        """Add a member to an organization"""
        member_id = str(uuid.uuid4())

        member = OrganizationMember(
            id=member_id,
            organization_id=organization_id,
            user_id=user_id,
            role=role.value,
        )

        if organization_id not in self.members:
            self.members[organization_id] = []

        self.members[organization_id].append(member)
        return member

    def remove_member(
        self, organization_id: str, member_id: str
    ) -> bool:
        """Remove a member from an organization"""
        if organization_id not in self.members:
            return False

        self.members[organization_id] = [
            m for m in self.members[organization_id] if m.id != member_id
        ]
        return True

    def get_members(self, organization_id: str) -> List[OrganizationMember]:
        """Get all members of an organization"""
        return self.members.get(organization_id, [])

    def get_member_role(
        self, organization_id: str, user_id: str
    ) -> Optional[OrganizationRole]:
        """Get role of a user in an organization"""
        members = self.get_members(organization_id)
        for member in members:
            if member.user_id == user_id:
                return OrganizationRole(member.role)
        return None

    def update_member_role(
        self, organization_id: str, member_id: str, new_role: OrganizationRole
    ) -> bool:
        """Update member role"""
        members = self.members.get(organization_id, [])
        for member in members:
            if member.id == member_id:
                member.role = new_role.value
                member.updated_at = datetime.utcnow()
                return True
        return False

    def check_permission(
        self,
        organization_id: str,
        user_id: str,
        permission: str,
    ) -> bool:
        """
        Check if a user has a permission in an organization.

        Args:
            organization_id: Organization ID
            user_id: User ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        role = self.get_member_role(organization_id, user_id)
        if not role:
            return False

        permissions = ROLE_PERMISSIONS.get(role, [])

        # Owner has all permissions
        if "*" in permissions:
            return True

        return permission in permissions

    def get_resource_usage(
        self, tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get current resource usage for a tenant.

        In production, this would query actual usage metrics.
        """
        # Simulated usage data
        return {
            "cpu_cores_used": 2,
            "memory_gb_used": 8,
            "gpu_used": 0,
            "storage_gb_used": 15.5,
            "model_count": 3,
            "document_count": 150,
            "api_requests_today": 45,
            "user_count": 5,
            "experiment_count": 8,
            "deployment_count": 2,
            "concurrent_jobs": 0,
        }

    def check_resource_limit(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a resource request is within tenant limits.

        Args:
            tenant_id: Tenant ID
            resource: Resource type
            amount: Amount requested

        Returns:
            Tuple of (allowed, error_message)
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False, "Tenant not found"

        usage = self.get_resource_usage(tenant_id)
        quota = tenant.quota

        resource_map = {
            "cpu_cores": (usage["cpu_cores_used"], quota.max_cpu_cores),
            "memory_gb": (usage["memory_gb_used"], quota.max_memory_gb),
            "gpu": (usage["gpu_used"], quota.max_gpu),
            "storage_gb": (usage["storage_gb_used"], quota.max_storage_gb),
            "models": (usage["model_count"], quota.max_models),
            "documents": (usage["document_count"], quota.max_documents_kb),
            "api_requests": (usage["api_requests_today"], quota.api_requests_per_day),
            "users": (usage["user_count"], quota.max_users),
            "experiments": (usage["experiment_count"], quota.max_experiments),
            "deployments": (usage["deployment_count"], quota.max_deployments),
            "jobs": (usage["concurrent_jobs"], quota.max_concurrent_jobs),
        }

        if resource not in resource_map:
            return False, f"Unknown resource: {resource}"

        used, limit = resource_map[resource]

        if used + amount > limit:
            return False, f"Resource limit exceeded: {used}/{limit} {resource}"

        return True, None

    def get_tenant_statistics(
        self, tenant_id: str
    ) -> Dict[str, Any]:
        """Get usage statistics for a tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}

        usage = self.get_resource_usage(tenant_id)
        quota = tenant.quota

        return {
            "tenant_id": tenant_id,
            "plan": tenant.plan.value,
            "status": tenant.status.value,
            "usage": usage,
            "quotas": {
                "cpu_cores": {"used": usage["cpu_cores_used"], "limit": quota.max_cpu_cores},
                "memory_gb": {"used": usage["memory_gb_used"], "limit": quota.max_memory_gb},
                "gpu": {"used": usage["gpu_used"], "limit": quota.max_gpu},
                "storage_gb": {"used": usage["storage_gb_used"], "limit": quota.max_storage_gb},
                "models": {"used": usage["model_count"], "limit": quota.max_models},
                "documents": {"used": usage["document_count"], "limit": quota.max_documents_kb},
                "api_requests": {"used": usage["api_requests_today"], "limit": quota.api_requests_per_day},
                "users": {"used": usage["user_count"], "limit": quota.max_users},
                "experiments": {"used": usage["experiment_count"], "limit": quota.max_experiments},
                "deployments": {"used": usage["deployment_count"], "limit": quota.max_deployments},
                "jobs": {"used": usage["concurrent_jobs"], "limit": quota.max_concurrent_jobs},
            },
            "utilization": {
                "cpu_percent": round(usage["cpu_cores_used"] / quota.max_cpu_cores * 100, 1),
                "memory_percent": round(usage["memory_gb_used"] / quota.max_memory_gb * 100, 1),
                "storage_percent": round(usage["storage_gb_used"] / quota.max_storage_gb * 100, 1),
                "api_requests_percent": round(usage["api_requests_today"] / quota.api_requests_per_day * 100, 1),
            },
        }


# Global service instance
tenant_service = TenantService()
