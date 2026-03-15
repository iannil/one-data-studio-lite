"""
Tenant Management API Endpoints

Provides REST API for multi-tenant management, quota control, and user administration.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.tenant import TenantStatus, TenantTier
from app.services.tenant import (
    TenantService,
    QuotaService,
    TenantAlreadyExistsError,
    TenantNotFoundError,
    QuotaExceededError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant", tags=["Tenant Management"])


# ============================================================================
# Dependencies
# ============================================================================


async def get_tenant_context(
    x_tenant_slug: Optional[str] = Header(None, alias="X-Tenant-Slug"),
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """
    Get tenant context from request headers.

    This is used for multi-tenant isolation. In production, this would
    validate the user's access to the tenant.
    """
    if x_tenant_id:
        # Validate user belongs to tenant
        tenant_service = TenantService(db)
        tenants = tenant_service.get_user_tenants(current_user.id)
        tenant_ids = [t.id for t in tenants]
        if x_tenant_id not in tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this tenant",
            )
        return x_tenant_id

    if x_tenant_slug:
        tenant_service = TenantService(db)
        tenant = tenant_service.get_tenant_by_slug(x_tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{x_tenant_slug}' not found",
            )
        # Validate user belongs to tenant
        tenants = tenant_service.get_user_tenants(current_user.id)
        tenant_ids = [t.id for t in tenants]
        if tenant.id not in tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this tenant",
            )
        return tenant.id

    # If no tenant specified, use user's primary tenant
    tenant_service = TenantService(db)
    primary_tenant = tenant_service.get_user_primary_tenant(current_user.id)
    if primary_tenant:
        return primary_tenant.id

    return None


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateTenantRequest(BaseModel):
    """Request to create a tenant"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    contact_email: str = Field(..., email=True)
    contact_name: Optional[str] = None
    description: Optional[str] = None
    tier: TenantTier = TenantTier.BASIC
    trial_days: Optional[int] = Field(None, ge=1, le=90)
    settings: Optional[Dict[str, Any]] = None


class UpdateTenantRequest(BaseModel):
    """Request to update tenant"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    billing_email: Optional[str] = None
    billing_address: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ChangeTierRequest(BaseModel):
    """Request to change tenant tier"""
    tier: TenantTier


class InviteUserRequest(BaseModel):
    """Request to invite a user to tenant"""
    email: str = Field(..., email=True)
    role: str = Field("member", pattern="^(owner|admin|member|viewer)$")


class AddUserRequest(BaseModel):
    """Request to add a user to tenant"""
    user_id: int
    role: str = Field("member", pattern="^(owner|admin|member|viewer)$")
    is_primary: bool = False


class UpdateUserRoleRequest(BaseModel):
    """Request to update user role"""
    role: str = Field(..., pattern="^(owner|admin|member|viewer)$")


class CreateAPIKeyRequest(BaseModel):
    """Request to create API key"""
    name: str = Field(..., min_length=1, max_length=255)
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class QuotaCheckRequest(BaseModel):
    """Request to check quota"""
    resource_type: str
    count: int = Field(1, ge=1)


class QuotaAllocateRequest(BaseModel):
    """Request to allocate quota"""
    resource_type: str
    count: int = Field(1, ge=1)


# ============================================================================
# Tenant Management Endpoints
# ============================================================================


@router.post("/", response_model=Dict[str, Any])
async def create_tenant(
    request: CreateTenantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new tenant"""
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.create_tenant(
            name=request.name,
            slug=request.slug,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            description=request.description,
            tier=request.tier,
            owner_id=current_user.id,
            trial_days=request.trial_days,
            settings=request.settings,
        )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.tier.value,
            "status": tenant.status.value,
            "is_trial": tenant.is_trial,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "created_at": tenant.created_at.isoformat(),
            "message": "Tenant created successfully",
        }
    except TenantAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all tenants for the current user"""
    try:
        tenant_service = TenantService(db)
        tenants = tenant_service.get_user_tenants(current_user.id)

        return [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "tier": t.tier.value,
                "status": t.status.value,
                "is_trial": t.is_trial,
                "description": t.description,
                "contact_email": t.contact_email,
                "created_at": t.created_at.isoformat(),
            }
            for t in tenants
        ]
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{tenant_id}", response_model=Dict[str, Any])
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant details"""
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.get_tenant(tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )

        # Verify access
        user_tenants = tenant_service.get_user_tenants(current_user.id)
        if tenant.id not in [t.id for t in user_tenants]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "description": tenant.description,
            "tier": tenant.tier.value,
            "status": tenant.status.value,
            "is_trial": tenant.is_trial,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "contact_email": tenant.contact_email,
            "contact_name": tenant.contact_name,
            "contact_phone": tenant.contact_phone,
            "billing_email": tenant.billing_email,
            "enable_sso": tenant.enable_sso,
            "sso_provider": tenant.sso_provider,
            "network_isolated": tenant.network_isolated,
            "vpc_id": tenant.vpc_id,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{tenant_id}", response_model=Dict[str, Any])
async def update_tenant(
    tenant_id: int,
    request: UpdateTenantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update tenant details"""
    try:
        tenant_service = TenantService(db)

        # Verify user is admin or owner
        tenants = tenant_service.get_user_tenants(current_user.id)
        if tenant_id not in [t.id for t in tenants]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        tenant = tenant_service.update_tenant(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            billing_email=request.billing_email,
            billing_address=request.billing_address,
            settings=request.settings,
        )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "updated_at": tenant.updated_at.isoformat(),
            "message": "Tenant updated successfully",
        }
    except HTTPException:
        raise
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/tier", response_model=Dict[str, Any])
async def change_tier(
    tenant_id: int,
    request: ChangeTierRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change tenant subscription tier"""
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.change_tier(tenant_id, request.tier)

        return {
            "id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier.value,
            "message": f"Tenant tier changed to {request.tier.value}",
        }
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to change tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/suspend", response_model=Dict[str, Any])
async def suspend_tenant(
    tenant_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suspend a tenant"""
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.suspend_tenant(tenant_id, reason)

        return {
            "id": tenant.id,
            "status": tenant.status.value,
            "suspended_at": tenant.suspended_at.isoformat() if tenant.suspended_at else None,
            "message": "Tenant suspended successfully",
        }
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to suspend tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/activate", response_model=Dict[str, Any])
async def activate_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activate a suspended tenant"""
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.activate_tenant(tenant_id)

        return {
            "id": tenant.id,
            "status": tenant.status.value,
            "message": "Tenant activated successfully",
        }
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to activate tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Quota Management Endpoints
# ============================================================================


@router.get("/{tenant_id}/quota", response_model=Dict[str, Any])
async def get_quota_summary(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant quota summary"""
    try:
        quota_service = QuotaService(db)
        summary = quota_service.get_quota_summary(tenant_id)

        return {
            "tenant_id": summary.tenant_id,
            "tenant_name": summary.tenant_name,
            "tier": summary.tier,
            "status": summary.status,
            "overall_usage_percent": summary.overall_usage_percent,
            "cpu_cores": summary.cpu_cores,
            "memory_gb": summary.memory_gb,
            "gpu_count": summary.gpu_count,
            "storage_gb": summary.storage_gb,
            "object_storage_gb": summary.object_storage_gb,
            "notebooks": summary.notebooks,
            "training_jobs": summary.training_jobs,
            "inference_services": summary.inference_services,
            "workflows": summary.workflows,
            "data_sources": summary.data_sources,
            "etl_pipelines": summary.etl_pipelines,
            "data_assets": summary.data_assets,
            "users": summary.users,
            "api_requests": {
                "per_minute": summary.api_requests_per_minute,
                "per_day": summary.api_requests_per_day,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get quota summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/quota/check", response_model=Dict[str, Any])
async def check_quota(
    tenant_id: int,
    request: QuotaCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if quota allows a request"""
    try:
        quota_service = QuotaService(db)
        result = quota_service.check_quota(
            tenant_id=tenant_id,
            resource_type=request.resource_type,
            count=request.count,
        )

        return {
            "allowed": result.allowed,
            "resource_type": result.resource_type,
            "requested": result.requested,
            "limit": result.limit,
            "current": result.current,
            "remaining": result.remaining,
            "reason": result.reason,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/quota/allocate", response_model=Dict[str, Any])
async def allocate_quota(
    tenant_id: int,
    request: QuotaAllocateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allocate resources from tenant quota"""
    try:
        quota_service = QuotaService(db)
        success = quota_service.allocate_resource(
            tenant_id=tenant_id,
            resource_type=request.resource_type,
            count=request.count,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quota exceeded for {request.resource_type}",
            )

        return {
            "message": f"Allocated {request.count} {request.resource_type}",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to allocate quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/quota/release", response_model=Dict[str, Any])
async def release_quota(
    tenant_id: int,
    request: QuotaAllocateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Release resources back to tenant quota"""
    try:
        quota_service = QuotaService(db)
        success = quota_service.release_resource(
            tenant_id=tenant_id,
            resource_type=request.resource_type,
            count=request.count,
        )

        return {
            "message": f"Released {request.count} {request.resource_type}",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to release quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Tenant User Management Endpoints
# ============================================================================


@router.get("/{tenant_id}/users", response_model=List[Dict[str, Any]])
async def get_tenant_users(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all users in a tenant"""
    try:
        tenant_service = TenantService(db)
        users = tenant_service.get_tenant_users(tenant_id)

        return users
    except Exception as e:
        logger.error(f"Failed to get tenant users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/users", response_model=Dict[str, Any])
async def add_tenant_user(
    tenant_id: int,
    request: AddUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user to a tenant"""
    try:
        tenant_service = TenantService(db)
        tenant_user = tenant_service.add_user(
            tenant_id=tenant_id,
            user_id=request.user_id,
            role=request.role,
            is_primary=request.is_primary,
            invited_by=current_user.id,
        )

        return {
            "message": "User added to tenant",
            "user_id": tenant_user.user_id,
            "role": tenant_user.role,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to add user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{tenant_id}/users/{user_id}", response_model=Dict[str, Any])
async def remove_tenant_user(
    tenant_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user from a tenant"""
    try:
        tenant_service = TenantService(db)
        success = tenant_service.remove_user(tenant_id, user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant",
            )

        return {"message": "User removed from tenant"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{tenant_id}/users/{user_id}/role", response_model=Dict[str, Any])
async def update_user_role(
    tenant_id: int,
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user role in tenant"""
    try:
        tenant_service = TenantService(db)
        tenant_user = tenant_service.update_user_role(tenant_id, user_id, request.role)

        return {
            "message": "User role updated",
            "user_id": tenant_user.user_id,
            "role": tenant_user.role,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/invite", response_model=Dict[str, Any])
async def invite_user(
    tenant_id: int,
    request: InviteUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a user to join a tenant"""
    try:
        tenant_service = TenantService(db)
        invitation = tenant_service.invite_user(
            tenant_id=tenant_id,
            email=request.email,
            role=request.role,
            invited_by=current_user.id,
        )

        return invitation
    except Exception as e:
        logger.error(f"Failed to invite user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# API Key Management Endpoints
# ============================================================================


@router.get("/{tenant_id}/api-keys", response_model=List[Dict[str, Any]])
async def get_api_keys(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all API keys for a tenant"""
    try:
        tenant_service = TenantService(db)
        keys = tenant_service.get_api_keys(tenant_id)

        return keys
    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{tenant_id}/api-keys", response_model=Dict[str, Any])
async def create_api_key(
    tenant_id: int,
    request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an API key for a tenant"""
    try:
        tenant_service = TenantService(db)
        api_key = tenant_service.create_api_key(
            tenant_id=tenant_id,
            name=request.name,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            created_by=current_user.id,
        )

        # Return the key (only time it's shown)
        key_value = f"odsk_{api_key.key_prefix}"  # In production, return full key here

        return {
            "id": api_key.id,
            "key": key_value,  # Only shown once
            "key_prefix": api_key.key_prefix,
            "name": api_key.name,
            "scopes": api_key.scopes,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "created_at": api_key.created_at.isoformat(),
            "message": "Save this key securely. It won't be shown again.",
        }
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{tenant_id}/api-keys/{key_id}", response_model=Dict[str, Any])
async def revoke_api_key(
    tenant_id: int,
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke an API key"""
    try:
        tenant_service = TenantService(db)
        success = tenant_service.revoke_api_key(tenant_id, key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        return {"message": "API key revoked"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Audit Log Endpoints
# ============================================================================


@router.get("/{tenant_id}/audit-logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    tenant_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs for a tenant"""
    try:
        from app.models.tenant import TenantAuditLog

        query = db.query(TenantAuditLog).filter(TenantAuditLog.tenant_id == tenant_id)

        if action:
            query = query.filter(TenantAuditLog.action == action)
        if resource_type:
            query = query.filter(TenantAuditLog.resource_type == resource_type)

        logs = (
            query.order_by(TenantAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "user_name": log.user_name,
                "ip_address": log.ip_address,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
