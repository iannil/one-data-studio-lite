"""
TC-ADM-06: 安全巡检测试
测试敏感数据检测结果查看和异常操作记录
"""

import pytest
from httpx import AsyncClient


class TestSecurityCheck:
    """TC-ADM-06: 安全巡检测试"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_06_01_check_sensitive_reports(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-06-01: 检查敏感数据识别结果"""
        response = await sensitive_detect_client.get(
            "/api/sensitive/reports",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # 应该返回扫描报告列表
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_06_02_view_abnormal_operations(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-06-02: 查看异常操作记录"""
        # 先创建一些失败的请求记录
        await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test",
                "event_type": "api_call",
                "user": "admin",
                "action": "failed request",
                "resource": "/test",
                "status_code": 403
            }
        )
        await audit_log_client.post(
            "/api/audit/log",
            json={
                "subsystem": "test",
                "event_type": "api_call",
                "user": "admin",
                "action": "server error",
                "resource": "/test",
                "status_code": 500
            }
        )

        # 查询所有日志
        response = await audit_log_client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 筛选出异常操作（状态码 >= 400）
        abnormal_records = [r for r in data if r.get("status_code", 0) >= 400]
        # 应该能找到异常记录
        assert len(abnormal_records) > 0
