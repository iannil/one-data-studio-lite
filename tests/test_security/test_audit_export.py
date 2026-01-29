"""
TC-SEC-07: 审计报告导出测试
测试审计日志导出功能
"""

import pytest
from httpx import AsyncClient


class TestAuditExport:
    """TC-SEC-07: 审计报告导出测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_07_01_export_csv(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-07-01: 导出审计日志为 CSV"""
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
    async def test_sec_07_02_export_with_filter(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-07-02: 按条件导出审计日志"""
        response = await audit_log_client.post(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "format": "json",
                "query": {
                    "subsystem": "sensitive-detect"
                }
            }
        )
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type
