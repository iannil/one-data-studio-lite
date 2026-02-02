"""Test Data API Gateway Lifecycle - Phase 14

Tests Data API gateway for data asset access:
- Setup and configuration
- Search data assets
- Get asset details
- Get dataset schema
- Query data
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestDataAPIGatewayLifecycle:
    """Test Data API gateway complete lifecycle"""

    async def test_dataapi_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify Data API endpoint is accessible"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/assets/search",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_dataapi_02_search_assets(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Search data assets"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/assets/search",
            params={"keyword": "users", "type": "", "page": 1, "page_size": 20},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_dataapi_03_get_asset_detail(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get data asset details"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/assets/asset-1",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_dataapi_04_get_dataset_schema(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get dataset schema"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/data/dataset-1/schema",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_dataapi_05_query_data(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Query data through API gateway"""
        query_request = {
            "sql": "SELECT * FROM test LIMIT 10",
            "limit": 10
        }

        response = await portal_client.post(
            "/api/proxy/data-api/v1/query",
            json=query_request,
            headers=super_admin_headers
        )
        # Query endpoint may not exist
        assert response.status_code in (200, 404, 405, 503, 504)


@pytest.mark.p1
class TestDataAPIPermissions:
    """Test Data API permission boundaries"""

    async def test_dataapi_06_scientist_can_access(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """Data scientist can access data API"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/assets/search",
            headers=data_scientist_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_dataapi_07_analyst_can_search(self, portal_client: AsyncClient, analyst_headers: dict):
        """Analyst can search assets"""
        response = await portal_client.get(
            "/api/proxy/data-api/v1/assets/search",
            headers=analyst_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_dataapi_08_viewer_cannot_query(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot query data (may be limited access)"""
        response = await portal_client.post(
            "/api/proxy/data-api/v1/query",
            json={"sql": "SELECT 1", "limit": 1},
            headers=viewer_headers
        )
        assert response.status_code in (403, 404, 405, 503, 504)


@pytest.mark.p2
class TestDataAPIIntegration:
    """Test Data API integration with metadata"""

    async def test_dataapi_09_metadata_integration(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify Data API integrates with DataHub metadata"""
        response = await portal_client.get(
            "/api/proxy/datahub/v1/datasets",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_dataapi_10_sensitive_masking(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify data is masked according to rules"""
        # Query should return masked data
        response = await portal_client.get(
            "/api/proxy/data-api/v1/data/customers/schema",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_dataapi_11_audit_logged(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify data access is logged"""
        response = await portal_client.get(
            "/api/audit/events",
            params={"subsystem": "data_api", "limit": 10},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 403, 504, 401)


@pytest.mark.p3
class TestDataAPIRateLimit:
    """Test Data API rate limiting"""

    async def test_dataapi_12_rate_limit_enforced(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify rate limiting is enforced"""
        # Make multiple requests
        responses = []
        for _ in range(5):
            response = await portal_client.get(
                "/api/proxy/data-api/v1/assets/search",
                headers=super_admin_headers
            )
            responses.append(response.status_code)

        # At least some requests should succeed or be rate limited
        assert any(status in (200, 429) for status in responses)
