"""
TC-STW-02: 元数据管理测试
测试元数据同步、映射规则管理等功能
"""

import pytest
from httpx import AsyncClient


class TestMetadataManagement:
    """TC-STW-02: 元数据管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_stw_01_01_login_system(self, portal_client: AsyncClient):
        """TC-STW-01-01: 登录系统"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_stw_02_01_trigger_metadata_sync(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-STW-02-01: 触发元数据同步"""
        response = await metadata_sync_client.post(
            "/api/metadata/sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_stw_02_02_view_change_events(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-STW-02-02: 查看元数据变更事件"""
        response = await audit_log_client.get(
            "/api/audit/logs",
            params={"subsystem": "metadata-sync"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_stw_02_03_configure_mapping(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-STW-02-03: 配置元数据采集映射"""
        response = await metadata_sync_client.put(
            "/api/metadata/mappings/stw-mapping-001",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "stw-mapping-001",
                "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,prod_db.customers,PROD)",
                "target_task_type": "dolphinscheduler",
                "target_task_id": "200",
                "trigger_on": ["CREATE", "UPDATE", "DELETE"],
                "enabled": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "stw-mapping-001"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_stw_02_04_view_mappings(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-STW-02-04: 查看已配置的映射规则"""
        response = await metadata_sync_client.get(
            "/api/metadata/mappings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
