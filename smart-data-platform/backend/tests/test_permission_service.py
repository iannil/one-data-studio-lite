"""Tests for permission service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import AuditLog, DataAsset, Role, User, UserRole
from app.models.asset import AccessLevel, AssetType
from app.models.audit import AuditAction
from app.services.permission_service import PermissionService


class TestPermissionService:
    """Test suite for PermissionService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a PermissionService instance with mock database."""
        return PermissionService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Create a sample User for testing."""
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.is_superuser = False
        return user

    @pytest.fixture
    def sample_role(self):
        """Create a sample Role for testing."""
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.name = "analyst"
        role.level = 2
        role.permissions = ["read", "export"]
        return role

    @pytest.fixture
    def sample_asset(self):
        """Create a sample DataAsset for testing."""
        asset = MagicMock(spec=DataAsset)
        asset.id = uuid.uuid4()
        asset.name = "Test Asset"
        asset.access_level = AccessLevel.INTERNAL
        asset.domain = "sales"
        asset.is_active = True
        asset.is_certified = False
        return asset


class TestSuggestPermissionsForAsset(TestPermissionService):
    """Test asset permission suggestions."""

    @pytest.mark.asyncio
    async def test_suggest_public_asset(self, service, mock_db, sample_asset, sample_role):
        """Test suggestions for public asset."""
        sample_asset.access_level = AccessLevel.PUBLIC

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_db.execute.side_effect = [mock_asset_result, mock_roles_result]

        result = await service.suggest_permissions_for_asset(sample_asset.id)

        assert result["access_level"] == "public"
        assert result["permission_rules"]["require_approval"] is False
        assert len(result["suggested_roles"]) == 1

    @pytest.mark.asyncio
    async def test_suggest_confidential_asset(self, service, mock_db, sample_asset, sample_role):
        """Test suggestions for confidential asset."""
        sample_asset.access_level = AccessLevel.CONFIDENTIAL

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_db.execute.side_effect = [mock_asset_result, mock_roles_result]

        result = await service.suggest_permissions_for_asset(sample_asset.id)

        assert result["access_level"] == "confidential"
        assert result["permission_rules"]["require_approval"] is True
        assert result["permission_rules"]["min_role_level"] == 3
        assert "data masking" in result["recommendations"][0].lower() or len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_suggest_asset_not_found(self, service, mock_db):
        """Test suggestions for nonexistent asset."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Asset not found"):
            await service.suggest_permissions_for_asset(uuid.uuid4())


class TestSuggestPermissionsForUser(TestPermissionService):
    """Test user permission suggestions."""

    @pytest.mark.asyncio
    async def test_suggest_user_with_roles(
        self, service, mock_db, sample_user, sample_role, sample_asset
    ):
        """Test suggestions for user with roles."""
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value = [sample_asset]

        mock_db.execute.side_effect = [
            mock_user_result,
            mock_roles_result,
            mock_assets_result,
        ]

        result = await service.suggest_permissions_for_user(sample_user.id)

        assert result["user_id"] == str(sample_user.id)
        assert result["max_role_level"] == 2
        assert len(result["roles"]) == 1

    @pytest.mark.asyncio
    async def test_suggest_user_without_roles(self, service, mock_db, sample_user, sample_asset):
        """Test suggestions for user without roles."""
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = []

        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value = [sample_asset]

        mock_db.execute.side_effect = [
            mock_user_result,
            mock_roles_result,
            mock_assets_result,
        ]

        result = await service.suggest_permissions_for_user(sample_user.id)

        assert result["max_role_level"] == 0
        assert len(result["roles"]) == 0

    @pytest.mark.asyncio
    async def test_suggest_user_not_found(self, service, mock_db):
        """Test suggestions for nonexistent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="User not found"):
            await service.suggest_permissions_for_user(uuid.uuid4())


class TestCheckAccessPermission(TestPermissionService):
    """Test access permission checking."""

    @pytest.mark.asyncio
    async def test_check_superuser_access(self, service, mock_db, sample_user, sample_asset):
        """Test superuser has full access."""
        sample_user.is_superuser = True

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_user_result

        result = await service.check_access_permission(
            user_id=sample_user.id,
            asset_id=sample_asset.id,
        )

        assert result["allowed"] is True
        assert "Superuser" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_user_not_found(self, service, mock_db, sample_asset):
        """Test access check for nonexistent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.check_access_permission(
            user_id=uuid.uuid4(),
            asset_id=sample_asset.id,
        )

        assert result["allowed"] is False
        assert "User not found" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_asset_not_found(self, service, mock_db, sample_user):
        """Test access check for nonexistent asset."""
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_user_result, mock_asset_result]

        result = await service.check_access_permission(
            user_id=sample_user.id,
            asset_id=uuid.uuid4(),
        )

        assert result["allowed"] is False
        assert "Asset not found" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_sufficient_role_level(
        self, service, mock_db, sample_user, sample_asset, sample_role
    ):
        """Test access allowed with sufficient role level."""
        sample_asset.access_level = AccessLevel.INTERNAL
        sample_role.level = 2

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_db.execute.side_effect = [
            mock_user_result,
            mock_asset_result,
            mock_roles_result,
        ]

        result = await service.check_access_permission(
            user_id=sample_user.id,
            asset_id=sample_asset.id,
        )

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_insufficient_role_level(
        self, service, mock_db, sample_user, sample_asset, sample_role
    ):
        """Test access denied with insufficient role level."""
        sample_asset.access_level = AccessLevel.CONFIDENTIAL
        sample_role.level = 1

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_db.execute.side_effect = [
            mock_user_result,
            mock_asset_result,
            mock_roles_result,
        ]

        result = await service.check_access_permission(
            user_id=sample_user.id,
            asset_id=sample_asset.id,
        )

        assert result["allowed"] is False
        assert "below requirement" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_export_confidential_denied(
        self, service, mock_db, sample_user, sample_asset, sample_role
    ):
        """Test export denied for confidential data."""
        sample_asset.access_level = AccessLevel.CONFIDENTIAL
        sample_role.level = 3

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = [sample_role]

        mock_db.execute.side_effect = [
            mock_user_result,
            mock_asset_result,
            mock_roles_result,
        ]

        result = await service.check_access_permission(
            user_id=sample_user.id,
            asset_id=sample_asset.id,
            operation="export",
        )

        assert result["allowed"] is False
        assert "Export not allowed" in result["reason"]


class TestAuditPermissionChange(TestPermissionService):
    """Test permission change auditing."""

    @pytest.mark.asyncio
    async def test_audit_permission_change(self, service, mock_db):
        """Test recording permission change in audit log."""
        user_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        await service.audit_permission_change(
            user_id=user_id,
            actor_id=actor_id,
            action="grant",
            details={"role": "analyst"},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_permission_audit_history(self, service, mock_db):
        """Test getting permission audit history."""
        log1 = MagicMock(spec=AuditLog)
        log1.id = uuid.uuid4()
        log1.user_id = uuid.uuid4()
        log1.action = AuditAction.PERMISSION_CHANGE
        log1.details = {"target_user_id": str(uuid.uuid4()), "change_type": "grant"}
        log1.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value = [log1]
        mock_db.execute.return_value = mock_result

        result = await service.get_permission_audit_history(limit=100)

        assert len(result) == 1
        assert result[0]["change_type"] == "grant"


class TestRoleReasonGeneration(TestPermissionService):
    """Test role reason generation."""

    def test_get_role_reason_meets_requirement(self, service, sample_role):
        """Test reason when role meets requirement."""
        sample_role.level = 3

        reason = service._get_role_reason(sample_role, min_level=2)

        assert "meets minimum requirement" in reason

    def test_get_role_reason_below_requirement(self, service, sample_role):
        """Test reason when role is below requirement."""
        sample_role.level = 1

        reason = service._get_role_reason(sample_role, min_level=2)

        assert "below minimum requirement" in reason


class TestRecommendationGeneration(TestPermissionService):
    """Test recommendation generation."""

    def test_generate_recommendations_approval_required(self, service, sample_asset):
        """Test recommendations include approval workflow."""
        rules = {"require_approval": True, "audit_level": "standard"}

        recommendations = service._generate_recommendations(sample_asset, rules)

        assert any("approval" in r.lower() for r in recommendations)

    def test_generate_recommendations_detailed_audit(self, service, sample_asset):
        """Test recommendations include detailed audit for sensitive data."""
        rules = {"require_approval": False, "audit_level": "detailed"}

        recommendations = service._generate_recommendations(sample_asset, rules)

        assert any("audit" in r.lower() for r in recommendations)

    def test_generate_recommendations_confidential(self, service, sample_asset):
        """Test recommendations for confidential assets."""
        sample_asset.access_level = AccessLevel.CONFIDENTIAL
        rules = {"require_approval": True, "audit_level": "comprehensive"}

        recommendations = service._generate_recommendations(sample_asset, rules)

        assert any("masking" in r.lower() for r in recommendations)
