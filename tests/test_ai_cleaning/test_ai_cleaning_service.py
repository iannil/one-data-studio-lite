"""Unit tests for ai_cleaning service main module

Tests for services/ai_cleaning/main.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from services.ai_cleaning.main import (
    app,
    _call_llm_service,
    _parse_llm_json_response,
    get_current_user,
)
from services.ai_cleaning.models import (
    AnalyzeRequest,
    DataQualityReport,
    QualityIssue,
    QualityIssueType,
    CleaningRule,
    CleaningRecommendation,
    GenerateConfigRequest,
    SeaTunnelTransformConfig,
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


class TestHealthCheck:
    """测试健康检查端点"""

    def test_health_check(self):
        """测试健康检查"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-cleaning"


class TestCallLlmService:
    """测试LLM服务调用"""

    @pytest.mark.asyncio
    async def test_call_llm_service_success(self):
        """测试成功调用LLM"""
        with patch('services.ai_cleaning.main.call_llm') as mock_call:
            mock_call.return_value = "AI response"

            result = await _call_llm_service("test prompt")

            assert result == "AI response"

    @pytest.mark.asyncio
    async def test_call_llm_service_error(self):
        """测试LLM调用失败"""
        from services.common.llm_client import LLMError

        with patch('services.ai_cleaning.main.call_llm') as mock_call:
            mock_call.side_effect = LLMError("Service unavailable", code=503)

            from services.common.exceptions import AppException
            with pytest.raises(AppException) as exc_info:
                await _call_llm_service("test prompt")

            assert "LLM 调用失败" in str(exc_info.value)


class TestParseLlmJsonResponse:
    """测试LLM JSON响应解析"""

    def test_parse_valid_json(self):
        """测试解析有效JSON"""
        response = '[{"name": "rule1", "type": "filter"}]'
        result = _parse_llm_json_response(response)

        assert len(result) == 1
        assert result[0]["name"] == "rule1"

    def test_parse_json_in_markdown(self):
        """测试解析Markdown中的JSON"""
        response = '''```json
[{"name": "rule1", "type": "filter"}]
```'''
        result = _parse_llm_json_response(response)

        assert len(result) == 1
        assert result[0]["name"] == "rule1"

    def test_parse_json_with_code_block(self):
        """测试解析代码块中的JSON"""
        response = '''```
[{"name": "rule1"}]
```'''
        result = _parse_llm_json_response(response)

        assert len(result) == 1

    def test_parse_invalid_json(self):
        """测试解析无效JSON"""
        response = 'not valid json'
        result = _parse_llm_json_response(response, context="test")

        assert result == []

    def test_parse_malformed_json(self):
        """测试解析格式错误的JSON"""
        response = '```[{"name": "rule1"}```'
        result = _parse_llm_json_response(response)

        assert result == []


class TestAnalyzeRequest:
    """测试分析请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = AnalyzeRequest(table_name="users")
        assert req.table_name == "users"
        assert req.database is None
        assert req.sample_size == 1000

    def test_with_all_values(self):
        """测试带所有值的请求"""
        req = AnalyzeRequest(
            table_name="orders",
            database="test_db",
            sample_size=500
        )
        assert req.database == "test_db"
        assert req.sample_size == 500


class TestQualityIssue:
    """测试质量问题模型"""

    def test_quality_issue_creation(self):
        """测试创建质量问题"""
        issue = QualityIssue(
            column="email",
            issue_type=QualityIssueType.FORMAT_ERROR,
            description="Invalid email format",
            affected_rows=10,
            severity="high",
            sample_values=["test@", "invalid"]
        )
        assert issue.column == "email"
        assert issue.severity == "high"


class TestDataQualityReport:
    """测试数据质量报告模型"""

    def test_report_creation(self):
        """测试创建报告"""
        report = DataQualityReport(
            table_name="users",
            total_rows=1000,
            analyzed_rows=1000,
            issues=[],
            quality_score=95.0
        )
        assert report.table_name == "users"
        assert report.quality_score == 95.0


class TestCleaningRule:
    """测试清洗规则模型"""

    def test_rule_creation(self):
        """测试创建规则"""
        rule = CleaningRule(
            rule_id="rule-123",
            name="过滤空值",
            description="过滤email字段的空值",
            target_column="email",
            rule_type="filter",
            config={"operator": "IS_NOT_NULL"}
        )
        assert rule.rule_id == "rule-123"
        assert rule.rule_type == "filter"


class TestCleaningRecommendation:
    """测试清洗规则推荐模型"""

    def test_recommendation_creation(self):
        """测试创建推荐"""
        rule = CleaningRule(
            rule_id="rule-1",
            name="测试规则",
            description="测试",
            target_column="col1",
            rule_type="filter",
            config={}
        )
        rec = CleaningRecommendation(
            rules=[rule],
            explanation="推荐1条规则"
        )
        assert len(rec.rules) == 1
        assert rec.explanation == "推荐1条规则"


class TestSeaTunnelTransformConfig:
    """测试SeaTunnel配置模型"""

    def test_config_creation(self):
        """测试创建配置"""
        config = SeaTunnelTransformConfig(
            plugin_name="Filter",
            source_table_name="users",
            result_table_name="users_cleaned",
            config={"fields": ["email"]}
        )
        assert config.plugin_name == "Filter"
        assert config.source_table_name == "users"


class TestGenerateConfigRequest:
    """测试生成配置请求模型"""

    def test_request_with_output_table(self):
        """测试指定输出表"""
        req = GenerateConfigRequest(
            table_name="users",
            rules=[],
            output_table="users_cleaned"
        )
        assert req.output_table == "users_cleaned"

    def test_request_without_output_table(self):
        """测试不指定输出表"""
        req = GenerateConfigRequest(
            table_name="users",
            rules=[]
        )
        assert req.output_table is None


class TestAnalyzeEndpoint:
    """测试分析端点"""

    @pytest.mark.asyncio
    async def test_analyze_table_success(self):
        """测试成功分析表"""
        mock_db = AsyncMock()

        # Mock validate_table_exists
        with patch('services.ai_cleaning.main.validate_table_exists', return_value="test_dataset"):
            # Mock count query
            count_result = MagicMock()
            count_result.scalar.return_value = 100
            mock_db.execute.return_value = count_result

            # Mock get_table_columns - use a table that exists
            with patch('services.ai_cleaning.main.get_table_columns', return_value=[
                ("id", "INTEGER", True),
                ("title", "TEXT", True),
            ]):
                with patch('services.ai_cleaning.main.get_db', return_value=mock_db):
                    app.dependency_overrides[get_current_user] = mock_get_current_user
                    try:
                        client = TestClient(app)
                        response = client.post(
                            "/api/cleaning/analyze",
                            json={"table_name": "test_dataset"}
                        )

                        assert response.status_code == 200
                        result = response.json()
                        assert result["table_name"] == "test_dataset"
                    finally:
                        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_analyze_table_not_found(self):
        """测试表不存在"""
        mock_db = AsyncMock()

        with patch('services.ai_cleaning.main.validate_table_exists', side_effect=ValueError("Table not found")):
            with patch('services.ai_cleaning.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/cleaning/analyze",
                        json={"table_name": "nonexistent"}
                    )

                    assert response.status_code in (400, 404)
                finally:
                    app.dependency_overrides.clear()


class TestRecommendEndpoint:
    """测试推荐规则端点"""

    @pytest.mark.asyncio
    async def test_recommend_with_no_issues(self):
        """测试无问题时推荐"""
        mock_db = AsyncMock()

        with patch('services.ai_cleaning.main.validate_table_exists', return_value="test_dataset"):
            count_result = MagicMock()
            count_result.scalar.return_value = 100
            mock_db.execute.return_value = count_result

            with patch('services.ai_cleaning.main.get_table_columns', return_value=[]):
                with patch('services.ai_cleaning.main.get_db', return_value=mock_db):
                    app.dependency_overrides[get_current_user] = mock_get_current_user
                    try:
                        client = TestClient(app)
                        response = client.post(
                            "/api/cleaning/recommend",
                            json={"table_name": "test_dataset"}
                        )

                        assert response.status_code == 200
                        result = response.json()
                        assert "数据质量良好" in result["explanation"]
                    finally:
                        app.dependency_overrides.clear()


class TestGenerateConfigEndpoint:
    """测试生成配置端点"""

    def test_generate_filter_config(self):
        """测试生成过滤配置"""
        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            response = client.post(
                "/api/cleaning/generate-config",
                json={
                    "table_name": "users",
                    "rules": [{
                        "rule_id": "rule-1",
                        "name": "过滤空值",
                        "description": "过滤空值",
                        "target_column": "email",
                        "rule_type": "filter",
                        "config": {"operator": "IS_NOT_NULL"}
                    }],
                    "output_table": "users_cleaned"
                }
            )

            assert response.status_code == 200
            configs = response.json()
            assert len(configs) == 1
            assert configs[0]["plugin_name"] == "Filter"
        finally:
            app.dependency_overrides.clear()

    def test_generate_replace_config(self):
        """测试生成替换配置"""
        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            response = client.post(
                "/api/cleaning/generate-config",
                json={
                    "table_name": "users",
                    "rules": [{
                        "rule_id": "rule-1",
                        "name": "替换异常值",
                        "description": "替换",
                        "target_column": "status",
                        "rule_type": "replace",
                        "config": {"old_value": "unknown", "new_value": "active"}
                    }]
                }
            )

            assert response.status_code == 200
            configs = response.json()
            assert len(configs) == 1
            assert configs[0]["plugin_name"] == "Replace"
        finally:
            app.dependency_overrides.clear()

    def test_generate_deduplicate_config(self):
        """测试生成去重配置"""
        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            response = client.post(
                "/api/cleaning/generate-config",
                json={
                    "table_name": "users",
                    "rules": [{
                        "rule_id": "rule-1",
                        "name": "去重",
                        "description": "去除重复",
                        "target_column": "email",
                        "rule_type": "deduplicate",
                        "config": {}
                    }]
                }
            )

            assert response.status_code == 200
            configs = response.json()
            assert len(configs) == 1
            assert configs[0]["plugin_name"] == "SQL"
        finally:
            app.dependency_overrides.clear()


class TestListRuleTemplates:
    """测试列出规则模板"""

    def test_list_rule_templates(self):
        """测试获取规则模板列表"""
        client = TestClient(app)
        response = client.get("/api/cleaning/rules")

        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) > 0

        # Check for expected rule types
        rule_types = [t["type"] for t in templates]
        assert "filter" in rule_types
        assert "replace" in rule_types
        assert "fill" in rule_types
        assert "deduplicate" in rule_types
