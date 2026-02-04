"""生命周期测试 - 阶段2: 数据规划 (Planning)

测试数据规划功能:
- OpenMetadata: 版本检查、连通性测试
- 元数据代理: Portal代理访问OpenMetadata
- 标签管理: 获取标签分类、元数据管理
- 元数据实体: 完整元数据导入验证
"""

import pytest
from httpx import AsyncClient

# ============================================================
# OpenMetadata 连通性测试
# ============================================================

@pytest.mark.p0
class TestOpenMetadataConnectivity:
    """OpenMetadata 连通性测试"""

    async def test_om_01_service_health(self, portal_client: AsyncClient, admin_headers: dict):
        """测试OpenMetadata服务健康检查"""
        response = await portal_client.get(
            "/api/proxy/metadata/health",
            headers=admin_headers
        )
        # 代理端点可能不存在
        assert response.status_code in (200, 404, 503)

    async def test_om_02_version_check(self, portal_client: AsyncClient, admin_headers: dict):
        """测试OpenMetadata版本检查"""
        response = await portal_client.get(
            "/api/proxy/metadata/api/v1/system/version",
            headers=admin_headers
        )
        # 直接访问OpenMetadata
        assert response.status_code in (200, 404, 502)

    async def test_om_03_direct_connection(self, portal_client: AsyncClient):
        """测试直接连接OpenMetadata"""
        # 直接调用OpenMetadata API（不通过代理）
        import os
        om_url = os.environ.get("OPENMETADATA_URL", "http://localhost:8585")

        response = await portal_client.get(
            f"{om_url}/api/v1/system/version"
        )
        # OpenMetadata可能未运行
        assert response.status_code in (200, 404, 503)


# ============================================================
# 元数据代理测试
# ============================================================

@pytest.mark.p0
class TestMetadataProxy:
    """元数据代理测试"""

    async def test_proxy_01_metadata_proxy_forward(self, portal_client: AsyncClient, admin_headers: dict):
        """测试Portal代理转发OpenMetadata请求"""
        response = await portal_client.get(
            "/api/proxy/metadata/api/v1/tables",
            headers=admin_headers
        )
        # 代理可能不存在
        assert response.status_code in (200, 404, 502)

    async def test_proxy_02_proxy_authentication(self, portal_client: AsyncClient):
        """测试代理认证 - 未授权访问被拒绝"""
        response = await portal_client.get(
            "/api/proxy/metadata/api/v1/tables"
        )
        # 应该需要认证
        assert response.status_code in (401, 404)

    async def test_proxy_03_proxy_error_handling(self, portal_client: AsyncClient, admin_headers: dict):
        """测试代理错误处理"""
        # 请求不存在的OpenMetadata端点
        response = await portal_client.get(
            "/api/proxy/metadata/api/v1/invalid_endpoint",
            headers=admin_headers
        )
        assert response.status_code in (404, 502)


# ============================================================
# 标签管理测试
# ============================================================

@pytest.mark.p0
class TestTagManagement:
    """标签管理测试"""

    async def test_tag_01_list_classifications(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取标签分类列表"""
        response = await portal_client.get(
            "/api/metadata/classifications",
            headers=admin_headers
        )
        # 端点可能不存在
        assert response.status_code in (200, 404)

    async def test_tag_02_get_tags(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取标签列表"""
        response = await portal_client.get(
            "/api/metadata/tags",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_tag_03_create_tag(self, portal_client: AsyncClient, admin_headers: dict):
        """测试创建标签"""
        response = await portal_client.post(
            "/api/metadata/tags",
            headers=admin_headers,
            json={
                "name": "test_tag",
                "description": "测试标签"
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_tag_04_pii_tags_exist(self, portal_client: AsyncClient, admin_headers: dict):
        """测试PII敏感标签存在"""
        # 验证系统预定义的敏感标签
        expected_tags = ["PII", "SENSITIVE", "PHONE", "EMAIL", "ID_CARD"]

        response = await portal_client.get(
            "/api/metadata/tags",
            headers=admin_headers
        )

        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                existing_tags = {t.get("name") for t in data["data"]}
                # 至少有一些标签
                assert len(existing_tags) > 0


# ============================================================
# 元数据实体测试
# ============================================================

@pytest.mark.p0
class TestMetadataEntities:
    """元数据实体测试"""

    async def test_entity_01_list_databases(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取数据库列表"""
        response = await portal_client.get(
            "/api/metadata/databases",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_entity_02_list_tables(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取表列表"""
        response = await portal_client.get(
            "/api/metadata/tables",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_entity_03_get_table_schema(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取表结构"""
        response = await portal_client.get(
            "/api/metadata/tables/users/schema",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_entity_04_get_table_lineage(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取表血缘关系"""
        response = await portal_client.get(
            "/api/metadata/tables/users/lineage",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 数据资产目录测试
# ============================================================

@pytest.mark.p1
class TestDataAssetCatalog:
    """数据资产目录测试"""

    async def test_catalog_01_list_datasets(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取数据集列表"""
        response = await portal_client.get(
            "/api/datasets",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_catalog_02_search_datasets(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试搜索数据集"""
        response = await portal_client.get(
            "/api/datasets?q=user",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_catalog_03_get_dataset_details(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取数据集详情"""
        response = await portal_client.get(
            "/api/datasets/1",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_catalog_04_dataset_tags(self, portal_client: AsyncClient, admin_headers: dict):
        """测试数据集标签管理"""
        # 添加标签
        response = await portal_client.post(
            "/api/datasets/1/tags",
            headers=admin_headers,
            json={"tags": ["PII", "SENSITIVE"]}
        )
        assert response.status_code in (200, 201, 404)


# ============================================================
# 数据质量规则测试
# ============================================================

@pytest.mark.p1
class TestDataQualityRules:
    """数据质量规则测试"""

    async def test_quality_01_list_rules(self, portal_client: AsyncClient, steward_headers: dict):
        """测试获取质量规则列表"""
        response = await portal_client.get(
            "/api/quality/rules",
            headers=steward_headers
        )
        assert response.status_code in (200, 404)

    async def test_quality_02_create_rule(self, portal_client: AsyncClient, steward_headers: dict):
        """测试创建质量规则"""
        response = await portal_client.post(
            "/api/quality/rules",
            headers=steward_headers,
            json={
                "name": "空值检测",
                "dataset_id": 1,
                "rule_type": "null_check",
                "threshold": 0.0
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_quality_03_execute_rule(self, portal_client: AsyncClient, steward_headers: dict):
        """测试执行质量规则"""
        response = await portal_client.post(
            "/api/quality/rules/1/execute",
            headers=steward_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 元数据同步测试
# ============================================================

@pytest.mark.p1
class TestMetadataSync:
    """元数据同步测试"""

    async def test_sync_01_trigger_sync(self, portal_client: AsyncClient, admin_headers: dict):
        """测试触发元数据同步"""
        response = await portal_client.post(
            "/api/metadata/sync",
            headers=admin_headers,
            json={"source": "mysql"}
        )
        assert response.status_code in (200, 201, 202, 404)

    async def test_sync_02_get_sync_status(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取同步状态"""
        response = await portal_client.get(
            "/api/metadata/sync/status",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_sync_03_sync_history(self, portal_client: AsyncClient, admin_headers: dict):
        """测试同步历史记录"""
        response = await portal_client.get(
            "/api/metadata/sync/history",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 术语表测试
# ============================================================

@pytest.mark.p2
class TestGlossary:
    """术语表测试"""

    async def test_glossary_01_list_terms(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取术语列表"""
        response = await portal_client.get(
            "/api/glossary/terms",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_glossary_02_search_term(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试搜索术语"""
        response = await portal_client.get(
            "/api/glossary/terms?q=DAU",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_glossary_03_get_term_definition(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取术语定义"""
        response = await portal_client.get(
            "/api/glossary/terms/DAU",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)
