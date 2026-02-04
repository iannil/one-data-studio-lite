"""Unit tests for sensitive_detect main module

Tests for services/sensitive_detect/main.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.common.auth import TokenPayload
from services.common.orm_models import DetectionRuleORM, ScanReportORM, SensitiveFieldORM
from services.sensitive_detect.main import (
    _field_orm_to_pydantic,
    _field_to_orm,
    _level_order,
    _report_orm_to_pydantic,
    _rule_orm_to_pydantic,
    _rule_pydantic_to_orm,
    app,
    get_current_user,
)
from services.sensitive_detect.models import (
    DetectionRule,
    ScanReport,
    SensitiveField,
    SensitivityLevel,
)

# Mock user for testing
MOCK_USER = TokenPayload(
    sub="test",
    username="test",
    role="admin",
    exp=datetime(2099, 12, 31),
    iat=datetime(2023, 1, 1)
)


async def mock_get_current_user():
    return MOCK_USER


class TestLevelOrder:
    """测试敏感级别排序"""

    def test_level_order_low(self):
        """测试 LOW 级别"""
        assert _level_order(SensitivityLevel.LOW) == 0

    def test_level_order_medium(self):
        """测试 MEDIUM 级别"""
        assert _level_order(SensitivityLevel.MEDIUM) == 1

    def test_level_order_high(self):
        """测试 HIGH 级别"""
        assert _level_order(SensitivityLevel.HIGH) == 2

    def test_level_order_critical(self):
        """测试 CRITICAL 级别"""
        assert _level_order(SensitivityLevel.CRITICAL) == 3


class TestRuleOrmToPydantic:
    """测试 ORM 转 Pydantic 规则"""

    def test_rule_orm_to_pydantic_full(self):
        """测试完整转换"""
        orm = DetectionRuleORM(
            id="rule-123",
            name="phone_rule",
            pattern=r"\d{11}",
            sensitivity_level="high",
            description="Phone number detection",
            enabled=True,
        )

        result = _rule_orm_to_pydantic(orm)

        assert result.id == "rule-123"
        assert result.name == "phone_rule"
        assert result.pattern == r"\d{11}"
        assert result.sensitivity_level == SensitivityLevel.HIGH
        assert result.description == "Phone number detection"
        assert result.enabled is True

    def test_rule_orm_to_pydantic_no_description(self):
        """测试无描述的转换"""
        orm = DetectionRuleORM(
            id="rule-456",
            name="email_rule",
            pattern=r"[a-z]+@[a-z]+\.[a-z]+",
            sensitivity_level="medium",
            description=None,
            enabled=False,
        )

        result = _rule_orm_to_pydantic(orm)

        assert result.description == ""
        assert result.enabled is False


class TestRulePydanticToOrm:
    """测试 Pydantic 转 ORM 规则"""

    def test_rule_pydantic_to_orm_with_id(self):
        """测试带 ID 的转换"""
        rule = DetectionRule(
            id="rule-789",
            name="id_card_rule",
            pattern=r"\d{18}",
            sensitivity_level=SensitivityLevel.CRITICAL,
            description="ID card detection",
            enabled=True,
        )

        result = _rule_pydantic_to_orm(rule)

        assert result.id == "rule-789"
        assert result.name == "id_card_rule"
        assert result.sensitivity_level == "critical"

    def test_rule_pydantic_to_orm_without_id(self):
        """测试无 ID 的转换（生成新 ID）"""
        rule = DetectionRule(
            id=None,
            name="test_rule",
            pattern="test",
            sensitivity_level=SensitivityLevel.LOW,
            description="Test",
            enabled=True,
        )

        result = _rule_pydantic_to_orm(rule)

        assert result.id is not None  # Should generate UUID
        assert len(result.id) > 0


class TestFieldOrmToPydantic:
    """测试字段 ORM 转 Pydantic"""

    def test_field_orm_to_pydantic(self):
        """测试字段转换"""
        orm = SensitiveFieldORM(
            report_id="report-123",
            column_name="phone",
            sensitivity_level="high",
            detected_types=["phone", "regex"],
            detection_method="field_name+regex",
            sample_count=50,
            confidence=0.85,
        )

        result = _field_orm_to_pydantic(orm)

        assert result.column_name == "phone"
        assert result.sensitivity_level == SensitivityLevel.HIGH
        assert result.detected_types == ["phone", "regex"]
        assert result.detection_method == "field_name+regex"
        assert result.sample_count == 50
        assert result.confidence == 0.85


class TestFieldToOrm:
    """测试字段 Pydantic 转 ORM"""

    def test_field_to_orm(self):
        """测试字段转换"""
        field = SensitiveField(
            column_name="email",
            sensitivity_level=SensitivityLevel.MEDIUM,
            detected_types=["email"],
            detection_method="regex",
            sample_count=10,
            confidence=0.5,
        )

        result = _field_to_orm(field, "report-456")

        assert result.report_id == "report-456"
        assert result.column_name == "email"
        assert result.sensitivity_level == "medium"


class TestReportOrmToPydantic:
    """测试报告 ORM 转 Pydantic"""

    def test_report_orm_to_pydantic(self):
        """测试报告转换"""
        report_orm = ScanReportORM(
            id="report-789",
            table_name="users",
            database_name="test_db",
            scan_time=datetime.now(UTC),
            total_columns=10,
            sensitive_columns=2,
            risk_level="high",
            scanned_by="user123",
        )

        field_orm1 = SensitiveFieldORM(
            report_id="report-789",
            column_name="phone",
            sensitivity_level="high",
            detected_types=["phone"],
            detection_method="field_name",
            sample_count=100,
            confidence=1.0,
        )

        field_orm2 = SensitiveFieldORM(
            report_id="report-789",
            column_name="email",
            sensitivity_level="medium",
            detected_types=["email"],
            detection_method="regex",
            sample_count=50,
            confidence=0.5,
        )

        result = _report_orm_to_pydantic(report_orm, [field_orm1, field_orm2])

        assert result.id == "report-789"
        assert result.table_name == "users"
        assert result.total_columns == 10
        assert result.sensitive_columns == 2
        assert result.risk_level == SensitivityLevel.HIGH
        assert len(result.fields) == 2
        assert result.fields[0].column_name == "phone"
        assert result.fields[1].column_name == "email"


class TestScanAndApplyRequest:
    """测试扫描并应用请求模型"""

    def test_default_values(self):
        """测试默认值"""
        # Import the class from the module where it's defined
        from services.sensitive_detect import main

        req = main.ScanAndApplyRequest(table_name="users")
        assert req.table_name == "users"
        assert req.database is None
        assert req.sample_size == 100
        assert req.auto_apply is True

    def test_with_all_values(self):
        """测试带所有值的请求"""
        from services.sensitive_detect import main

        req = main.ScanAndApplyRequest(
            table_name="users",
            database="test_db",
            sample_size=200,
            auto_apply=False
        )
        assert req.database == "test_db"
        assert req.sample_size == 200
        assert req.auto_apply is False


class TestScanAndApplyResponse:
    """测试扫描并应用响应模型"""

    def test_create_response(self):
        """测试创建响应"""
        from services.sensitive_detect import main

        report = ScanReport(
            id="report-123",
            table_name="users",
            scan_time=datetime.now(UTC),
            total_columns=5,
            sensitive_columns=1,
            fields=[],
            risk_level=SensitivityLevel.MEDIUM,
        )

        response = main.ScanAndApplyResponse(
            report=report,
            applied_rules=[{"column": "phone"}],
            skipped_rules=[]
        )

        assert response.report.id == "report-123"
        assert len(response.applied_rules) == 1
        assert len(response.skipped_rules) == 0


class TestHealthCheck:
    """测试健康检查端点"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sensitive-detect"


class TestListRules:
    """测试获取规则列表端点"""

    @pytest.mark.asyncio
    async def test_list_rules_success(self):
        """测试成功获取规则列表"""

        mock_db = AsyncMock()

        mock_rule1 = DetectionRuleORM(
            id="rule-1",
            name="phone_rule",
            pattern=r"\d{11}",
            sensitivity_level="high",
            description="Phone",
            enabled=True,
        )

        mock_rule2 = DetectionRuleORM(
            id="rule-2",
            name="email_rule",
            pattern=r"[a-z]+@[a-z]+",
            sensitivity_level="medium",
            description="Email",
            enabled=True,
        )

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_all.return_value = [mock_rule1, mock_rule2]
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules")

                    assert response.status_code == 200
                    rules = response.json()
                    assert len(rules) == 2
                    assert rules[0]["name"] == "phone_rule"
                    assert rules[1]["name"] == "email_rule"
                finally:
                    app.dependency_overrides.clear()


class TestGetRule:
    """测试获取单个规则端点"""

    @pytest.mark.asyncio
    async def test_get_rule_success(self):
        """测试成功获取规则"""

        mock_db = AsyncMock()

        mock_rule = DetectionRuleORM(
            id="rule-123",
            name="test_rule",
            pattern="test",
            sensitivity_level="low",
            description="Test",
            enabled=True,
        )

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_rule
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules/rule-123")

                    assert response.status_code == 200
                    rule = response.json()
                    assert rule["id"] == "rule-123"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self):
        """测试规则不存在"""

        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/rules/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestAddRule:
    """测试添加规则端点"""

    @pytest.mark.asyncio
    async def test_add_rule_success(self):
        """测试成功添加规则"""

        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.create = AsyncMock()
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    rule_data = {
                        "name": "new_rule",
                        "pattern": r"\d+",
                        "sensitivity_level": "medium",
                        "description": "Numbers",
                        "enabled": True
                    }
                    response = client.post("/api/sensitive/rules", json=rule_data)

                    assert response.status_code == 200
                    result = response.json()
                    assert result["name"] == "new_rule"
                    assert "id" in result
                finally:
                    app.dependency_overrides.clear()


class TestDeleteRule:
    """测试删除规则端点"""

    @pytest.mark.asyncio
    async def test_delete_rule_success(self):
        """测试成功删除规则"""

        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.delete.return_value = True
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.delete("/api/sensitive/rules/rule-123")

                    assert response.status_code == 200
                    result = response.json()
                    assert "已删除" in result["message"]
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self):
        """测试删除不存在的规则"""

        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.DetectionRuleRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.delete.return_value = False
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.delete("/api/sensitive/rules/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestListReports:
    """测试获取报告列表端点"""

    @pytest.mark.asyncio
    async def test_list_reports_success(self):
        """测试成功获取报告列表"""

        mock_db = AsyncMock()

        mock_report = ScanReportORM(
            id="report-123",
            table_name="users",
            database_name="test_db",
            scan_time=datetime.now(UTC),
            total_columns=5,
            sensitive_columns=1,
            risk_level="medium",
            scanned_by="user123",
        )

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.ScanReportRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_latest_reports.return_value = [mock_report]
                mock_repo.get_fields.return_value = []
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports?page=1&page_size=20")

                    assert response.status_code == 200
                    reports = response.json()
                    assert len(reports) >= 0
                finally:
                    app.dependency_overrides.clear()


class TestGetReport:
    """测试获取单个报告端点"""

    @pytest.mark.asyncio
    async def test_get_report_success(self):
        """测试成功获取报告"""

        mock_db = AsyncMock()

        mock_report = ScanReportORM(
            id="report-123",
            table_name="users",
            database_name="test_db",
            scan_time=datetime.now(UTC),
            total_columns=5,
            sensitive_columns=1,
            risk_level="medium",
            scanned_by="user123",
        )

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.ScanReportRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_report
                mock_repo.get_fields.return_value = []
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports/report-123")

                    assert response.status_code == 200
                    report = response.json()
                    assert report["id"] == "report-123"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_not_found(self):
        """测试报告不存在"""

        mock_db = AsyncMock()

        with patch('services.sensitive_detect.main.get_db', return_value=mock_db):
            with patch('services.sensitive_detect.main.ScanReportRepository') as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None
                mock_repo_cls.return_value = mock_repo

                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/sensitive/reports/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()
