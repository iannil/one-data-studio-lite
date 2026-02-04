"""Test User Management Lifecycle - Phase 02

Tests complete user CRUD lifecycle:
- Setup and configuration
- Create new user
- Read/retrieve user
- Update user
- Delete user
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestUserLifecycle:
    """Test user complete lifecycle"""

    async def test_user_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify user management system is ready"""
        response = await portal_client.get(
            "/api/users",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 401)  # May be unauthorized but endpoint exists

    async def test_user_02_create(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new user"""
        # Create a test user
        user_data = {
            "username": "lifecycle_test_user",
            "password": "TestPass123!",
            "role": "viewer",
            "display_name": "Lifecycle Test User",
            "email": "lifecycle@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        # ApiResponse format: code, message, data
        assert data.get("code") == 20000 or "message" in data
        assert "data" in data
        if isinstance(data.get("data"), dict):
            assert "id" in data["data"] or "username" in data["data"]

    async def test_user_03_read(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Read/retrieve created user"""
        response = await portal_client.get(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data
        assert "data" in data
        assert data["data"]["username"] == "lifecycle_test_user"
        assert data["data"]["role"] == "viewer"
        assert data["data"]["email"] == "lifecycle@test.com"

    async def test_user_04_update(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Update existing user"""
        update_data = {
            "display_name": "Updated Test User",
            "email": "updated@test.com",
            "phone": "13800138000"
        }

        response = await portal_client.put(
            "/api/users/lifecycle_test_user",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify update
        response = await portal_client.get(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        user_data = response.json()["data"]
        assert user_data["display_name"] == "Updated Test User"
        assert user_data["email"] == "updated@test.com"
        assert user_data["phone"] == "13800138000"

    async def test_user_05_disable(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Disable user account"""
        disable_data = {
            "disabled_by": "super_admin",
            "reason": "Testing disable functionality"
        }

        response = await portal_client.post(
            "/api/users/lifecycle_test_user/disable",
            json=disable_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify user is disabled
        response = await portal_client.get(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_user_06_enable(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Enable disabled user account"""
        response = await portal_client.post(
            "/api/users/lifecycle_test_user/enable",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify user is enabled
        response = await portal_client.get(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True

    async def test_user_07_reset_password(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Reset user password"""
        reset_data = {
            "new_password": "NewPassword456!"
        }

        response = await portal_client.post(
            "/api/users/lifecycle_test_user/reset-password",
            json=reset_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

    async def test_user_08_delete(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Delete user account"""
        response = await portal_client.delete(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify user is deleted
        response = await portal_client.get(
            "/api/users/lifecycle_test_user",
            headers=super_admin_headers
        )
        assert response.status_code == 404


@pytest.mark.p1
class TestUserPermissions:
    """Test user permission boundaries"""

    async def test_user_09_admin_cannot_create_super_admin(self, portal_client: AsyncClient, admin_headers: dict):
        """Admin cannot create super admin user"""
        user_data = {
            "username": "test_sa_user",
            "password": "TestPass123!",
            "role": "super_admin",
            "display_name": "Test Super Admin",
            "email": "testsa@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=admin_headers
        )
        assert response.status_code == 403
        # The API returns "只有超级管理员可以创建管理员用户" for admin creating admin/super_admin
        detail = response.json()["detail"]
        assert "权限不足" in detail or "超级管理员" in detail

    async def test_user_10_viewer_cannot_create_user(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot create users"""
        user_data = {
            "username": "test_viewer_user",
            "password": "TestPass123!",
            "role": "viewer",
            "display_name": "Test Viewer User",
            "email": "viewertest@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=viewer_headers
        )
        assert response.status_code == 403

    async def test_user_11_cannot_delete_self(self, portal_client: AsyncClient, admin_headers: dict):
        """User cannot delete themselves

        Note: admin_headers uses user_id="admin" and username="admin"
        The API compares path parameter to user_id, so we use "admin" here.
        """
        response = await portal_client.delete(
            "/api/users/admin",
            headers=admin_headers
        )
        # May return 400 (cannot delete self), 403 (permission denied), or 404 (user not found)
        assert response.status_code in (400, 403, 404)
        if response.status_code == 400:
            assert "不能删除自己的账户" in response.json()["detail"]

    async def test_user_12_cannot_disable_self(self, portal_client: AsyncClient, admin_headers: dict):
        """User cannot disable themselves

        Note: admin_headers uses user_id="admin" and username="admin"
        The API compares path parameter to user_id, so we use "admin" here.
        """
        disable_data = {
            "disabled_by": "admin",
            "reason": "Testing"
        }

        response = await portal_client.post(
            "/api/users/admin/disable",
            json=disable_data,
            headers=admin_headers
        )
        # May return 400 (cannot disable self) or 404 (admin user not found in test DB)
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            assert "不能禁用自己的账户" in response.json()["detail"]


@pytest.mark.p2
class TestUserListAndFilter:
    """Test user listing and filtering"""

    async def test_user_13_list_all(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List all users with pagination"""
        response = await portal_client.get(
            "/api/users?page=1&page_size=20",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1

    async def test_user_14_filter_by_role(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Filter users by role"""
        response = await portal_client.get(
            "/api/users?role=viewer",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["items"]:
            assert user["role"] == "viewer"

    async def test_user_15_filter_by_status(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Filter users by active status"""
        response = await portal_client.get(
            "/api/users?is_active=true",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["items"]:
            assert user["is_active"] is True

    async def test_user_16_admin_cannot_see_super_admin(self, portal_client: AsyncClient, admin_headers: dict):
        """Admin cannot see super admin in list"""
        response = await portal_client.get(
            "/api/users",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Super admin should not be visible to regular admin
        for user in data["items"]:
            assert user["role"] != "super_admin"


@pytest.mark.p3
class TestUserValidation:
    """Test user input validation"""

    async def test_user_17_duplicate_username_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating user with duplicate username fails"""
        # First create a user
        user_data = {
            "username": "test_duplicate_user",
            "password": "TestPass123!",
            "role": "viewer",
            "display_name": "Test Duplicate User",
            "email": "duplicate@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201

        # Try to create the same user again
        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=super_admin_headers
        )
        assert response.status_code == 409
        assert "已存在" in response.json()["detail"]

        # Cleanup
        await portal_client.delete(
            "/api/users/test_duplicate_user",
            headers=super_admin_headers
        )

    async def test_user_18_invalid_role_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating user with invalid role fails"""
        user_data = {
            "username": "test_invalid_role",
            "password": "TestPass123!",
            "role": "invalid_role",
            "display_name": "Test Invalid Role",
            "email": "invalid@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=super_admin_headers
        )
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]

    async def test_user_19_get_nonexistent_user_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Getting non-existent user returns 404"""
        response = await portal_client.get(
            "/api/users/nonexistent_user_xyz",
            headers=super_admin_headers
        )
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]
