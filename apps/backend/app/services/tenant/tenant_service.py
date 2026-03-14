"""
Tenant Management Service

Handles tenant lifecycle, user management, and isolation.
"""

import hashlib
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

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
from app.models.user import User
from app.services.tenant.quota_service import QuotaService, get_quota_service

logger = logging.getLogger(__name__)


class TenantAlreadyExistsError(Exception):
    """Raised when trying to create a tenant with duplicate slug"""


class TenantNotFoundError(Exception):
    """Raised when tenant is not found"""


class TenantService:
    """
    Tenant Management Service

    Handles tenant creation, updates, user management, and audit logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.quota_service = QuotaService(db)

    def create_tenant(
        self,
        name: str,
        slug: str,
        contact_email: str,
        tier: TenantTier = TenantTier.BASIC,
        contact_name: Optional[str] = None,
        description: Optional[str] = None,
        owner_id: Optional[int] = None,
        trial_days: Optional[int] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Display name
            slug: URL-friendly identifier
            contact_email: Primary contact email
            tier: Subscription tier
            contact_name: Contact person name
            description: Tenant description
            owner_id: User ID to make tenant owner
            trial_days: Days until trial ends (creates trial tenant)
            settings: Additional tenant settings

        Returns:
            Created Tenant instance
        """
        # Check for existing slug
        existing = self.db.query(Tenant).filter(Tenant.slug == slug).first()
        if existing:
            raise TenantAlreadyExistsError(f"Tenant with slug '{slug}' already exists")

        # Determine trial status
        is_trial = trial_days is not None and trial_days > 0
        trial_ends_at = datetime.utcnow() + timedelta(days=trial_days) if is_trial else None
        status = TenantStatus.PENDING if is_trial else TenantStatus.ACTIVE

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            description=description,
            contact_email=contact_email,
            contact_name=contact_name,
            tier=tier,
            status=status,
            is_trial=is_trial,
            trial_ends_at=trial_ends_at,
            settings=settings or {},
        )

        self.db.add(tenant)
        self.db.flush()  # Get tenant ID

        # Create quota
        self.quota_service._create_default_quota(tenant)

        # Create usage record
        self.quota_service._create_default_usage(tenant.id)

        # Add owner if provided
        if owner_id:
            self.add_user(tenant.id, owner_id, "owner", is_primary=True)

        # Log creation
        self._log_audit(
            tenant_id=tenant.id,
            action="create",
            resource_type="tenant",
            resource_id=str(tenant.id),
            user_id=owner_id,
            new_values={
                "name": name,
                "slug": slug,
                "tier": tier.value,
                "is_trial": is_trial,
            },
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Created tenant: {tenant.id} ({slug})")
        return tenant

    def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_user_tenants(self, user_id: int) -> List[Tenant]:
        """Get all tenants for a user"""
        tenant_users = (
            self.db.query(TenantUser)
            .filter(TenantUser.user_id == user_id)
            .filter(TenantUser.invitation_status == "accepted")
            .all()
        )
        tenant_ids = [tu.tenant_id for tu in tenant_users]
        return self.db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()

    def get_user_primary_tenant(self, user_id: int) -> Optional[Tenant]:
        """Get user's primary tenant"""
        tenant_user = (
            self.db.query(TenantUser)
            .filter(TenantUser.user_id == user_id)
            .filter(TenantUser.is_primary == True)
            .first()
        )
        if tenant_user:
            return self.db.query(Tenant).filter(Tenant.id == tenant_user.tenant_id).first()
        return None

    def update_tenant(
        self,
        tenant_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        billing_email: Optional[str] = None,
        billing_address: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """Update tenant information"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        old_values = {
            "name": tenant.name,
            "description": tenant.description,
            "contact_email": tenant.contact_email,
        }

        if name is not None:
            tenant.name = name
        if description is not None:
            tenant.description = description
        if contact_email is not None:
            tenant.contact_email = contact_email
        if contact_name is not None:
            tenant.contact_name = contact_name
        if contact_phone is not None:
            tenant.contact_phone = contact_phone
        if billing_email is not None:
            tenant.billing_email = billing_email
        if billing_address is not None:
            tenant.billing_address = billing_address
        if settings is not None:
            tenant.settings = {**(tenant.settings or {}), **settings}

        tenant.updated_at = datetime.utcnow()

        new_values = {
            "name": tenant.name,
            "description": tenant.description,
            "contact_email": tenant.contact_email,
        }

        self._log_audit(
            tenant_id=tenant_id,
            action="update",
            resource_type="tenant",
            resource_id=str(tenant_id),
            old_values=old_values,
            new_values=new_values,
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Updated tenant: {tenant_id}")
        return tenant

    def change_tier(self, tenant_id: int, new_tier: TenantTier) -> Tenant:
        """Change tenant subscription tier"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        old_tier = tenant.tier
        tenant.tier = new_tier
        tenant.updated_at = datetime.utcnow()

        # Update quota
        self.quota_service.update_tier(tenant_id, new_tier)

        self._log_audit(
            tenant_id=tenant_id,
            action="change_tier",
            resource_type="tenant",
            resource_id=str(tenant_id),
            old_values={"tier": old_tier.value},
            new_values={"tier": new_tier.value},
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Changed tenant {tenant_id} tier from {old_tier.value} to {new_tier.value}")
        return tenant

    def suspend_tenant(self, tenant_id: int, reason: Optional[str] = None) -> Tenant:
        """Suspend a tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="suspend",
            resource_type="tenant",
            resource_id=str(tenant_id),
            new_values={"reason": reason or "Not specified"},
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Suspended tenant: {tenant_id} (reason: {reason})")
        return tenant

    def activate_tenant(self, tenant_id: int) -> Tenant:
        """Activate a suspended tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        tenant.status = TenantStatus.ACTIVE
        tenant.suspended_at = None
        tenant.updated_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="activate",
            resource_type="tenant",
            resource_id=str(tenant_id),
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Activated tenant: {tenant_id}")
        return tenant

    def terminate_tenant(self, tenant_id: int) -> Tenant:
        """Terminate a tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        tenant.status = TenantStatus.TERMINATED
        tenant.terminated_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="terminate",
            resource_type="tenant",
            resource_id=str(tenant_id),
        )

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"Terminated tenant: {tenant_id}")
        return tenant

    def add_user(
        self,
        tenant_id: int,
        user_id: int,
        role: str = "member",
        is_primary: bool = False,
        invited_by: Optional[int] = None,
    ) -> TenantUser:
        """
        Add a user to a tenant.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            role: Role within tenant (owner, admin, member, viewer)
            is_primary: Whether this is the user's primary tenant
            invited_by: User ID who sent the invitation

        Returns:
            TenantUser instance
        """
        # Check if already a member
        existing = (
            self.db.query(TenantUser)
            .filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id,
                )
            )
            .first()
        )
        if existing:
            existing.role = role
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing

        # If setting as primary, clear other primary
        if is_primary:
            self.db.query(TenantUser).filter(
                and_(
                    TenantUser.user_id == user_id,
                    TenantUser.is_primary == True,
                )
            ).update({"is_primary": False})

        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            is_primary=is_primary,
            invited_by=invited_by,
            invitation_status="accepted",
            joined_at=datetime.utcnow(),
        )

        self.db.add(tenant_user)

        # Update user count
        self.quota_service.allocate_resource(tenant_id, "users", 1)

        self._log_audit(
            tenant_id=tenant_id,
            action="add_user",
            resource_type="tenant_user",
            resource_id=str(user_id),
            user_id=invited_by,
            new_values={"role": role, "is_primary": is_primary},
        )

        self.db.commit()
        self.db.refresh(tenant_user)

        logger.info(f"Added user {user_id} to tenant {tenant_id} as {role}")
        return tenant_user

    def remove_user(self, tenant_id: int, user_id: int) -> bool:
        """Remove a user from a tenant"""
        tenant_user = (
            self.db.query(TenantUser)
            .filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id,
                )
            )
            .first()
        )

        if not tenant_user:
            return False

        # Don't allow removing the last owner
        owner_count = (
            self.db.query(TenantUser)
            .filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.role == "owner",
                )
            )
            .count()
        )
        if tenant_user.role == "owner" and owner_count <= 1:
            raise ValueError("Cannot remove the last owner from a tenant")

        self.db.delete(tenant_user)

        # Update user count
        self.quota_service.release_resource(tenant_id, "users", 1)

        self._log_audit(
            tenant_id=tenant_id,
            action="remove_user",
            resource_type="tenant_user",
            resource_id=str(user_id),
        )

        self.db.commit()

        logger.info(f"Removed user {user_id} from tenant {tenant_id}")
        return True

    def update_user_role(self, tenant_id: int, user_id: int, new_role: str) -> TenantUser:
        """Update user role in tenant"""
        tenant_user = (
            self.db.query(TenantUser)
            .filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id,
                )
            )
            .first()
        )

        if not tenant_user:
            raise ValueError(f"User {user_id} is not a member of tenant {tenant_id}")

        old_role = tenant_user.role
        tenant_user.role = new_role
        tenant_user.updated_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="update_user_role",
            resource_type="tenant_user",
            resource_id=str(user_id),
            old_values={"role": old_role},
            new_values={"role": new_role},
        )

        self.db.commit()
        self.db.refresh(tenant_user)

        logger.info(f"Updated user {user_id} role in tenant {tenant_id} to {new_role}")
        return tenant_user

    def get_tenant_users(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Get all users in a tenant with their roles"""
        tenant_users = (
            self.db.query(TenantUser)
            .filter(TenantUser.tenant_id == tenant_id)
            .filter(TenantUser.invitation_status == "accepted")
            .all()
        )

        result = []
        for tu in tenant_users:
            user = self.db.query(User).filter(User.id == tu.user_id).first()
            if user:
                result.append({
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": tu.role,
                    "is_primary": tu.is_primary,
                    "joined_at": tu.joined_at.isoformat() if tu.joined_at else None,
                    "invited_by": tu.invited_by,
                })

        return result

    def invite_user(
        self,
        tenant_id: int,
        email: str,
        role: str = "member",
        invited_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Invite a user to join a tenant.

        Returns:
            Dictionary with invitation token and details
        """
        # Generate invitation token
        token = str(uuid4())

        # Store in settings for now (in production, use separate table)
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        invitations = tenant.settings.get("invitations", {})
        invitations[token] = {
            "email": email,
            "role": role,
            "invited_by": invited_by,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }
        tenant.settings["invitations"] = invitations
        tenant.updated_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="invite_user",
            resource_type="invitation",
            resource_id=token,
            user_id=invited_by,
            new_values={"email": email, "role": role},
        )

        self.db.commit()

        logger.info(f"Created invitation for {email} to join tenant {tenant_id}")
        return {
            "token": token,
            "email": email,
            "role": role,
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
        }

    def accept_invitation(self, token: str, user_id: int) -> Optional[TenantUser]:
        """Accept a tenant invitation"""
        # Find tenant with this invitation
        tenants = self.db.query(Tenant).all()
        invited_tenant = None
        invitation_data = None

        for tenant in tenants:
            invitations = tenant.settings.get("invitations", {})
            if token in invitations:
                invited_tenant = tenant
                invitation_data = invitations[token]
                break

        if not invited_tenant or not invitation_data:
            raise ValueError("Invalid or expired invitation")

        # Check expiration
        expires_at = datetime.fromisoformat(invitation_data["expires_at"])
        if datetime.utcnow() > expires_at:
            raise ValueError("Invitation has expired")

        # Add user to tenant
        tenant_user = self.add_user(
            tenant_id=invited_tenant.id,
            user_id=user_id,
            role=invitation_data["role"],
            invited_by=invitation_data.get("invited_by"),
        )

        # Remove invitation
        del invited_tenant.settings["invitations"][token]
        self.db.commit()

        logger.info(f"User {user_id} accepted invitation to tenant {invited_tenant.id}")
        return tenant_user

    def create_api_key(
        self,
        tenant_id: int,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> TenantApiKey:
        """
        Create an API key for a tenant.

        Returns:
            TenantApiKey instance (key is only shown once)
        """
        import secrets

        # Generate secure key
        key = f"odsk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_prefix = key[:8]

        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None

        api_key = TenantApiKey(
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes or [],
            expires_at=expires_at,
            created_by=created_by,
        )

        self.db.add(api_key)

        self._log_audit(
            tenant_id=tenant_id,
            action="create_api_key",
            resource_type="api_key",
            resource_id=key_prefix,
            user_id=created_by,
            new_values={"name": name, "scopes": scopes},
        )

        self.db.commit()
        self.db.refresh(api_key)

        logger.info(f"Created API key {key_prefix} for tenant {tenant_id}")
        return api_key

    def revoke_api_key(self, tenant_id: int, key_id: int) -> bool:
        """Revoke an API key"""
        api_key = (
            self.db.query(TenantApiKey)
            .filter(
                and_(
                    TenantApiKey.id == key_id,
                    TenantApiKey.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not api_key:
            return False

        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()

        self._log_audit(
            tenant_id=tenant_id,
            action="revoke_api_key",
            resource_type="api_key",
            resource_id=api_key.key_prefix,
        )

        self.db.commit()

        logger.info(f"Revoked API key {api_key.key_prefix} for tenant {tenant_id}")
        return True

    def get_api_keys(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Get all API keys for a tenant"""
        api_keys = (
            self.db.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
            .all()
        )

        return [
            {
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "scopes": key.scopes,
                "is_active": key.is_active,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "usage_count": key.usage_count,
                "created_at": key.created_at.isoformat(),
            }
            for key in api_keys
        ]

    def check_trial_expiration(self) -> List[Tenant]:
        """Check and expire trial tenants"""
        now = datetime.utcnow()
        expiring_trials = (
            self.db.query(Tenant)
            .filter(Tenant.is_trial == True)
            .filter(Tenant.trial_ends_at <= now)
            .filter(Tenant.status == TenantStatus.ACTIVE)
            .all()
        )

        for tenant in expiring_trials:
            tenant.status = TenantStatus.SUSPENDED
            tenant.suspended_at = now
            logger.info(f"Suspended expired trial tenant: {tenant.id}")

        self.db.commit()
        return expiring_trials

    def _log_audit(
        self,
        tenant_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit entry"""
        log = TenantAuditLog(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )
        self.db.add(log)


def get_tenant_service(db: Session) -> TenantService:
    """Get tenant service instance"""
    return TenantService(db)
