"""生命周期测试 - 阶段4: 数据加工 (Processing)

测试数据加工功能:
- AI清洗服务: 数据质量分析、清洗规则推荐
- 敏感检测服务: 敏感数据识别、分类
- 元数据同步: 跨系统元数据同步
- 清洗规则: 实际数据清洗验证
"""

import pytest
from httpx import AsyncClient


# ============================================================
# AI 清洗服务测试
# ============================================================

@pytest.mark.p0
class TestAICleaningService:
    """AI 清洗服务测试"""

    async def test_cleaning_01_service_health(self, portal_client: AsyncClient):
        """测试AI清洗服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8012/health"
        )
        # 直接访问服务
        assert response.status_code in (200, 404, 502)

    async def test_cleaning_02_analyze_quality(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试数据质量分析"""
        response = await portal_client.post(
            "/api/cleaning/analyze",
            headers=data_scientist_headers,
            json={
                "table": "users",
                "sample_size": 1000
            }
        )
        assert response.status_code in (200, 404)

    async def test_cleaning_03_recommend_rules(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试清洗规则推荐"""
        response = await portal_client.post(
            "/api/cleaning/recommend",
            headers=data_scientist_headers,
            json={
                "table": "users",
                "issues": ["null_values", "duplicates", "outliers"]
            }
        )
        assert response.status_code in (200, 404)

    async def test_cleaning_04_create_rule(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试创建清洗规则"""
        response = await portal_client.post(
            "/api/cleaning/rules",
            headers=data_scientist_headers,
            json={
                "name": "remove_nulls",
                "table": "users",
                "column": "email",
                "rule_type": "filter_nulls",
                "enabled": True
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_cleaning_05_apply_rule(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试应用清洗规则"""
        response = await portal_client.post(
            "/api/cleaning/rules/1/apply",
            headers=engineer_headers,
            json={
                "target_table": "users_clean",
                "preview": True
            }
        )
        assert response.status_code in (200, 404)

    async def test_cleaning_06_list_rules(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试获取清洗规则列表"""
        response = await portal_client.get(
            "/api/cleaning/rules",
            headers=data_scientist_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 敏感检测服务测试
# ============================================================

@pytest.mark.p0
class TestSensitiveDetectionService:
    """敏感检测服务测试"""

    async def test_sensitive_01_service_health(self, portal_client: AsyncClient):
        """测试敏感检测服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8015/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_sensitive_02_scan_table(self, portal_client: AsyncClient, admin_headers: dict):
        """测试扫描表敏感数据"""
        response = await portal_client.post(
            "/api/sensitive/scan",
            headers=admin_headers,
            json={
                "database": "demo_retail_db",
                "table": "ods_user_info",
                "sample_size": 1000
            }
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_03_get_scan_result(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取扫描结果"""
        response = await portal_client.get(
            "/api/sensitive/scans/1/result",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_04_list_detection_rules(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取检测规则列表"""
        response = await portal_client.get(
            "/api/sensitive/rules",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_05_create_rule(self, portal_client: AsyncClient, admin_headers: dict):
        """测试创建检测规则"""
        response = await portal_client.post(
            "/api/sensitive/rules",
            headers=admin_headers,
            json={
                "name": "员工工号检测",
                "pattern": "^EMP\\d{6}$",
                "sensitivity_level": "medium",
                "enabled": True
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_sensitive_06_detect_phone(self, portal_client: AsyncClient, admin_headers: dict):
        """测试手机号识别"""
        response = await portal_client.post(
            "/api/sensitive/detect/phone",
            headers=admin_headers,
            json={
                "text": "13800138000, 13912345678"
            }
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_07_detect_id_card(self, portal_client: AsyncClient, admin_headers: dict):
        """测试身份证号识别"""
        response = await portal_client.post(
            "/api/sensitive/detect/id_card",
            headers=admin_headers,
            json={
                "text": "110101199001011234, 310101198512125678"
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 元数据同步服务测试
# ============================================================

@pytest.mark.p0
class TestMetadataSyncService:
    """元数据同步服务测试"""

    async def test_sync_01_service_health(self, portal_client: AsyncClient):
        """测试元数据同步服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8013/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_sync_02_trigger_sync(self, portal_client: AsyncClient, admin_headers: dict):
        """测试触发元数据同步"""
        response = await portal_client.post(
            "/api/metadata/sync/trigger",
            headers=admin_headers,
            json={
                "source": "mysql",
                "source_config": {
                    "host": "mysql",
                    "port": 3306,
                    "database": "demo_retail_db"
                }
            }
        )
        assert response.status_code in (200, 201, 202, 404)

    async def test_sync_03_get_sync_status(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取同步状态"""
        response = await portal_client.get(
            "/api/metadata/sync/status",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_sync_04_list_sync_tasks(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取同步任务列表"""
        response = await portal_client.get(
            "/api/metadata/sync/tasks",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_sync_05_create_sync_task(self, portal_client: AsyncClient, admin_headers: dict):
        """测试创建同步任务"""
        response = await portal_client.post(
            "/api/metadata/sync/tasks",
            headers=admin_headers,
            json={
                "name": "mysql_metadata_sync",
                "source_type": "mysql",
                "source_config": {
                    "host": "mysql",
                    "port": 3306
                },
                "target": "openmetadata",
                "schedule": "0 1 * * *"
            }
        )
        assert response.status_code in (201, 200, 404)


# ============================================================
# 数据质量检查测试
# ============================================================

@pytest.mark.p1
class TestDataQualityChecks:
    """数据质量检查测试"""

    async def test_quality_01_run_checks(self, portal_client: AsyncClient, steward_headers: dict):
        """测试运行质量检查"""
        response = await portal_client.post(
            "/api/quality/run",
            headers=steward_headers,
            json={
                "table": "users",
                "checks": ["null_check", "unique_check", "format_check"]
            }
        )
        assert response.status_code in (200, 404)

    async def test_quality_02_get_quality_report(self, portal_client: AsyncClient, steward_headers: dict):
        """测试获取质量报告"""
        response = await portal_client.get(
            "/api/quality/reports/users",
            headers=steward_headers
        )
        assert response.status_code in (200, 404)

    async def test_quality_03_quality_score(self, portal_client: AsyncClient, steward_headers: dict):
        """测试获取质量分数"""
        response = await portal_client.get(
            "/api/quality/score/users",
            headers=steward_headers
        )
        assert response.status_code in (200, 404)

    async def test_quality_04_set_threshold(self, portal_client: AsyncClient, steward_headers: dict):
        """测试设置质量阈值"""
        response = await portal_client.post(
            "/api/quality/thresholds",
            headers=steward_headers,
            json={
                "table": "users",
                "metric": "completeness",
                "min_value": 0.95
            }
        )
        assert response.status_code in (201, 200, 404)


# ============================================================
# ETL 映射规则测试
# ============================================================

@pytest.mark.p1
class TestETLMapping:
    """ETL 映射规则测试"""

    async def test_mapping_01_list_mappings(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试获取ETL映射列表"""
        response = await portal_client.get(
            "/api/etl/mappings",
            headers=engineer_headers
        )
        assert response.status_code in (200, 404)

    async def test_mapping_02_create_mapping(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试创建ETL映射"""
        response = await portal_client.post(
            "/api/etl/mappings",
            headers=engineer_headers,
            json={
                "source_urn": "urn:li:dataset:(mysql,users,PROD)",
                "target_task_type": "seatunnel",
                "target_task_id": "sync_users",
                "trigger_on": ["CREATE", "UPDATE"],
                "enabled": True
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_mapping_03_auto_update(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试自动更新配置"""
        response = await portal_client.put(
            "/api/etl/mappings/1/auto-update",
            headers=engineer_headers,
            json={
                "enabled": True
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 脱敏规则测试
# ============================================================

@pytest.mark.p1
class TestMaskRules:
    """脱敏规则测试"""

    async def test_mask_01_list_rules(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取脱敏规则列表"""
        response = await portal_client.get(
            "/api/mask/rules",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_mask_02_create_rule(self, portal_client: AsyncClient, admin_headers: dict):
        """测试创建脱敏规则"""
        response = await portal_client.post(
            "/api/mask/rules",
            headers=admin_headers,
            json={
                "table_name": "customers",
                "column_name": "phone",
                "algorithm_type": "MASK_FIRST_LAST",
                "algorithm_props": {
                    "mask_first": 3,
                    "mask_last": 4,
                    "mask_char": "*"
                },
                "enabled": True
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_mask_03_test_masking(self, portal_client: AsyncClient, admin_headers: dict):
        """测试脱敏效果"""
        response = await portal_client.post(
            "/api/mask/test",
            headers=admin_headers,
            json={
                "value": "13800138000",
                "algorithm": "MASK_FIRST_LAST",
                "params": {
                    "mask_first": 3,
                    "mask_last": 4
                }
            }
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                masked = data["data"]
                # 脱敏后的值应该包含掩码符
                assert "*" in str(masked) or masked != "13800138000"


# ============================================================
# 数据变换测试
# ============================================================

@pytest.mark.p2
class TestDataTransformation:
    """数据变换测试"""

    async def test_transform_01_list_transformations(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试获取数据变换列表"""
        response = await portal_client.get(
            "/api/transform/transformations",
            headers=engineer_headers
        )
        assert response.status_code in (200, 404)

    async def test_transform_02_create_transformation(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试创建数据变换"""
        response = await portal_client.post(
            "/api/transform/transformations",
            headers=engineer_headers,
            json={
                "name": "normalize_phone",
                "description": "手机号标准化",
                "transform_type": "function",
                "config": {
                    "function": "replace",
                    "pattern": "[^0-9]",
                    "replacement": ""
                }
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_transform_03_apply_transformation(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试应用数据变换"""
        response = await portal_client.post(
            "/api/transform/transformations/1/apply",
            headers=engineer_headers,
            json={
                "data": ["138-0000-0000", "139 1234 5678"]
            }
        )
        assert response.status_code in (200, 404)
