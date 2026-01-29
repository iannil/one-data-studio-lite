"""
TC-ADM-02: 平台配置测试
测试子系统状态查看和服务健康检查
"""

import pytest
from httpx import AsyncClient


class TestSubsystems:
    """TC-ADM-02: 平台配置测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_adm_02_01_view_subsystem_status(
        self, portal_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-02-01: 查看子系统状态"""
        response = await portal_client.get(
            "/api/subsystems",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # 应该返回子系统列表
        assert isinstance(data, list)
        assert len(data) > 0

        # 验证每个子系统的结构
        for subsystem in data:
            assert "name" in subsystem
            assert "display_name" in subsystem
            assert "url" in subsystem
            assert "status" in subsystem
            assert subsystem["status"] in ("online", "offline")

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_02_02_batch_health_check(
        self,
        portal_client: AsyncClient,
        nl2sql_client: AsyncClient,
        ai_cleaning_client: AsyncClient,
        metadata_sync_client: AsyncClient,
        data_api_client: AsyncClient,
        sensitive_detect_client: AsyncClient,
        audit_log_client: AsyncClient
    ):
        """TC-ADM-02-02: 批量检查服务健康状态"""
        clients = {
            "portal": portal_client,
            "nl2sql": nl2sql_client,
            "ai_cleaning": ai_cleaning_client,
            "metadata_sync": metadata_sync_client,
            "data_api": data_api_client,
            "sensitive_detect": sensitive_detect_client,
            "audit_log": audit_log_client
        }

        for service_name, client in clients.items():
            response = await client.get("/health")
            assert response.status_code == 200, f"{service_name} 健康检查失败"
            data = response.json()
            assert data["status"] == "healthy", f"{service_name} 状态不健康"
