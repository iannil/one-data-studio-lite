"""Unit tests for sensitive_detect service main module

Tests for services/sensitive_detect/main.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from services.sensitive_detect.main import (
    app,
    _rule_orm_to_pydantic,
    _rule_pydantic_to_orm,
    _field_to_orm,
    _field_orm_to_pydantic,
    _report_orm_to_pydantic,
    _level_order,
    get_current_user,
)
from services.sensitive_detect.models import (
    ScanRequest,
    ScanReport,
    SensitiveField,
    SensitivityLevel,
    DetectionRule,
    ClassifyRequest,
)
from services.common.auth import TokenPayload


# Mock user for testing
MOCK_USER = TokenPayload(
    sub="test",
    username="test",
    role="viewer",
    exp=datetime(2099, 12, 31),
    iat=datetime(2023, 1, 1)
)


async def mock_get_current_user():
    return MOCK_USER


class TestLevelOrder:
    """测试敏感级别排序"""

    def test_level_order_low(self):
        """测试低级别"""
        assert _level_order(SensitivityLevel.LOW) == 0

    def test_level_order_medium(self):
        """测试中级别"""
        assert _level_order(SensitivityLevel.MEDIUM) == 1

    def test_level_order_high(self):
        """测试高级别"""
        assert _level_order(SensitivityLevel.HIGH) == 2

    def test_level_order_critical(self):
        """测试严重级别"""
        assert _level_order(SensitivityLevel.CRITICAL) == 3


class TestRuleOrmToPydantic:
    """测试规则ORM转Pydantic"""

    def test_rule_orm_to_pydantic(self):
        """测试转换"""
        mock_orm = MagicMock()
        mock_orm.id = "rule-123"
        mock_orm.name = "测试规则"
        mock_orm.pattern = "\\d{11}"
        mock_orm.sensitivity_level = "high"
        mock_orm.description = "手机号"
        mock_orm.enabled = True

        result = _rule_orm_to_pydantic(mock_orm)

        assert result.id == "rule-123"
        assert result.name == "测试规则"
        assert result.pattern == "\\d{11}"
        assert result.sensitivity_level == SensitivityLevel.HIGH
        assert result.description == "手机号"
        assert result.enabled is True


class TestRulePydanticToOrm:
    """测试规则Pydantic转ORM"""

    def test_rule_pydantic_to_orm(self):
        """测试转换"""
        rule = DetectionRule(
            id="rule-123",
            name="测试规则",
            pattern="\\d{11}",
            sensitivity_level=SensitivityLevel.HIGH,
            description="手机号",
            enabled=True,
        )

        result = _rule_pydantic_to_orm(rule)

        assert result.id == "rule-123"
        assert result.name == "测试规则"
        assert result.pattern == "\\d{11}"
        assert result.sensitivity_level == "high"
        assert result.description == "手机号"
        assert result.enabled is True


class TestFieldToOrm:
    """测试字段Pydantic转ORM"""

    def test_field_to_orm(self):
        """测试转换"""
        field = SensitiveField(
            column_name="phone",
            sensitivity_level=SensitivityLevel.HIGH,
            detected_types=["phone"],
            detection_method="regex",
            sample_count=10,
            confidence=0.8,
        )

        result = _field_to_orm(field, "report-123")

        assert result.report_id == "report-123"
        assert result.column_name == "phone"
        assert result.sensitivity_level == "high"
        assert result.detected_types == ["phone"]
        assert result.detection_method == "regex"
        assert result.sample_count == 10
        assert result.confidence == 0.8


class TestFieldOrmToPydantic:
    """测试字段ORM转Pydantic"""

    def test_field_orm_to_pydantic(self):
        """测试转换"""
        mock_orm = MagicMock()
        mock_orm.column_name = "phone"
        mock_orm.sensitivity_level = "high"
        mock_orm.detected_types = ["phone"]
        mock_orm.detection_method = "regex"
        mock_orm.sample_count = 10
        mock_orm.confidence = 0.8

        result = _field_orm_to_pydantic(mock_orm)

        assert result.column_name == "phone"
        assert result.sensitivity_level == SensitivityLevel.HIGH
        assert result.detected_types == ["phone"]
        assert result.detection_method == "regex"
        assert result.sample_count == 10
        assert result.confidence == 0.8


class TestReportOrmToPydantic:
    """测试报告ORM转Pydantic"""

    def test_report_orm_to_pydantic(self):
        """测试转换"""
        mock_report = MagicMock()
        mock_report.id = "report-123"
        mock_report.table_name = "users"
        mock_report.scan_time = datetime.now(timezone.utc)
        mock_report.total_columns = 10
        mock_report.sensitive_columns = 2
        mock_report.risk_level = "high"

        mock_field1 = MagicMock()
        mock_field1.column_name = "phone"
        mock_field1.sensitivity_level = "high"
        mock_field1.detected_types = ["phone"]
        mock_field1.detection_method = "regex"
        mock_field1.sample_count = 10
        mock_field1.confidence = 0.8

        mock_field2 = MagicMock()
        mock_field2.column_name = "email"
        mock_field2.sensitivity_level = "medium"
        mock_field2.detected_types = ["email"]
        mock_field2.detection_method = "field_name"
        mock_field2.sample_count = 0
        mock_field2.confidence = 0.5

        result = _report_orm_to_pydantic(mock_report, [mock_field1, mock_field2])

        assert result.id == "report-123"
        assert result.table_name == "users"
        assert result.total_columns == 10
        assert result.sensitive_columns == 2
        assert result.risk_level == SensitivityLevel.HIGH
        assert len(result.fields) == 2
        assert result.fields[0].column_name == "phone"
        assert result.fields[1].column_name == "email"


class TestHealthCheck:
    """测试健康检查"""

    def test_health_check(self):
        """测试健康检查端点"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sensitive-detect"


class TestScanEndpoint:
    """测试扫描端点"""

    @pytest.mark.asyncio
    async def test_scan_table_success(self):
        """测试成功扫描表"""
        mock_db = AsyncMock()

        # Mock validate_table_exists
        with patch('services.sensitive_detect.main.validate_table_exists', return_value="`test_dataset`"):
            # Mock get_table_columns
            with patch('services.sensitive_detect.main.get_table_columns', return_value=[
                ("id", "INTEGER", "YES"),
                ("phone", "VARCHAR", "YES"),
                ("email", "VARCHAR", "YES"),
            ]):
                # Mock query result
                mock_result = MagicMock()
                mock_result.fetchall.return_value = [
                    ("13800138000",),
                    ("test@example.com",),
                ]
                mock_db.execute.return_value = mock_result

                # Mock repository
                with patch('services.sensitive_detect.main.ScanReportRepository') as mock_repo_class:
                    mock_repo = MagicMock()
                    mock_repo.create_with_fields = AsyncMock()
                    mock_repo_class.return_value = mock_repo

                    with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                        app.dependency_overrides[get_current_user] = mock_get_current_user
                        try:
                            client = TestClient(app)
                            response = client.post(
                                "/api/sensitive/scan",
                                json={"table_name": "test_dataset", "sample_size": 10}
                            )

                            assert response.status_code == 200
                            result = response.json()
                            assert result["table_name"] == "test_dataset"
                            assert "id" in result
                        finally:
                            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_scan_table_not_found(self):
        """测试表不存在"""
        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.validate_table_exists', side_effect=ValueError("Table not found")):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/sensitive/scan",
                        json={"table_name": "nonexistent"}
                    )

                    assert response.status_code == 400
                finally:
                    app.dependency_overrides.clear()


class TestClassifyEndpoint:
    """测试分类端点"""

    @pytest.mark.asyncio
    async def test_classify_data_success(self):
        """测试成功分类"""
        with patch('services.sensitive_detect.main.call_llm', new=AsyncMock(return_value='[{"type": "phone", "level": "high"}]')):
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/sensitive/classify",
                    json={
                        "data_samples": [
                            {"phone": "13800138000"},
                            {"email": "test@example.com"}
                        ],
                        "context": "用户信息"
                    }
                )

                assert response.status_code == 200
                result = response.json()
                assert "analysis" in result
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_classify_data_llm_error(self):
        """测试LLM调用失败"""
        from services.common.llm_client import LLMError

        with patch('services.sensitive_detect.main.call_llm', new=AsyncMock(side_effect=LLMError("Service unavailable"))):
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/sensitive/classify",
                    json={"data_samples": [{"value": "test"}]}
                )

                # Should return error response
                assert response.status_code in (500, 503)
            finally:
                app.dependency_overrides.clear()


class TestRulesEndpoints:
    """测试规则管理端点"""

    @pytest.mark.asyncio
    async def test_list_rules(self):
        """测试列出规则"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "rule-1"
        mock_orm.name = "手机号"
        mock_orm.pattern = "\\d{11}"
        mock_orm.sensitivity_level = "high"
        mock_orm.description = "手机号规则"
        mock_orm.enabled = True

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[mock_orm])

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules")

                    assert response.status_code == 200
                    rules = response.json()
                    assert isinstance(rules, list)
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_add_rule(self):
        """测试添加规则"""
        mock_db = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock()

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/sensitive/rules",
                        json={
                            "name": "测试规则",
                            "pattern": "\\d{4}",
                            "sensitivity_level": "medium",
                            "description": "测试",
                            "enabled": True,
                        }
                    )

                    assert response.status_code == 200
                    result = response.json()
                    assert result["name"] == "测试规则"
                    assert "id" in result
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_rule_found(self):
        """测试获取存在的规则"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "rule-1"
        mock_orm.name = "手机号"
        mock_orm.pattern = "\\d{11}"
        mock_orm.sensitivity_level = "high"
        mock_orm.description = "手机号规则"
        mock_orm.enabled = True

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_orm)

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules/rule-1")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["id"] == "rule-1"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self):
        """测试获取不存在的规则"""
        mock_db = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_rule_success(self):
        """测试删除规则"""
        mock_db = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=True)

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.delete("/api/sensitive/rules/rule-1")

                    assert response.status_code == 200
                    result = response.json()
                    assert "message" in result
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self):
        """测试删除不存在的规则"""
        mock_db = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=False)

        with patch('services.sensitive_detect.main.DetectionRuleRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.delete("/api/sensitive/rules/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestReportsEndpoints:
    """测试报告管理端点"""

    @pytest.mark.asyncio
    async def test_list_reports(self):
        """测试列出报告"""
        mock_db = AsyncMock()

        mock_report = MagicMock()
        mock_report.id = "report-1"
        mock_report.table_name = "users"
        mock_report.scan_time = datetime.now(timezone.utc)
        mock_report.total_columns = 10
        mock_report.sensitive_columns = 2
        mock_report.risk_level = "high"

        mock_repo = MagicMock()
        mock_repo.get_latest_reports = AsyncMock(return_value=[mock_report])
        mock_repo.get_fields = AsyncMock(return_value=[])

        with patch('services.sensitive_detect.main.ScanReportRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports")

                    assert response.status_code == 200
                    reports = response.json()
                    assert isinstance(reports, list)
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_found(self):
        """测试获取存在的报告"""
        mock_db = AsyncMock()

        mock_report = MagicMock()
        mock_report.id = "report-1"
        mock_report.table_name = "users"
        mock_report.scan_time = datetime.now(timezone.utc)
        mock_report.total_columns = 10
        mock_report.sensitive_columns = 2
        mock_report.risk_level = "high"

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_report)
        mock_repo.get_fields = AsyncMock(return_value=[])

        with patch('services.sensitive_detect.main.ScanReportRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports/report-1")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["id"] == "report-1"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_not_found(self):
        """测试获取不存在的报告"""
        mock_db = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch('services.sensitive_detect.main.ScanReportRepository', return_value=mock_repo):
            with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestScanAndApplyEndpoint:
    """测试扫描并应用端点"""

    @pytest.mark.asyncio
    async def test_scan_and_apply_no_sensitive_fields(self):
        """测试无敏感字段时扫描并应用"""
        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.validate_table_exists', return_value="`test_dataset`"):
            with patch('services.sensitive_detect.main.get_table_columns', return_value=[
                ("id", "INTEGER", "YES"),
                ("name", "VARCHAR", "YES"),
            ]):
                mock_result = MagicMock()
                mock_result.fetchall.return_value = []
                mock_db.execute.return_value = mock_result

                mock_repo = MagicMock()
                mock_repo.create_with_fields = AsyncMock()

                with patch('services.sensitive_detect.main.ScanReportRepository', return_value=mock_repo):
                    with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                        app.dependency_overrides[get_current_user] = mock_get_current_user
                        try:
                            client = TestClient(app)
                            response = client.post(
                                "/api/sensitive/scan-and-apply",
                                json={
                                    "table_name": "test_dataset",
                                    "auto_apply": True,
                                }
                            )

                            assert response.status_code == 200
                            result = response.json()
                            assert "report" in result
                            assert result["applied_rules"] == []
                        finally:
                            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_scan_and_apply_with_sensitive_fields(self):
        """测试有敏感字段时扫描并应用"""
        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.validate_table_exists', return_value="`test_dataset`"):
            # Mock phone column detection
            with patch('services.sensitive_detect.main.get_table_columns', return_value=[
                ("id", "INTEGER", "YES"),
                ("phone", "VARCHAR", "YES"),
            ]):
                # Mock query samples
                mock_result = MagicMock()
                mock_result.fetchall.return_value = [("13800138000",)]
                mock_db.execute.return_value = mock_result

                # Mock repository
                mock_repo = MagicMock()
                mock_repo.create_with_fields = AsyncMock()

                with patch('services.sensitive_detect.main.ScanReportRepository', return_value=mock_repo):
                    with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
                        # Mock httpx call to ShardingSphere
                        with patch('httpx.AsyncClient') as mock_httpx:
                            mock_client = AsyncMock()
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_client.put.return_value = mock_response
                            mock_client.__aenter__.return_value = mock_client
                            mock_client.__aexit__.return_value = None
                            mock_httpx.return_value = mock_client

                            app.dependency_overrides[get_current_user] = mock_get_current_user
                            try:
                                client = TestClient(app)
                                response = client.post(
                                    "/api/sensitive/scan-and-apply",
                                    json={
                                        "table_name": "test_dataset",
                                        "auto_apply": True,
                                    }
                                )

                                assert response.status_code == 200
                                result = response.json()
                                assert "report" in result
                            finally:
                                app.dependency_overrides.clear()
