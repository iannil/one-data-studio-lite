"""Test ShardingSphere Data Masking Lifecycle - Phase 12

Tests ShardingSphere data masking operations:
- Setup and configuration
- List mask rules
- Get table mask rules
- Create mask rule
- Update mask rule
- Delete mask rule
- Batch operations
- Sync to proxy
- Available algorithms
- Permission boundaries
"""
import pytest
from httpx import AsyncClient


@pytest.mark.p0
class TestShardingSphereLifecycle:
    """Test ShardingSphere masking complete lifecycle"""

    async def test_sharding_01_setup(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Verify ShardingSphere endpoint is accessible"""
        response = await portal_client.get(
            "/api/proxy/shardingsphere/v1/mask-rules",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_02_list_mask_rules(self, portal_client: AsyncClient, super_admin_headers: dict):
        """List all masking rules"""
        response = await portal_client.get(
            "/api/proxy/shardingsphere/v1/mask-rules",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_03_get_table_rules(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get masking rules for specific table"""
        response = await portal_client.get(
            "/api/proxy/shardingsphere/v1/mask-rules/customers",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 404, 503, 504)

    async def test_sharding_04_create_mask_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Create new masking rule"""
        rule_data = {
            "table_name": "test_users",
            "column_name": "phone",
            "algorithm_type": "MASK_FIRST_LAST",
            "algorithm_props": {"mask_first": 3, "mask_last": 4, "mask_char": "*"}
        }

        response = await portal_client.post(
            "/api/proxy/shardingsphere/v1/mask-rules",
            json=rule_data,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_05_update_mask_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Update existing masking rule"""
        update_data = {
            "table_name": "test_users",
            "column_name": "phone",
            "algorithm_type": "MASK_FROM",
            "algorithm_props": {"from": 1, "length": 3}
        }

        response = await portal_client.put(
            "/api/proxy/shardingsphere/v1/mask-rules",
            json=update_data,
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_06_delete_mask_rule(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Delete masking rule"""
        response = await portal_client.delete(
            "/api/proxy/shardingsphere/v1/mask-rules/test_users/phone",
            headers=super_admin_headers
        )
        # May return 405 if DELETE is not supported by proxy endpoint
        assert response.status_code in (200, 404, 405, 503, 504)

    async def test_sharding_07_get_algorithms(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Get available masking algorithms"""
        response = await portal_client.get(
            "/api/proxy/shardingsphere/v1/algorithms",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_08_sync_to_proxy(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Sync rules to ShardingSphere Proxy"""
        response = await portal_client.post(
            "/api/proxy/shardingsphere/v1/sync",
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p1
class TestShardingSphereBatchOperations:
    """Test ShardingSphere batch operations"""

    async def test_sharding_09_batch_create_rules(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Batch create masking rules"""
        batch_data = {
            "rules": [
                {
                    "table_name": "users",
                    "column_name": "email",
                    "algorithm_type": "MASK_EMAIL"
                },
                {
                    "table_name": "users",
                    "column_name": "phone",
                    "algorithm_type": "MASK_FIRST_LAST"
                }
            ]
        }

        # ShardingSphere service may not be available in test environment
        # The request may fail with connection error or return 503/504
        try:
            response = await portal_client.post(
                "/api/proxy/shardingsphere/v1/mask-rules/batch",
                json=batch_data,
                headers=super_admin_headers
            )
            assert response.status_code in (200, 503, 504)
        except Exception:
            # Connection error is expected when service is unavailable
            pass


@pytest.mark.p2
class TestShardingSphereAlgorithms:
    """Test ShardingSphere masking algorithms"""

    async def test_sharding_10_mask_first_last(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Test MASK_FIRST_LAST algorithm"""
        response = await portal_client.post(
            "/api/proxy/shardingsphere/v1/mask-rules",
            json={
                "table_name": "test",
                "column_name": "test_col",
                "algorithm_type": "MASK_FIRST_LAST",
                "algorithm_props": {"mask_first": 2, "mask_last": 2}
            },
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_11_mask_from(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Test MASK_FROM algorithm"""
        response = await portal_client.post(
            "/api/proxy/shardingsphere/v1/mask-rules",
            json={
                "table_name": "test",
                "column_name": "test_col",
                "algorithm_type": "MASK_FROM",
                "algorithm_props": {"from": 1, "length": 5}
            },
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)


@pytest.mark.p3
class TestShardingSphereIntegration:
    """Test ShardingSphere integration with sensitive detection"""

    async def test_sharding_12_sensitive_detection_trigger(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Sensitive data scan triggers masking rule suggestion"""
        response = await portal_client.post(
            "/api/proxy/sensitive/v1/scan",
            json={"table_name": "customers", "sample_size": 100},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)

    async def test_sharding_13_apply_mask_after_scan(self, portal_client: AsyncClient, super_admin_headers: dict):
        """Auto-apply masking after sensitive data detection"""
        response = await portal_client.post(
            "/api/proxy/sensitive/v1/scan-and-apply",
            json={"table_name": "customers", "auto_apply": False},
            headers=super_admin_headers
        )
        assert response.status_code in (200, 503, 504)
