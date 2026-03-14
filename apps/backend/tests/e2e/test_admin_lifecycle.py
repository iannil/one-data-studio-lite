"""
E2E tests for Super Admin lifecycle.

Lifecycle stages:
1. Register - First time registration
2. Login - Get access token
3. User Management - List users
4. Role Management - Create roles, assign permissions
5. Audit - View audit logs

Coverage: /auth/register, /auth/login, /auth/me, /users, /users/roles, /audit/logs
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models import User


class TestAdminRegistration:
    """Test admin registration lifecycle stage."""

    @pytest.mark.asyncio
    async def test_admin_register_success(self, async_client: AsyncClient):
        """Test successful admin registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"newadmin_{uuid4().hex[:8]}@test.com",
                "password": "SecurePassword123!",
                "full_name": "New Admin User",
                "is_active": True,
            },
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_admin_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration with duplicate email fails."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "password": "SecurePassword123!",
                "full_name": "Duplicate User",
                "is_active": True,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePassword123!",
                "full_name": "Invalid Email User",
                "is_active": True,
            },
        )

        assert response.status_code == 422


class TestAdminLogin:
    """Test admin login lifecycle stage."""

    @pytest.mark.asyncio
    async def test_admin_login_missing_credentials(self, async_client: AsyncClient):
        """Test login with missing credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_admin_login_invalid_password(self, async_client: AsyncClient):
        """Test login with invalid password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "wrong_password",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_success(self, async_client: AsyncClient):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "admin_password_123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestAdminGetCurrentUser:
    """Test getting current admin user."""

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, async_client: AsyncClient):
        """Test getting current user without authentication."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_success(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test getting current user with valid authentication."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=superuser_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["is_superuser"] is True


class TestAdminUserManagement:
    """Test admin user management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, async_client: AsyncClient):
        """Test listing users without authentication."""
        response = await async_client.get("/api/v1/users")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_users_non_superuser(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test listing users with non-superuser fails."""
        response = await async_client.get(
            "/api/v1/users",
            headers=data_engineer_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users_as_superuser(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test listing users as superuser."""
        response = await async_client.get(
            "/api/v1/users",
            headers=superuser_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5


class TestAdminRoleManagement:
    """Test admin role management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_create_role_unauthorized(self, async_client: AsyncClient):
        """Test creating role without authentication."""
        response = await async_client.post(
            "/api/v1/users/roles",
            json={
                "name": "test_role",
                "description": "Test role",
                "permissions": ["read", "write"],
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_role_non_superuser(
        self,
        async_client: AsyncClient,
        data_analyst_headers: dict,
    ):
        """Test creating role with non-superuser fails."""
        response = await async_client.post(
            "/api/v1/users/roles",
            json={
                "name": "test_role",
                "description": "Test role",
                "permissions": ["read", "write"],
            },
            headers=data_analyst_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_role_as_superuser(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test creating role as superuser."""
        response = await async_client.post(
            "/api/v1/users/roles",
            json={
                "name": f"test_role_{uuid4().hex[:8]}",
                "description": "Test role for E2E",
                "permissions": ["sources:read", "sources:write"],
            },
            headers=superuser_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_list_roles(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test listing roles."""
        response = await async_client.get(
            "/api/v1/users/roles",
            headers=superuser_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5


class TestAdminAuditLogs:
    """Test admin audit log viewing lifecycle stage."""

    @pytest.mark.asyncio
    async def test_view_audit_logs_unauthorized(self, async_client: AsyncClient):
        """Test viewing audit logs without authentication."""
        response = await async_client.get("/api/v1/audit/logs")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_view_audit_logs_non_superuser(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test viewing audit logs with non-superuser fails."""
        response = await async_client.get(
            "/api/v1/audit/logs",
            headers=data_engineer_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_view_audit_logs_as_superuser(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test viewing audit logs as superuser."""
        response = await async_client.get(
            "/api/v1/audit/logs",
            headers=superuser_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_view_audit_logs_with_filters(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test viewing audit logs with filters."""
        response = await async_client.get(
            "/api/v1/audit/logs",
            params={
                "resource_type": "user",
                "skip": 0,
                "limit": 50,
            },
            headers=superuser_headers,
        )

        assert response.status_code == 200


class TestAdminLifecycleIntegration:
    """Integration tests for complete admin lifecycle."""

    @pytest.mark.asyncio
    async def test_admin_full_lifecycle(
        self,
        async_client: AsyncClient,
        superuser_headers: dict,
    ):
        """Test complete admin lifecycle: login -> user management -> role management -> audit."""
        me_response = await async_client.get(
            "/api/v1/auth/me",
            headers=superuser_headers,
        )

        users_response = await async_client.get(
            "/api/v1/users",
            headers=superuser_headers,
        )

        roles_response = await async_client.get(
            "/api/v1/users/roles",
            headers=superuser_headers,
        )

        audit_response = await async_client.get(
            "/api/v1/audit/logs",
            headers=superuser_headers,
        )

        assert me_response.status_code == 200
        assert users_response.status_code == 200
        assert roles_response.status_code == 200
        assert audit_response.status_code == 200
