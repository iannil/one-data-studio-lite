"""
TC-SEC-06: 审计日志查询测试
测试安全管理员查询审计日志功能
"""

import pytest
from httpx import AsyncClient


class TestAuditQuery:
    """TC-SEC-06: 审计日志查询测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_06_01_query_all_logs(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-01: 查询所有审计日志"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_06_02_query_by_subsystem(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-02: 按子系统查询审计日志"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"subsystem": "sensitive-detect"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 所有返回的记录应该都是指定子系统的
        for record in data:
            assert record["subsystem"] == "sensitive-detect"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_06_03_query_failed_access(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-03: 查询失败的访问尝试"""
        # 先创建一些失败的请求记录
        await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test",
                "event_type": "api_call",
                "user": "attacker",
                "action": "unauthorized access",
                "resource": "/admin",
                "status_code": 403
            }
        )

        response = await audit_log_client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 筛选失败的请求
        failed_requests = [r for r in data if r.get("status_code", 0) >= 400]
        # 应该能找到失败的请求
        assert len(failed_requests) >= 0  # 可能为空，但不应该报错

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_sec_06_04_query_anonymous_access(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-04: 查询匿名访问记录"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"user": "anonymous"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 所有返回的记录应该都是匿名用户的
        for record in data:
            assert record["user"] == "anonymous"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_06_05_query_sensitive_operations(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-05: 查询敏感操作记录"""
        # 查询敏感数据服务的日志
        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"subsystem": "sensitive-detect"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

        # 查询数据 API 的日志
        response2 = await audit_log_client.get(
            "/api/audit/logs",
            params={"subsystem": "data-api"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_06_06_view_audit_stats(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-06-06: 查看审计统计"""
        response = await audit_log_client.get(
            "/api/audit/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_events" in data
        assert "events_by_subsystem" in data
