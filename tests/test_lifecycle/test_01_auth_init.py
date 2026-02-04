"""Test Authentication Initialization - Phase 01

Tests authentication system initialization and configuration.
Tests JWT token generation, validation, and lifecycle.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestAuthInitLifecycle:
    """Test authentication initialization lifecycle"""

    async def test_auth_01_system_configured(self, portal_client: AsyncClient):
        """Verify authentication system is properly configured"""
        # Check JWT settings are loaded
        from services.common.auth import JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_SECRET

        assert JWT_SECRET is not None
        assert JWT_ALGORITHM == "HS256"
        assert JWT_EXPIRE_HOURS > 0

    async def test_auth_02_token_generation(self, portal_client: AsyncClient):
        """Test JWT token generation for different user roles"""
        from services.common.auth import create_token

        # Test token generation for different roles
        roles = ["super_admin", "admin", "data_scientist", "analyst", "viewer", "service_account"]

        for role in roles:
            token = create_token(
                user_id=f"test_{role}",
                username=f"test_{role}",
                role=role
            )
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 50  # JWT tokens are typically long

    async def test_auth_03_token_validation_valid(self, portal_client: AsyncClient):
        """Test valid token validation"""
        from services.common.auth import create_token, verify_token

        token = create_token(
            user_id="test_user",
            username="testuser",
            role="analyst"
        )

        payload = verify_token(token)
        assert payload is not None
        assert payload.user_id == "test_user"
        assert payload.username == "testuser"
        assert payload.role == "analyst"

    async def test_auth_04_token_validation_invalid(self, portal_client: AsyncClient):
        """Test invalid token validation fails"""
        from fastapi.exceptions import HTTPException

        from services.common.auth import verify_token

        # Invalid token raises HTTPException
        try:
            verify_token("invalid_token_string")
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

        # Malformed token raises HTTPException
        try:
            verify_token("not.a.jwt")
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

    async def test_auth_05_token_expiration(self, portal_client: AsyncClient):
        """Test token expiration handling"""
        from fastapi.exceptions import HTTPException

        from services.common.auth import create_token, verify_token

        # Create expired token
        expired_token = create_token(
            user_id="test_user",
            username="testuser",
            role="analyst",
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Verify expired token raises HTTPException
        try:
            verify_token(expired_token)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 401
            assert "已过期" in e.detail or "expired" in e.detail.lower()

    async def test_auth_06_token_claims(self, portal_client: AsyncClient):
        """Test token contains correct claims"""
        import jwt

        from services.common.auth import create_token

        token = create_token(
            user_id="test_user",
            username="testuser",
            role="analyst"
        )

        # Decode and verify claims
        from services.common.auth import JWT_ALGORITHM, JWT_SECRET
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert decoded["sub"] == "test_user"
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "analyst"
        assert "exp" in decoded
        assert "iat" in decoded

    async def test_auth_07_default_expiry(self, portal_client: AsyncClient):
        """Test default token expiration time"""
        import jwt

        from services.common.auth import JWT_EXPIRE_HOURS, create_token

        token = create_token(
            user_id="test_user",
            username="testuser",
            role="analyst"
        )

        from services.common.auth import JWT_ALGORITHM, JWT_SECRET
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Check expiration is approximately correct (within 60 seconds)
        exp = datetime.fromtimestamp(decoded["exp"])
        iat = datetime.fromtimestamp(decoded["iat"])
        diff = (exp - iat).total_seconds()

        expected_seconds = JWT_EXPIRE_HOURS * 3600
        assert abs(diff - expected_seconds) < 60

    async def test_auth_08_custom_expiry(self, portal_client: AsyncClient):
        """Test custom token expiration time"""
        import jwt

        from services.common.auth import create_token

        custom_hours = 48
        token = create_token(
            user_id="test_user",
            username="testuser",
            role="analyst",
            expires_delta=timedelta(hours=custom_hours)
        )

        from services.common.auth import JWT_ALGORITHM, JWT_SECRET
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        exp = datetime.fromtimestamp(decoded["exp"])
        iat = datetime.fromtimestamp(decoded["iat"])
        diff = (exp - iat).total_seconds()

        expected_seconds = custom_hours * 3600
        assert abs(diff - expected_seconds) < 60


@pytest.mark.p1
class TestAuthPermissions:
    """Test permission boundaries in authentication"""

    async def test_auth_09_role_hierarchy(self, portal_client: AsyncClient):
        """Test role hierarchy is properly defined"""
        from services.portal.routers.roles import PREDEFINED_ROLES

        # Verify super_admin has all permissions
        super_admin_perms = set(PREDEFINED_ROLES["super_admin"]["permissions"])

        # Verify admin has fewer permissions than super_admin
        admin_perms = set(PREDEFINED_ROLES["admin"]["permissions"])
        assert admin_perms.issubset(super_admin_perms)
        assert len(admin_perms) < len(super_admin_perms)

    async def test_auth_10_permission_categories(self, portal_client: AsyncClient):
        """Test permissions are properly categorized"""
        from services.portal.routers.roles import PREDEFINED_PERMISSIONS

        # Check permission categories
        categories = set()
        for code in PREDEFINED_PERMISSIONS.keys():
            if ":" in code:
                categories.add(code.split(":")[0])

        # Expected categories
        expected_categories = {"data", "pipeline", "system", "metadata", "sensitive", "audit", "quality", "service"}
        assert categories == expected_categories
