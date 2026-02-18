"""Permission service for intelligent access control."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, DataAsset, Role, User, UserRole
from app.models.asset import AccessLevel
from app.models.audit import AuditAction


class PermissionRequestStatus(str, Enum):
    """Permission request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PermissionService:
    """Service for intelligent permission management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def suggest_permissions_for_asset(
        self,
        asset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Suggest permissions based on asset sensitivity level.

        Args:
            asset_id: Asset ID to analyze

        Returns:
            Permission suggestions based on sensitivity
        """
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        sensitivity_rules = {
            AccessLevel.PUBLIC: {
                "min_role_level": 0,
                "require_approval": False,
                "allowed_operations": ["read"],
                "audit_level": "basic",
                "retention_days": 30,
            },
            AccessLevel.INTERNAL: {
                "min_role_level": 1,
                "require_approval": False,
                "allowed_operations": ["read", "export"],
                "audit_level": "standard",
                "retention_days": 90,
            },
            AccessLevel.RESTRICTED: {
                "min_role_level": 2,
                "require_approval": True,
                "allowed_operations": ["read", "export"],
                "audit_level": "detailed",
                "retention_days": 365,
            },
            AccessLevel.CONFIDENTIAL: {
                "min_role_level": 3,
                "require_approval": True,
                "allowed_operations": ["read"],
                "audit_level": "comprehensive",
                "retention_days": 730,
            },
        }

        rules = sensitivity_rules.get(asset.access_level, sensitivity_rules[AccessLevel.INTERNAL])

        roles_result = await self.db.execute(select(Role))
        all_roles = list(roles_result.scalars())

        suggested_roles = [
            {
                "role_id": str(role.id),
                "role_name": role.name,
                "can_access": (role.level or 0) >= rules["min_role_level"],
                "reason": self._get_role_reason(role, rules["min_role_level"]),
            }
            for role in all_roles
        ]

        return {
            "asset_id": str(asset_id),
            "asset_name": asset.name,
            "access_level": asset.access_level.value,
            "permission_rules": rules,
            "suggested_roles": suggested_roles,
            "recommendations": self._generate_recommendations(asset, rules),
        }

    def _get_role_reason(self, role: Role, min_level: int) -> str:
        """Generate reason for role access decision."""
        role_level = role.level or 0
        if role_level >= min_level:
            return f"Role level ({role_level}) meets minimum requirement ({min_level})"
        return f"Role level ({role_level}) below minimum requirement ({min_level})"

    def _generate_recommendations(
        self,
        asset: DataAsset,
        rules: dict[str, Any],
    ) -> list[str]:
        """Generate permission recommendations."""
        recommendations = []

        if rules["require_approval"]:
            recommendations.append("Enable approval workflow for access requests")

        if rules["audit_level"] in ["detailed", "comprehensive"]:
            recommendations.append("Enable detailed audit logging for all access")

        if asset.access_level == AccessLevel.CONFIDENTIAL:
            recommendations.append("Consider data masking for sensitive fields")
            recommendations.append("Implement time-limited access grants")

        if not asset.is_certified:
            recommendations.append("Consider certifying this asset for governance compliance")

        return recommendations

    async def suggest_permissions_for_user(
        self,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Suggest permissions based on user's role.

        Args:
            user_id: User ID to analyze

        Returns:
            Permission suggestions based on role
        """
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        roles_result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        user_roles = list(roles_result.scalars())

        max_role_level = max((r.level or 0) for r in user_roles) if user_roles else 0

        accessible_assets = []
        assets_result = await self.db.execute(
            select(DataAsset).where(DataAsset.is_active.is_(True))
        )
        all_assets = list(assets_result.scalars())

        level_requirements = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.INTERNAL: 1,
            AccessLevel.RESTRICTED: 2,
            AccessLevel.CONFIDENTIAL: 3,
        }

        for asset in all_assets:
            required_level = level_requirements.get(asset.access_level, 1)
            can_access = max_role_level >= required_level

            accessible_assets.append({
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "access_level": asset.access_level.value,
                "domain": asset.domain,
                "can_access": can_access,
                "requires_approval": asset.access_level in [AccessLevel.RESTRICTED, AccessLevel.CONFIDENTIAL],
            })

        return {
            "user_id": str(user_id),
            "user_email": user.email,
            "roles": [{"id": str(r.id), "name": r.name, "level": r.level} for r in user_roles],
            "max_role_level": max_role_level,
            "accessible_assets": [a for a in accessible_assets if a["can_access"]],
            "restricted_assets": [a for a in accessible_assets if not a["can_access"]],
            "upgrade_suggestions": self._suggest_role_upgrades(user_roles, all_assets),
        }

    def _suggest_role_upgrades(
        self,
        current_roles: list[Role],
        assets: list[DataAsset],
    ) -> list[dict[str, Any]]:
        """Suggest role upgrades based on access needs."""
        suggestions = []

        max_level = max((r.level or 0) for r in current_roles) if current_roles else 0

        restricted_count = sum(1 for a in assets if a.access_level == AccessLevel.RESTRICTED)
        confidential_count = sum(1 for a in assets if a.access_level == AccessLevel.CONFIDENTIAL)

        if max_level < 2 and restricted_count > 0:
            suggestions.append({
                "suggestion": "Request elevated role for restricted data access",
                "reason": f"{restricted_count} restricted assets available",
                "required_level": 2,
            })

        if max_level < 3 and confidential_count > 0:
            suggestions.append({
                "suggestion": "Request admin role for confidential data access",
                "reason": f"{confidential_count} confidential assets available",
                "required_level": 3,
            })

        return suggestions

    async def auto_configure_permissions(
        self,
        user_id: uuid.UUID,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Automatically configure permissions based on user attributes.

        Uses AI to suggest appropriate roles and access based on department,
        job function, and organizational patterns.

        Args:
            user_id: User to configure
            department: Optional department override

        Returns:
            Configuration result with assigned permissions
        """
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        roles_result = await self.db.execute(select(Role))
        all_roles = list(roles_result.scalars())

        assets_result = await self.db.execute(
            select(DataAsset).where(DataAsset.is_active.is_(True))
        )
        all_assets = list(assets_result.scalars())

        user_dept = department or "general"
        user_info = {
            "email": user.email,
            "department": user_dept,
            "is_admin": user.is_superuser,
        }

        roles_info = [{"id": str(r.id), "name": r.name, "level": r.level, "permissions": r.permissions} for r in all_roles]
        assets_info = [
            {
                "id": str(a.id),
                "name": a.name,
                "domain": a.domain,
                "access_level": a.access_level.value,
            }
            for a in all_assets[:50]
        ]

        prompt = f"""Based on the user profile and organizational data, suggest appropriate permissions.

User Profile:
{json.dumps(user_info, indent=2)}

Available Roles:
{json.dumps(roles_info, indent=2)}

Available Data Assets (sample):
{json.dumps(assets_info, indent=2)}

Suggest role assignments and data access permissions following least-privilege principle.

Respond in JSON format:
{{
  "suggested_roles": [
    {{"role_id": "uuid", "reason": "Why this role is appropriate"}}
  ],
  "domain_access": [
    {{"domain": "sales", "access": true, "reason": "Based on department"}}
  ],
  "recommendations": ["Additional recommendation 1"],
  "confidence": 0.85
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security administrator. Suggest appropriate permissions following the principle of least privilege.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            suggestions = json.loads(response.choices[0].message.content or "{}")
        except Exception:
            suggestions = {
                "suggested_roles": [],
                "domain_access": [],
                "recommendations": ["Manual configuration recommended"],
                "confidence": 0.0,
            }

        return {
            "user_id": str(user_id),
            "user_email": user.email,
            "department": user_dept,
            "ai_suggestions": suggestions,
            "current_roles": [{"id": str(r.id), "name": r.name} for r in all_roles if hasattr(user, 'roles') and r in user.roles],
        }

    async def audit_permission_change(
        self,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: str,
        details: dict[str, Any],
    ) -> AuditLog:
        """Record a permission change in the audit log.

        Args:
            user_id: User whose permissions changed
            actor_id: User who made the change
            action: Type of change (grant, revoke, modify)
            details: Change details

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            user_id=actor_id,
            action=AuditAction.PERMISSION_CHANGE,
            resource_type="permission",
            resource_id=str(user_id),
            details={
                "target_user_id": str(user_id),
                "change_type": action,
                **details,
            },
            ip_address="system",
        )

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log

    async def get_permission_audit_history(
        self,
        user_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get permission change audit history.

        Args:
            user_id: Optional filter by user
            limit: Maximum records to return

        Returns:
            List of audit entries
        """
        query = select(AuditLog).where(
            AuditLog.action == AuditAction.PERMISSION_CHANGE
        )

        if user_id:
            query = query.where(AuditLog.resource_id == str(user_id))

        query = query.order_by(AuditLog.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        logs = list(result.scalars())

        return [
            {
                "id": str(log.id),
                "actor_id": str(log.user_id),
                "target_user_id": log.details.get("target_user_id"),
                "change_type": log.details.get("change_type"),
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def check_access_permission(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        operation: str = "read",
    ) -> dict[str, Any]:
        """Check if a user has permission to perform an operation on an asset.

        Args:
            user_id: User requesting access
            asset_id: Asset to access
            operation: Operation type (read, export, write)

        Returns:
            Permission check result
        """
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return {
                "allowed": False,
                "reason": "User not found",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
            }

        if user.is_superuser:
            return {
                "allowed": True,
                "reason": "Superuser has full access",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
            }

        asset_result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = asset_result.scalar_one_or_none()

        if not asset:
            return {
                "allowed": False,
                "reason": "Asset not found",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
            }

        if not asset.is_active:
            return {
                "allowed": False,
                "reason": "Asset is not active",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
            }

        roles_result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        user_roles = list(roles_result.scalars())

        max_role_level = max((r.level or 0) for r in user_roles) if user_roles else 0

        level_requirements = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.INTERNAL: 1,
            AccessLevel.RESTRICTED: 2,
            AccessLevel.CONFIDENTIAL: 3,
        }

        required_level = level_requirements.get(asset.access_level, 1)

        if operation == "export" and asset.access_level == AccessLevel.CONFIDENTIAL:
            return {
                "allowed": False,
                "reason": "Export not allowed for confidential data",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
                "operation": operation,
            }

        if max_role_level >= required_level:
            return {
                "allowed": True,
                "reason": f"User role level ({max_role_level}) meets requirement ({required_level})",
                "user_id": str(user_id),
                "asset_id": str(asset_id),
                "operation": operation,
            }

        return {
            "allowed": False,
            "reason": f"User role level ({max_role_level}) below requirement ({required_level})",
            "user_id": str(user_id),
            "asset_id": str(asset_id),
            "operation": operation,
            "required_level": required_level,
        }
