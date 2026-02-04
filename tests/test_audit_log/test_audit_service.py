"""Unit tests for audit_log service main module

Tests for services/audit_log/main.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.audit_log.main import (
    _orm_to_pydantic,
    _pydantic_to_orm,
    app,
    get_current_user,
)
from services.audit_log.models import (
    AuditEvent,
    AuditQuery,
    AuditStats,
    EventType,
    ExportRequest,
    Subsystem,
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
        assert data["service"] == "audit-log"


class TestOrmToPydantic:
    """测试ORM转Pydantic"""

    def test_orm_to_pydantic(self):
        """测试ORM模型转换为Pydantic模型"""
        mock_orm = MagicMock()
        mock_orm.id = "test-id"
        mock_orm.subsystem = "portal"
        mock_orm.event_type = "api_call"
        mock_orm.user = "admin"
        mock_orm.action = "login"
        mock_orm.resource = "/api/login"
        mock_orm.status_code = 200
        mock_orm.duration_ms = 100.5
        mock_orm.ip_address = "127.0.0.1"
        mock_orm.user_agent = "test-agent"
        mock_orm.details = {"key": "value"}
        mock_orm.created_at = datetime.now(UTC)

        result = _orm_to_pydantic(mock_orm)

        assert result.id == "test-id"
        assert result.subsystem == "portal"
        assert result.action == "login"


class TestPydanticToOrm:
    """测试Pydantic转ORM"""

    def test_pydantic_to_orm(self):
        """测试Pydantic模型转换为ORM模型"""
        event = AuditEvent(
            subsystem="portal",
            event_type="api_call",
            user="admin",
            action="login",
            resource="/api/login",
            status_code=200,
            duration_ms=100.5,
        )

        result = _pydantic_to_orm(event)

        assert result.subsystem == "portal"
        assert result.action == "login"
        assert result.id is not None  # Should generate UUID

    def test_pydantic_to_orm_with_id(self):
        """测试带ID的Pydantic模型转换"""
        event = AuditEvent(
            id="custom-id",
            subsystem="portal",
            action="test",
        )

        result = _pydantic_to_orm(event)

        assert result.id == "custom-id"


class TestAuditEventModel:
    """测试AuditEvent模型"""

    def test_audit_event_default_values(self):
        """测试默认值"""
        event = AuditEvent(
            subsystem="portal",
            action="test"
        )
        assert event.subsystem == "portal"
        assert event.event_type == "api_call"
        assert event.user == "anonymous"
        assert event.action == "test"
        assert event.resource is None

    def test_audit_event_with_all_values(self):
        """测试带所有值的事件"""
        event = AuditEvent(
            subsystem="portal",
            event_type="login",
            user="admin",
            action="user_login",
            resource="/api/login",
            status_code=200,
            duration_ms=50.5,
            ip_address="127.0.0.1",
            user_agent="Mozilla",
            details={"success": True}
        )
        assert event.user == "admin"
        assert event.status_code == 200
        assert event.details["success"] is True


class TestAuditQueryModel:
    """测试AuditQuery模型"""

    def test_audit_query_default_values(self):
        """测试默认值"""
        query = AuditQuery()
        assert query.subsystem is None
        assert query.event_type is None
        assert query.page == 1
        assert query.page_size == 50

    def test_audit_query_with_filters(self):
        """测试带过滤条件的查询"""
        query = AuditQuery(
            subsystem="portal",
            event_type="login",
            user="admin",
            page=2,
            page_size=100
        )
        assert query.subsystem == "portal"
        assert query.page == 2


class TestAuditStatsModel:
    """测试AuditStats模型"""

    def test_audit_stats_creation(self):
        """测试创建统计"""
        stats = AuditStats(
            total_events=1000,
            events_by_subsystem={"portal": 500, "nl2sql": 500},
            events_by_type={"api_call": 800, "login": 200},
            events_by_user={"admin": 300, "viewer": 700}
        )
        assert stats.total_events == 1000
        assert len(stats.events_by_subsystem) == 2


class TestExportRequestModel:
    """测试ExportRequest模型"""

    def test_export_request_default_csv(self):
        """测试默认CSV格式"""
        req = ExportRequest(query=AuditQuery())
        assert req.format == "csv"

    def test_export_request_json(self):
        """测试JSON格式"""
        req = ExportRequest(
            format="json",
            query=AuditQuery(subsystem="portal")
        )
        assert req.format == "json"


class TestRecordEventEndpoint:
    """测试记录事件端点"""

    @pytest.mark.asyncio
    async def test_record_event_success(self):
        """测试成功记录事件"""
        mock_db = AsyncMock()
        mock_session = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock()

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_session):
                client = TestClient(app)
                response = client.post(
                    "/api/audit/log",
                    json={
                        "subsystem": "portal",
                        "action": "test_action",
                        "user": "test_user"
                    }
                )

                assert response.status_code == 200
                result = response.json()
                assert result["action"] == "test_action"
                assert "id" in result


class TestQueryLogsEndpoint:
    """测试查询日志端点"""

    @pytest.mark.asyncio
    async def test_query_logs_success(self):
        """测试成功查询日志"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "test-id"
        mock_orm.subsystem = "portal"
        mock_orm.event_type = "api_call"
        mock_orm.user = "admin"
        mock_orm.action = "login"
        mock_orm.resource = None
        mock_orm.status_code = None
        mock_orm.duration_ms = None
        mock_orm.ip_address = None
        mock_orm.user_agent = None
        mock_orm.details = None
        mock_orm.created_at = datetime.now(UTC)

        mock_repo = MagicMock()
        mock_repo.query = AsyncMock(return_value=[mock_orm])

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/audit/logs")

                    assert response.status_code == 200
                    result = response.json()
                    assert isinstance(result, list)
                    assert len(result) >= 0
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_logs_with_filters(self):
        """测试带过滤条件查询日志"""
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.query = AsyncMock(return_value=[])

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get(
                        "/api/audit/logs?subsystem=portal&event_type=login&page=1&page_size=10"
                    )

                    assert response.status_code == 200
                finally:
                    app.dependency_overrides.clear()


class TestGetLogEndpoint:
    """测试获取单条日志端点"""

    @pytest.mark.asyncio
    async def test_get_log_found(self):
        """测试找到日志"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "log-123"
        mock_orm.subsystem = "portal"
        mock_orm.event_type = "api_call"
        mock_orm.user = "admin"
        mock_orm.action = "test"
        mock_orm.resource = None
        mock_orm.status_code = None
        mock_orm.duration_ms = None
        mock_orm.ip_address = None
        mock_orm.user_agent = None
        mock_orm.details = None
        mock_orm.created_at = datetime.now(UTC)

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_orm)

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/audit/logs/log-123")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["id"] == "log-123"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_log_not_found(self):
        """测试日志不存在"""
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/audit/logs/nonexistent")

                    assert response.status_code == 404
                finally:
                    app.dependency_overrides.clear()


class TestGetStatsEndpoint:
    """测试获取统计端点"""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """测试成功获取统计"""
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_stats = AsyncMock(return_value={
            "total_events": 1000,
            "events_by_subsystem": {"portal": 500},
            "events_by_type": {"api_call": 800},
            "events_by_user": {"admin": 300}
        })

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.get("/api/audit/stats")

                    assert response.status_code == 200
                    result = response.json()
                    assert result["total_events"] == 1000
                finally:
                    app.dependency_overrides.clear()


class TestExportLogsEndpoint:
    """测试导出日志端点"""

    @pytest.mark.asyncio
    async def test_export_csv(self):
        """测试导出CSV格式"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "test-id"
        mock_orm.subsystem = "portal"
        mock_orm.event_type = "api_call"
        mock_orm.user = "admin"
        mock_orm.action = "test"
        mock_orm.status_code = 200
        mock_orm.created_at = datetime.now(UTC)
        # Set other attributes to None explicitly
        mock_orm.resource = None
        mock_orm.duration_ms = None
        mock_orm.ip_address = None
        mock_orm.user_agent = None
        mock_orm.details = None

        mock_repo = MagicMock()
        mock_repo.export = AsyncMock(return_value=[mock_orm])

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/audit/export",
                        json={
                            "format": "csv",
                            "query": {}
                        }
                    )

                    assert response.status_code == 200
                    assert "text/csv" in response.headers["content-type"]
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_json(self):
        """测试导出JSON格式"""
        mock_db = AsyncMock()

        mock_orm = MagicMock()
        mock_orm.id = "test-id"
        mock_orm.subsystem = "portal"
        mock_orm.event_type = "api_call"
        mock_orm.user = "admin"
        mock_orm.action = "test"
        mock_orm.status_code = None
        mock_orm.created_at = datetime.now(UTC)
        mock_orm.resource = None
        mock_orm.duration_ms = None
        mock_orm.ip_address = None
        mock_orm.user_agent = None
        mock_orm.details = None

        mock_repo = MagicMock()
        mock_repo.export = AsyncMock(return_value=[mock_orm])

        with patch('services.audit_log.main.AuditRepository', return_value=mock_repo):
            with patch('services.audit_log.main.get_db', return_value=mock_db):
                app.dependency_overrides[get_current_user] = mock_get_current_user
                try:
                    client = TestClient(app)
                    response = client.post(
                        "/api/audit/export",
                        json={
                            "format": "json",
                            "query": {}
                        }
                    )

                    assert response.status_code == 200
                    assert "application/json" in response.headers["content-type"]
                finally:
                    app.dependency_overrides.clear()


class TestEventTypeEnum:
    """测试EventType枚举"""

    def test_event_type_values(self):
        """测试事件类型值"""
        assert EventType.API_CALL == "api_call"
        assert EventType.LOGIN == "login"
        assert EventType.LOGOUT == "logout"
        assert EventType.DATA_ACCESS == "data_access"
        assert EventType.DATA_MODIFY == "data_modify"
        assert EventType.CONFIG_CHANGE == "config_change"
        assert EventType.TASK_EXECUTE == "task_execute"
        assert EventType.EXPORT == "export"
        assert EventType.ADMIN == "admin"


class TestSubsystemEnum:
    """测试Subsystem枚举"""

    def test_subsystem_values(self):
        """测试子系统值"""
        assert Subsystem.PORTAL == "portal"
        assert Subsystem.NL2SQL == "nl2sql"
        assert Subsystem.AI_CLEANING == "ai-cleaning"
        assert Subsystem.METADATA_SYNC == "metadata-sync"
        assert Subsystem.DATA_API == "data-api"
        assert Subsystem.SENSITIVE_DETECT == "sensitive-detect"
        assert Subsystem.AUDIT_LOG == "audit-log"
