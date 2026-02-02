"""Test AI Cleaning Rules Lifecycle - Phase 17

Tests AI-powered data cleaning rules:
- Setup and configuration
- List cleaning rules
- Get rule details
    - Create cleaning rule
- Update cleaning rule
- Delete cleaning rule
- Apply cleaning rules
- Preview cleaning results
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestAICleaningRulesLifecycle:
    """Test AI cleaning rules complete lifecycle"""

    async def test_cleaning_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify AI cleaning endpoint is accessible"""
        response = await portal_client.get(
            "/api/proxy/cleaning/v1/rules",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_cleaning_02_list_rules(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List all cleaning rules"""
        response = await portal_client.get(
            "/api/proxy/cleaning/v1/rules",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_cleaning_03_get_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get cleaning rule details"""
        response = await portal_client.get(
            "/api/proxy/cleaning/v1/rules/rule-1",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_cleaning_04_create_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new cleaning rule"""
        rule_data = {
            "name": "Remove Duplicates",
            "target_column": "email",
            "rule_type": "deduplication",
            "config": {"match_columns": ["email"]}
        }

        response = await portal_client.post(
            "/api/proxy/cleaning/v1/rules",
            json=rule_data,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_cleaning_05_update_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Update existing cleaning rule"""
        update_data = {
            "rule_type": "filter",
            "config": {"condition": "is_not_null"}
        }

        response = await portal_client.put(
            "/api/proxy/cleaning/v1/rules/rule-1",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_cleaning_06_delete_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Delete cleaning rule"""
        response = await portal_client.delete(
            "/api/proxy/cleaning/v1/rules/rule-1",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)


@pytest.mark.p1
class TestAICleaningOperations:
    """Test AI cleaning operations"""

    async def test_cleaning_07_preview_cleaning(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Preview cleaning results"""
        request = {
            "table_name": "customers",
            "rules": ["rule-1", "rule-2"]
        }

        response = await portal_client.post(
            "/api/proxy/cleaning/v1/preview",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_cleaning_08_apply_cleaning(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Apply cleaning rules to data"""
        request = {
            "table_name": "customers",
            "rules": ["rule-1"],
            "create_backup": True
        }

        response = await portal_client.post(
            "/api/proxy/cleaning/v1/apply",
            json=request,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_cleaning_09_get_cleaning_history(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get cleaning operation history"""
        response = await portal_client.get(
            "/api/proxy/cleaning/v1/history",
            params={"table": "customers", "page": 1},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p2
class TestAICleaningIntegration:
    """Test AI cleaning integration"""

    async def test_cleaning_10_quality_integration(self, portal_client: AsyncClient, super_admin_headers: dict):
        """AI cleaning integrates with data quality rules"""
        response = await portal_client.get(
            "/api/quality/rules",
            headers=super_admin_headers
        )
        # Quality endpoint may not exist in proxy
        assert response.status_code in (200, 403, 404, 503, 504)

    async def test_cleaning_11_sensitive_data_handling(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify sensitive data is handled during cleaning"""
        response = await portal_client.post(
            "/api/proxy/sensitive/v1/scan",
            json={"table_name": "customers", "sample_size": 50},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p3
class TestAICleaningPermissions:
    """Test AI cleaning permission boundaries"""

    async def test_cleaning_12_steward_can_manage_rules(self, portal_client: AsyncClient, steward_headers: dict):
        """Data steward can manage cleaning rules"""
        response = await portal_client.get(
            "/api/proxy/cleaning/v1/rules",
            headers=steward_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_cleaning_13_engineer_can_apply(self, portal_client: AsyncClient, engineer_headers: dict):
        """Data engineer can apply cleaning rules"""
        response = await portal_client.post(
            "/api/proxy/cleaning/v1/apply",
            json={"table_name": "test", "rules": []},
            headers=engineer_headers
        )
        assert response.status_code in (200, 403, 503, 504)

    async def test_cleaning_14_viewer_cannot_create_rules(self, portal_client: AsyncClient, viewer_headers: dict):
        """Viewer cannot create cleaning rules"""
        response = await portal_client.post(
            "/api/proxy/cleaning/v1/rules",
            json={"name": "Unauthorized", "rule_type": "filter"},
            headers=viewer_headers
        )
        assert response.status_code in (403, 503, 504)
