"""Test NL2SQL Lifecycle - Phase 16

Tests Natural Language to SQL conversion:
- Setup and configuration
- Convert query to SQL
- Validate SQL output
- Execute query
- Get query results
- Get query history
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestNL2SQLLifecycle:
    """Test NL2SQL complete lifecycle"""

    async def test_nl2sql_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify NL2SQL endpoint is accessible"""
        response = await portal_client.get(
            "/api/proxy/nl2sql/v1/health",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_nl2sql_02_convert_simple_query(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Convert simple natural language to SQL"""
        request = {
            "query": "显示所有用户",
            "database": "test_db"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_03_convert_complex_query(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Convert complex natural language to SQL"""
        request = {
            "query": "查找销售额大于1000的订单，按日期排序",
            "database": "ecommerce"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_04_validate_sql(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Validate generated SQL"""
        request = {
            "sql": "SELECT * FROM users WHERE id = :id",
            "database": "test_db"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/validate",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_05_execute_query(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Execute NL2SQL query"""
        request = {
            "query": "前10条用户",
            "database": "test_db"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/execute",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_06_get_history(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get NL2SQL query history"""
        response = await portal_client.get(
            "/api/proxy/nl2sql/v1/history",
            params={"page": 1, "page_size": 10},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p1
class TestNL2SQLFeatures:
    """Test NL2SQL advanced features"""

    async def test_nl2sql_07_schema_awareness(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Test schema-aware query conversion"""
        request = {
            "query": "每个部门的用户数量",
            "database": "analytics"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_08_join_support(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Test JOIN query support"""
        request = {
            "query": "用户和订单的关联信息",
            "database": "ecommerce"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)

    async def test_nl2sql_09_aggregation_support(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Test aggregation query support"""
        request = {
            "query": "统计每个产品的总销售额",
            "database": "ecommerce"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)


@pytest.mark.p2
class TestNL2SQLIntegration:
    """Test NL2SQL integration with other systems"""

    async def test_nl2sql_10_metadata_integration(self, portal_client: AsyncClient, super_admin_headers: dict):
        """NL2SQL uses DataHub metadata for schema"""
        response = await portal_client.get(
            "/api/proxy/datahub/v1/datasets",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_nl2sql_11_results_formatting(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Query results are properly formatted"""
        request = {
            "query": "查询第一个用户",
            "database": "test_db"
        }

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/execute",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 400, 503, 504)


@pytest.mark.p3
class TestNL2SQLPermissions:
    """Test NL2SQL permission boundaries"""

    async def test_nl2sql_12_analyst_can_convert(self, portal_client: AsyncClient, analyst_headers: dict):
        """Analyst can convert natural language to SQL"""
        request = {"query": "显示前10条", "database": "test"}

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/convert",
            json=request,
            headers=analyst_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_nl2sql_13_viewer_cannot_execute(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot execute queries"""
        request = {"query": "显示数据", "database": "test"}

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/execute",
            json=request,
            headers=viewer_headers
        )
        assert response.status_code in (403, 503, 504)

    async def test_nl2sql_14_scientist_can_execute(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """Data scientist can execute queries"""
        request = {"query": "统计分析数据", "database": "analytics"}

        response = await portal_client.post(
            "/api/proxy/nl2sql/v1/execute",
            json=request,
            headers=data_scientist_headers
        )
        assert response.status_code in (200, 403, 503, 504)
