"""Test Service Account Lifecycle - Phase 04

Tests complete service account lifecycle:
- Setup and configuration
- Create service account
- Read/retrieve service account
- Update service account (via regenerate)
- Delete service account
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestServiceAccountLifecycle:
    """Test service account complete lifecycle"""

    async def test_sa_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify service account system is ready"""
        response = await portal_client.get(
            "/api/service-accounts",
            headers=super_admin_headers
        )
        assert response.status_code == 200

    async def test_sa_02_list_predefined(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List existing service accounts"""
        response = await portal_client.get(
            "/api/service-accounts",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    async def test_sa_03_create(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new service account"""
        sa_data = {
            "name": "lifecycle_test_sa",
            "display_name": "Lifecycle Test Service Account",
            "description": "Service account for lifecycle testing",
            "role": "service_account"
        }

        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        # ServiceAccountCreateResponse returns data directly (not wrapped in ApiResponse)
        assert data["name"] == "lifecycle_test_sa"
        assert "secret" in data  # Secret only shown on creation
        assert len(data["secret"]) > 20  # Secrets are long

    async def test_sa_04_get(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get service account details"""
        response = await portal_client.get(
            "/api/service-accounts/lifecycle_test_sa",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "data" in data
        sa = data.get("data") if "data" in data else data
        assert sa["name"] == "lifecycle_test_sa"
        assert sa["display_name"] == "Lifecycle Test Service Account"
        assert sa["is_active"] is True
        assert "secret" not in sa  # Secret not shown on GET

    async def test_sa_05_disable(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Disable service account"""
        response = await portal_client.post(
            "/api/service-accounts/lifecycle_test_sa/disable",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify it's disabled
        response = await portal_client.get(
            "/api/service-accounts/lifecycle_test_sa",
            headers=super_admin_headers
        )
        assert response.json()["data"]["is_active"] is False

    async def test_sa_06_enable(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Enable disabled service account"""
        response = await portal_client.post(
            "/api/service-accounts/lifecycle_test_sa/enable",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify it's enabled
        response = await portal_client.get(
            "/api/service-accounts/lifecycle_test_sa",
            headers=super_admin_headers
        )
        assert response.json()["data"]["is_active"] is True

    async def test_sa_07_regenerate_secret(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Regenerate service account secret"""
        response = await portal_client.post(
            "/api/service-accounts/lifecycle_test_sa/regenerate-secret",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "data" in data
        assert "secret" in data["data"]
        assert "warning" in data["data"]
        assert len(data["data"]["secret"]) > 20

    async def test_sa_08_delete(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Delete service account"""
        response = await portal_client.delete(
            "/api/service-accounts/lifecycle_test_sa",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # ApiResponse format: code, message, data, timestamp
        assert data.get("code") == 20000 or "message" in data

        # Verify it's deleted
        response = await portal_client.get(
            "/api/service-accounts/lifecycle_test_sa",
            headers=super_admin_headers
        )
        assert response.status_code == 404


@pytest.mark.p1
class TestServiceAccountPermissions:
    """Test service account permission boundaries"""

    async def test_sa_09_viewer_cannot_list(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot list service accounts"""
        response = await portal_client.get(
            "/api/service-accounts",
            headers=viewer_headers
        )
        assert response.status_code == 403

    async def test_sa_10_viewer_cannot_create(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot create service accounts"""
        sa_data = {
            "name": "test_viewer_sa",
            "display_name": "Test",
            "description": "Test",
            "role": "service_account"
        }

        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=viewer_headers
        )
        assert response.status_code == 403

    async def test_sa_11_analyst_cannot_create(self, portal_client: AsyncClient, analyst_headers: dict):
        """Analyst cannot create service accounts"""
        sa_data = {
            "name": "test_analyst_sa",
            "display_name": "Test",
            "description": "Test",
            "role": "service_account"
        }

        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=analyst_headers
        )
        assert response.status_code == 403


@pytest.mark.p2
class TestServiceAccountValidation:
    """Test service account input validation"""

    async def test_sa_12_duplicate_name_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating service account with duplicate name fails"""
        # First create a service account
        sa_data = {
            "name": "test_duplicate_sa",
            "display_name": "Duplicate Test SA",
            "description": "Test",
            "role": "service_account"
        }

        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )
        assert response.status_code == 201

        # Try to create with same name
        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )
        assert response.status_code == 409
        assert "已存在" in response.json()["detail"]

        # Cleanup
        await portal_client.delete(
            "/api/service-accounts/test_duplicate_sa",
            headers=super_admin_headers
        )

    async def test_sa_13_invalid_role_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Creating service account with invalid role fails"""
        sa_data = {
            "name": "test_invalid_role_sa",
            "display_name": "Test",
            "description": "Test",
            "role": "invalid_role"
        }

        response = await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]

    async def test_sa_14_get_nonexistent_fails(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Getting non-existent service account returns 404"""
        response = await portal_client.get(
            "/api/service-accounts/nonexistent_sa_xyz",
            headers=super_admin_headers
        )
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


@pytest.mark.p3
class TestServiceAccountCallHistory:
    """Test service account call history tracking"""

    async def test_sa_15_call_history_empty(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get call history for service account (may be empty)"""
        # Create a test service account
        sa_data = {
            "name": "history_test_sa",
            "display_name": "History Test SA",
            "description": "Test call history",
            "role": "service_account"
        }

        await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )

        response = await portal_client.get(
            "/api/service-accounts/history_test_sa/call-history",
            headers=super_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "stats" in data

        # Cleanup
        await portal_client.delete(
            "/api/service-accounts/history_test_sa",
            headers=super_admin_headers
        )

    async def test_sa_16_call_stats(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get call statistics for service account"""
        # First create a service account
        sa_data = {
            "name": "stats_test_sa",
            "display_name": "Stats Test SA",
            "description": "Test call stats",
            "role": "service_account"
        }

        await portal_client.post(
            "/api/service-accounts",
            json=sa_data,
            headers=super_admin_headers
        )

        # Get call stats for the created service account
        response = await portal_client.get(
            "/api/service-accounts/stats_test_sa/call-history/stats",
            headers=super_admin_headers
        )
        # Should return 200 (empty stats) or 404 (no calls yet)
        assert response.status_code in (200, 404)

        # Cleanup
        await portal_client.delete(
            "/api/service-accounts/stats_test_sa",
            headers=super_admin_headers
        )
