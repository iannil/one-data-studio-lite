"""API endpoints for permission management."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionSuggestionResponse(BaseModel):
    """Response schema for permission suggestions."""
    asset_id: str | None = None
    asset_name: str | None = None
    user_id: str | None = None
    user_email: str | None = None
    access_level: str | None = None
    permission_rules: dict[str, Any] | None = None
    suggested_roles: list[dict[str, Any]] | None = None
    recommendations: list[str] | None = None
    roles: list[dict[str, Any]] | None = None
    max_role_level: int | None = None
    accessible_assets: list[dict[str, Any]] | None = None
    restricted_assets: list[dict[str, Any]] | None = None
    upgrade_suggestions: list[dict[str, Any]] | None = None


class AutoConfigureRequest(BaseModel):
    """Request schema for auto-configure permissions."""
    user_id: uuid.UUID
    department: str | None = None


class AutoConfigureResponse(BaseModel):
    """Response schema for auto-configure permissions."""
    user_id: str
    user_email: str
    department: str
    ai_suggestions: dict[str, Any]
    current_roles: list[dict[str, Any]]


class PermissionChangeRequest(BaseModel):
    """Request schema for recording permission change."""
    target_user_id: uuid.UUID
    action: str = Field(..., pattern=r"^(grant|revoke|modify)$")
    details: dict[str, Any]


class PermissionCheckRequest(BaseModel):
    """Request schema for permission check."""
    user_id: uuid.UUID
    asset_id: uuid.UUID
    operation: str = Field(default="read", pattern=r"^(read|export|write)$")


class PermissionCheckResponse(BaseModel):
    """Response schema for permission check."""
    allowed: bool
    reason: str
    user_id: str
    asset_id: str
    operation: str | None = None
    required_level: int | None = None


class AuditEntryResponse(BaseModel):
    """Response schema for audit entry."""
    id: str
    actor_id: str
    target_user_id: str | None
    change_type: str | None
    details: dict[str, Any]
    created_at: str


@router.get("/suggest/asset/{asset_id}", response_model=PermissionSuggestionResponse)
async def suggest_permissions_for_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> PermissionSuggestionResponse:
    """Suggest permissions based on asset sensitivity level."""
    service = PermissionService(db)

    try:
        result = await service.suggest_permissions_for_asset(asset_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return PermissionSuggestionResponse(**result)


@router.get("/suggest/user/{user_id}", response_model=PermissionSuggestionResponse)
async def suggest_permissions_for_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> PermissionSuggestionResponse:
    """Suggest permissions based on user's role."""
    service = PermissionService(db)

    try:
        result = await service.suggest_permissions_for_user(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return PermissionSuggestionResponse(**result)


@router.post("/auto-configure", response_model=AutoConfigureResponse)
async def auto_configure_permissions(
    request: AutoConfigureRequest,
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> AutoConfigureResponse:
    """Automatically configure permissions based on user attributes using AI."""
    service = PermissionService(db)

    try:
        result = await service.auto_configure_permissions(
            user_id=request.user_id,
            department=request.department,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return AutoConfigureResponse(**result)


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> PermissionCheckResponse:
    """Check if a user has permission to perform an operation on an asset."""
    service = PermissionService(db)

    result = await service.check_access_permission(
        user_id=request.user_id,
        asset_id=request.asset_id,
        operation=request.operation,
    )

    return PermissionCheckResponse(**result)


@router.post("/audit", status_code=status.HTTP_201_CREATED)
async def record_permission_change(
    request: PermissionChangeRequest,
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> dict[str, str]:
    """Record a permission change in the audit log."""
    service = PermissionService(db)

    audit_log = await service.audit_permission_change(
        user_id=request.target_user_id,
        actor_id=current_user.id,
        action=request.action,
        details=request.details,
    )

    return {
        "status": "recorded",
        "audit_id": str(audit_log.id),
    }


@router.get("/audit", response_model=list[AuditEntryResponse])
async def get_permission_audit_history(
    user_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(DBSession),
    current_user: Any = Depends(CurrentUser),
) -> list[AuditEntryResponse]:
    """Get permission change audit history."""
    service = PermissionService(db)

    result = await service.get_permission_audit_history(
        user_id=user_id,
        limit=limit,
    )

    return [AuditEntryResponse(**r) for r in result]
