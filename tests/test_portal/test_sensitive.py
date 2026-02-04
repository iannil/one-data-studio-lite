"""Unit tests for portal sensitive router

Tests for services/portal/routers/sensitive.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.api_response import ErrorCode
from services.common.auth import TokenPayload
from services.portal.routers.sensitive import (
    ClassifyRequest,
    DetectionRuleBase,
    ScanAndApplyRequest,
    ScanRequest,
    add_rule_v1,
    classify_v1,
    delete_rule_v1,
    get_report_v1,
    get_reports_v1,
    get_rule_v1,
    get_rules_v1,
    router,
    scan_and_apply_v1,
    scan_v1,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/sensitive"


class TestScanRequest:
    """测试扫描请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = ScanRequest(table_name="test_table")
        assert req.table_name == "test_table"
        assert req.database is None
        assert req.sample_size == 100

    def test_with_values(self):
        """测试带值的请求"""
        req = ScanRequest(
            table_name="test_table",
            database="test_db",
            sample_size=500
        )
        assert req.table_name == "test_table"
        assert req.database == "test_db"
        assert req.sample_size == 500


class TestClassifyRequest:
    """测试分类请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = ClassifyRequest(data_samples=["data1", "data2"])
        assert req.data_samples == ["data1", "data2"]
        assert req.context is None

    def test_with_context(self):
        """测试带上下文的请求"""
        req = ClassifyRequest(
            data_samples=["phone", "email"],
            context="user contact information"
        )
        assert req.context == "user contact information"


class TestDetectionRuleBase:
    """测试检测规则模型"""

    def test_create_rule(self):
        """测试创建规则"""
        rule = DetectionRuleBase(
            name="phone_rule",
            pattern=r"\d{11}",
            description="Chinese phone number",
            sensitive_type="PHONE"
        )
        assert rule.name == "phone_rule"
        assert rule.pattern == r"\d{11}"
        assert rule.description == "Chinese phone number"
        assert rule.sensitive_type == "PHONE"

    def test_rule_without_description(self):
        """测试不带描述的规则"""
        rule = DetectionRuleBase(
            name="email_rule",
            pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            sensitive_type="EMAIL"
        )
        assert rule.description is None


class TestScanAndApplyRequest:
    """测试扫描并应用请求模型"""

    def test_default_values(self):
        """测试默认值"""
        req = ScanAndApplyRequest(table_name="test_table")
        assert req.table_name == "test_table"
        assert req.database is None
        assert req.sample_size == 100
        assert req.auto_apply is False

    def test_with_auto_apply(self):
        """测试自动应用"""
        req = ScanAndApplyRequest(
            table_name="test_table",
            database="test_db",
            sample_size=200,
            auto_apply=True
        )
        assert req.auto_apply is True


class TestScanV1:
    """测试扫描敏感数据"""

    @pytest.mark.asyncio
    async def test_scan_success(self):
        """测试成功扫描"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "table_name": "users",
            "sensitive_columns": [
                {"column": "phone", "type": "PHONE", "confidence": 0.95},
                {"column": "email", "type": "EMAIL", "confidence": 0.98}
            ]
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = ScanRequest(table_name="users", database="test_db")
            result = await scan_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "sensitive_columns" in result.data

    @pytest.mark.asyncio
    async def test_scan_service_error(self):
        """测试服务错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = ScanRequest(table_name="users")
            result = await scan_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.EXTERNAL_SERVICE_ERROR


class TestClassifyV1:
    """测试 LLM 分类"""

    @pytest.mark.asyncio
    async def test_classify_success(self):
        """测试成功分类"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "classifications": [
                {"data": "13800138000", "type": "PHONE", "confidence": 0.99},
                {"data": "test@example.com", "type": "EMAIL", "confidence": 0.97}
            ]
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = ClassifyRequest(data_samples=["13800138000", "test@example.com"])
            result = await classify_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "classifications" in result.data


class TestGetRulesV1:
    """测试获取检测规则列表"""

    @pytest.mark.asyncio
    async def test_get_rules_success(self):
        """测试成功获取规则列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rules": [
                {"id": "1", "name": "phone_rule", "sensitive_type": "PHONE"},
                {"id": "2", "name": "email_rule", "sensitive_type": "EMAIL"}
            ],
            "total": 2
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_rules_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "rules" in result.data


class TestGetRuleV1:
    """测试获取单个检测规则"""

    @pytest.mark.asyncio
    async def test_get_rule_success(self):
        """测试成功获取规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "1",
            "name": "phone_rule",
            "pattern": r"\d{11}",
            "sensitive_type": "PHONE"
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_rule_v1(rule_id="1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["name"] == "phone_rule"


class TestAddRuleV1:
    """测试添加检测规则"""

    @pytest.mark.asyncio
    async def test_add_rule_success(self):
        """测试成功添加规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "3",
            "name": "id_card_rule",
            "pattern": r"\d{18}",
            "sensitive_type": "ID_CARD"
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            rule = DetectionRuleBase(
                name="id_card_rule",
                pattern=r"\d{18}",
                sensitive_type="ID_CARD"
            )
            result = await add_rule_v1(rule=rule, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["id"] == "3"


class TestDeleteRuleV1:
    """测试删除检测规则"""

    @pytest.mark.asyncio
    async def test_delete_rule_success(self):
        """测试成功删除规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.delete.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await delete_rule_v1(rule_id="3", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetReportsV1:
    """测试获取扫描报告列表"""

    @pytest.mark.asyncio
    async def test_get_reports_success(self):
        """测试成功获取报告列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "reports": [
                {"id": "r1", "table_name": "users", "scan_time": "2023-01-01"},
                {"id": "r2", "table_name": "orders", "scan_time": "2023-01-02"}
            ],
            "total": 2
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_reports_v1(page=1, page_size=20, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["total"] == 2


class TestGetReportV1:
    """测试获取单个扫描报告"""

    @pytest.mark.asyncio
    async def test_get_report_success(self):
        """测试成功获取报告"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "r1",
            "table_name": "users",
            "sensitive_columns": [
                {"column": "phone", "type": "PHONE", "count": 1000}
            ],
            "scan_time": "2023-01-01T00:00:00"
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_report_v1(report_id="r1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["table_name"] == "users"


class TestScanAndApplyV1:
    """测试扫描并自动应用脱敏规则"""

    @pytest.mark.asyncio
    async def test_scan_and_apply_success(self):
        """测试成功扫描并应用"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "table_name": "users",
            "sensitive_columns": [
                {"column": "phone", "type": "PHONE"}
            ],
            "masking_rules_applied": [
                {"column": "phone", "rule": "mask_middle"}
            ]
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = ScanAndApplyRequest(
                table_name="users",
                auto_apply=True
            )
            result = await scan_and_apply_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "masking_rules_applied" in result.data

    @pytest.mark.asyncio
    async def test_scan_and_apply_without_auto_apply(self):
        """测试扫描但不自动应用"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "table_name": "users",
            "sensitive_columns": [
                {"column": "phone", "type": "PHONE"}
            ],
            "auto_applied": False
        }

        with patch('services.portal.routers.sensitive.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            req = ScanAndApplyRequest(table_name="users", auto_apply=False)
            result = await scan_and_apply_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
