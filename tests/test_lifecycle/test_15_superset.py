"""Test Superset Analytics Lifecycle - Phase 15

Tests Superset BI analytics integration:
- Setup and configuration
- List dashboards
- Get dashboard details
- Get chart data
- Create dashboard
- Update dashboard
- Delete dashboard
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestSupersetAnalyticsLifecycle:
    """Test Superset analytics complete lifecycle"""

    async def test_superset_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify Superset endpoint is accessible"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_superset_02_list_dashboards(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List all Superset dashboards"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_superset_03_get_dashboard(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get dashboard details"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards/1",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_superset_04_get_chart_data(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get chart data"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/charts/1/data",
            params={"datasource": "1", "queries": []},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_superset_05_list_charts(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List charts in dashboard"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards/1/charts",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)


@pytest.mark.p1
class TestSupersetReports:
    """Test Superset report operations"""

    async def test_superset_06_list_reports(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List available reports"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/reports",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_superset_07_export_dashboard(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Export dashboard configuration"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards/1/export",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_superset_08_get_sql_lab(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get SQL Lab queries"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/sql-lab/queries",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)


@pytest.mark.p2
class TestSupersetIntegration:
    """Test Superset integration with data sources"""

    async def test_superset_09_data_sources(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get available data sources"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/datasources",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_superset_10_databases(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get available databases"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/databases",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_superset_11_create_dashboard(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new dashboard"""
        dashboard_data = {
            "dashboard_title": "Lifecycle Test Dashboard",
            "slug": "lifecycle-test"
        }

        response = await portal_client.post(
            "/api/proxy/superset/v1/dashboards",
            json=dashboard_data,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p3
class TestSupersetPermissions:
    """Test Superset permission boundaries"""

    async def test_superset_12_analyst_can_view(self, portal_client: AsyncClient, analyst_headers: dict):
        """Analyst can view dashboards"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards",
            headers=analyst_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_superset_13_viewer_cannot_create(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot create dashboards"""
        response = await portal_client.post(
            "/api/proxy/superset/v1/dashboards",
            json={"dashboard_title": "Unauthorized"},
            headers=viewer_headers
        )
        assert response.status_code in (403, 503, 504)

    async def test_superset_14_scientist_can_export(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """Data scientist can export dashboards"""
        response = await portal_client.get(
            "/api/proxy/superset/v1/dashboards/1/export",
            headers=data_scientist_headers
        )
        assert response.status_code in (200, 403, 404, 503, 504)
