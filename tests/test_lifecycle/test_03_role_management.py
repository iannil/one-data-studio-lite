"""Test Role Management Lifecycle - Phase 03

Tests complete role management lifecycle:
- Setup and configuration
- Create new role
- Read/retrieve role
- Update role
- Delete role
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestRoleLifecycle:
    """Test role complete lifecycle"""

    async def test_role_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify role management system is ready"""
        response = await portal_client.get(
            "/api/roles",
            headers=super_admin_headers
        )
        assert response.status_code == 200

    async def test_role_02_list_predefined(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List all predefined roles"""
        response = await portal_client.get(
            "/api/roles",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 8  # At least 8 predefined roles

        # Check for expected roles
        role_codes = {role["role_code"] for role in data["items"]}
        expected_roles = {"super_admin", "admin", "data_scientist", "analyst", "viewer", "service_account", "engineer", "steward"}
        assert expected_roles.issubset(role_codes)

    async def test_role_03_get_predefined_role(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get details of predefined role"""
        response = await portal_client.get(
            "/api/roles/viewer",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "data" in data
        role = data["data"]
        assert role["role_code"] == "viewer"
        assert role["role_name"] == "查看者"
        assert role["is_system"] is True
        assert isinstance(role["permissions"], list)

    async def test_role_04_create_custom_role(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new custom role"""
        role_data = {
            "role_code": "custom_analyst",
            "role_name": "自定义分析师",
            "description": "具有有限权限的自定义分析师角色",
            "permissions": ["data:read", "metadata:read"]
        }

        response = await portal_client.post(
            "/api/roles",
            json=role_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20001 or "data" in data
        assert data["data"]["role_code"] == "custom_analyst"

    async def test_role_05_get_custom_role(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get details of custom role"""
        response = await portal_client.get(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        role = data["data"]
        assert role["role_code"] == "custom_analyst"
        assert role["role_name"] == "自定义分析师"
        assert role["is_system"] is False
        assert set(role["permissions"]) == {"data:read", "metadata:read"}

    async def test_role_06_update_role_permissions(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Update role permissions"""
        update_data = {
            "add_permissions": ["pipeline:read"],
            "remove_permissions": []
        }

        response = await portal_client.put(
            "/api/roles/custom_analyst",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify permissions were added
        response = await portal_client.get(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        role = response.json()["data"]
        assert "pipeline:read" in role["permissions"]

    async def test_role_07_update_role_info(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Update role basic information"""
        update_data = {
            "role_name": "高级自定义分析师",
            "description": "更新后的角色描述"
        }

        response = await portal_client.put(
            "/api/roles/custom_analyst",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200

        # Verify update
        response = await portal_client.get(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        role = response.json()["data"]
        assert role["role_name"] == "高级自定义分析师"
        assert role["description"] == "更新后的角色描述"

    async def test_role_08_remove_permissions(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Remove permissions from role"""
        update_data = {
            "add_permissions": [],
            "remove_permissions": ["pipeline:read"]
        }

        response = await portal_client.put(
            "/api/roles/custom_analyst",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code == 200

        # Verify permission was removed
        response = await portal_client.get(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        role = response.json()["data"]
        assert "pipeline:read" not in role["permissions"]

    async def test_role_09_delete_custom_role(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Delete custom role"""
        response = await portal_client.delete(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify role is deleted
        response = await portal_client.get(
            "/api/roles/custom_analyst",
            headers=super_admin_headers
        )
        assert response.status_code == 404


@pytest.mark.p1
class TestRolePermissions:
    """Test role permission boundaries"""

    async def test_role_10_admin_cannot_create_role(self, portal_client: AsyncClient, admin_headers: dict):
        """Admin cannot create roles (only super_admin)"""
        role_data = {
            "role_code": "test_admin_role",
            "role_name": "Test Role",
            "description": "Test",
            "permissions": ["data:read"]
        }

        response = await portal_client.post(
            "/api/roles",
            json=role_data,
            headers=admin_headers
        )
        assert response.status_code == 403
        assert "权限不足" in response.json()["detail"]

    async def test_role_11_admin_cannot_delete_role(self, portal_client: AsyncClient, admin_headers: dict):
        """Admin cannot delete roles (only super_admin)"""
        # First create a custom role as super_admin

        # Use super admin headers instead
        # This test just verifies admin cannot delete

        response = await portal_client.delete(
            "/api/roles/viewer",  # Try to delete predefined role
            headers=admin_headers
        )
        assert response.status_code == 403

    async def test_role_12_system_role_cannot_be_deleted(self, portal_client: AsyncClient, super_admin_headers: dict):
        """System predefined roles cannot be deleted"""
        response = await portal_client.delete(
            "/api/roles/viewer",
            headers=super_admin_headers
        )
        assert response.status_code == 400
        assert "系统内置角色不能删除" in response.json()["detail"]

    async def test_role_13_system_role_cannot_be_modified(self, portal_client: AsyncClient, super_admin_headers: dict):
        """System predefined roles cannot be modified"""
        update_data = {
            "role_name": "Modified Viewer"
        }

        response = await portal_client.put(
            "/api/roles/viewer",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code == 400
        assert "系统内置角色不能修改" in response.json()["detail"]

    async def test_role_14_viewer_cannot_list_roles(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot list roles"""
        response = await portal_client.get(
            "/api/roles",
            headers=viewer_headers
        )
        assert response.status_code == 403


@pytest.mark.p2
class TestRoleValidation:
    """Test role input validation"""

    async def test_role_15_duplicate_role_code_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating role with duplicate code fails"""
        role_data = {
            "role_code": "viewer",  # Already exists
            "role_name": "Duplicate Viewer",
            "description": "Test",
            "permissions": ["data:read"]
        }

        response = await portal_client.post(
            "/api/roles",
            json=role_data,
            headers=super_admin_headers
        )
        assert response.status_code == 409
        assert "已存在" in response.json()["detail"]

    async def test_role_16_invalid_permission_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating role with invalid permission fails"""
        role_data = {
            "role_code": "test_invalid_perm",
            "role_name": "Test Invalid Perm",
            "description": "Test",
            "permissions": ["invalid:permission"]
        }

        response = await portal_client.post(
            "/api/roles",
            json=role_data,
            headers=super_admin_headers
        )
        assert response.status_code == 400
        assert "无效的权限" in response.json()["detail"]

    async def test_role_17_get_nonexistent_role_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Getting non-existent role returns 404"""
        response = await portal_client.get(
            "/api/roles/nonexistent_role_xyz",
            headers=super_admin_headers
        )
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


@pytest.mark.p3
class TestRoleIntegration:
    """Test role integration with users"""

    async def test_role_18_user_role_assignment(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify users can be assigned to roles"""
        # Create a test user
        user_data = {
            "username": "role_test_user",
            "password": "TestPass123!",
            "role": "data_scientist",
            "display_name": "Role Test User",
            "email": "roletest@test.com"
        }

        response = await portal_client.post(
            "/api/users",
            json=user_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201

        # Verify user has the role
        response = await portal_client.get(
            "/api/users/role_test_user",
            headers=super_admin_headers
        )
        user_data = response.json()["data"]
        assert user_data["role"] == "data_scientist"

        # Cleanup
        await portal_client.delete(
            "/api/users/role_test_user",
            headers=super_admin_headers
        )
