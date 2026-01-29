"""
TC-ADM-05: 审计管理测试
测试审计日志的记录、查询、统计和导出
"""

import pytest
from httpx import AsyncClient


class TestAuditManagement:
    """TC-ADM-05: 审计管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_adm_05_01_record_audit_event(self, audit_log_client: AsyncClient):
        """TC-ADM-05-01: 内部服务记录审计事件"""
        response = await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test-system",
                "event_type": "manual_test",
                "user": "admin",
                "action": "测试审计日志记录",
                "resource": "/test",
                "status_code": 200
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "created_at" in data
        assert data["subsystem"] == "test-system"
        assert data["event_type"] == "manual_test"
        assert data["user"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_02_record_detailed_audit_event(
        self, audit_log_client: AsyncClient
    ):
        """TC-ADM-05-02: 记录带有详细信息的审计事件"""
        response = await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "portal",
                "event_type": "login",
                "user": "admin",
                "action": "用户登录",
                "resource": "/auth/login",
                "status_code": 200,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "duration_ms": 150.5,
                "details": {"login_method": "password"}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ip_address"] == "192.168.1.100"
        assert data["user_agent"] == "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_adm_05_03_query_audit_logs(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-03: 查询审计日志列表"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 应该返回列表
        assert isinstance(data, list)

        # 如果有数据，验证记录结构
        if len(data) > 0:
            record = data[0]
            assert "id" in record
            assert "subsystem" in record
            assert "event_type" in record
            assert "user" in record
            assert "action" in record
            assert "status_code" in record
            assert "created_at" in record

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_04_filter_by_subsystem(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-04: 按子系统筛选审计日志"""
        # 先创建一条测试数据
        await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "portal",
                "event_type": "test",
                "user": "admin",
                "action": "test action",
                "resource": "/test",
                "status_code": 200
            }
        )

        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"subsystem": "portal"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 所有返回的记录应该都是 portal 子系统的
        for record in data:
            assert record["subsystem"] == "portal"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_05_filter_by_event_type(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-05: 按事件类型筛选审计日志"""
        # 先创建一条测试数据
        await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test",
                "event_type": "api_call",
                "user": "admin",
                "action": "test action",
                "resource": "/test",
                "status_code": 200
            }
        )

        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"event_type": "api_call"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 所有返回的记录应该都是 api_call 类型
        for record in data:
            assert record["event_type"] == "api_call"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_06_filter_by_user(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-06: 按用户筛选审计日志"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"user": "admin"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 所有返回的记录应该都是 admin 用户的
        for record in data:
            assert record["user"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_07_pagination(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-07: 审计日志分页查询"""
        # 创建多条测试数据
        for i in range(5):
            await audit_log_client.post(
                "/api/audit/log",
                json={
                    "subsystem": "test",
                    "event_type": "pagination_test",
                    "user": "admin",
                    "action": f"test action {i}",
                    "resource": "/test",
                    "status_code": 200
                }
            )

        # 获取第一页
        response1 = await audit_log_client.get(
            "/api/audit/logs",
            params={"page": 1, "page_size": 2},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 200
        page1 = response1.json()

        # 获取第二页
        response2 = await audit_log_client.get(
            "/api/audit/logs",
            params={"page": 2, "page_size": 2},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200
        page2 = response2.json()

        # 两页的数据不应该重复
        if len(page1) > 0 and len(page2) > 0:
            page1_ids = {r["id"] for r in page1}
            page2_ids = {r["id"] for r in page2}
            assert page1_ids.isdisjoint(page2_ids), "分页数据不应重复"

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_adm_05_08_get_log_detail(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-08: 获取指定审计日志详情"""
        # 先创建一条日志
        create_response = await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test",
                "event_type": "detail_test",
                "user": "admin",
                "action": "test detail",
                "resource": "/test",
                "status_code": 200
            }
        )
        assert create_response.status_code == 200
        log_id = create_response.json()["id"]

        # 查询详情
        response = await audit_log_client.get(
            f"/api/audit/logs/{log_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == log_id

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_adm_05_09_view_audit_stats(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-09: 查看审计统计信息"""
        response = await audit_log_client.get(
            "/api/audit/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 验证统计信息结构
        assert "total_events" in data
        assert "events_by_subsystem" in data
        assert "events_by_type" in data
        assert "events_by_user" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_10_export_csv(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-10: 导出审计日志为 CSV"""
        response = await audit_log_client.post(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"format": "csv", "query": {}}
        )
        assert response.status_code == 200
        # 检查响应头
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type or "application/octet-stream" in content_type

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_05_11_export_json(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-11: 导出审计日志为 JSON"""
        response = await audit_log_client.post(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"format": "json", "query": {"subsystem": "portal"}}
        )
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_adm_05_12_export_with_filter(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-05-12: 带筛选条件导出审计日志"""
        response = await audit_log_client.post(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "format": "csv",
                "query": {"subsystem": "portal", "user": "admin"}
            }
        )
        assert response.status_code == 200
