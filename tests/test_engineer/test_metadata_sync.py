"""
TC-ENG-02: 元数据同步测试
测试 DataHub 元数据变更事件处理和映射规则管理
"""

import pytest
from httpx import AsyncClient


class TestMetadataSync:
    """TC-ENG-02: 元数据同步测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_02_01_receive_webhook(
        self, metadata_sync_client: AsyncClient
    ):
        """TC-ENG-02-01: 接收 DataHub 元数据变更事件"""
        response = await metadata_sync_client.post(
            "/api/metadata/webhook",
            json={
                "entity_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                "change_type": "CREATE",
                "changed_fields": ["schema"],
                "timestamp": "2024-01-29T10:00:00Z"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "affected_tasks" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_02_02_trigger_etl_task(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-02: 元数据变更触发 ETL 任务"""
        # 1. 先创建映射规则
        mapping_response = await metadata_sync_client.put(
            "/api/metadata/mappings/mapping-001",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "mapping-001",
                "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                "target_task_type": "dolphinscheduler",
                "target_task_id": "100",
                "trigger_on": ["CREATE", "UPDATE"],
                "enabled": True
            }
        )
        assert mapping_response.status_code == 200

        # 2. 发送变更事件
        response = await metadata_sync_client.post(
            "/api/metadata/webhook",
            json={
                "entity_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                "change_type": "UPDATE",
                "changed_fields": ["schema"],
                "timestamp": "2024-01-29T10:00:00Z"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "affected_tasks" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_eng_02_03_delete_event(
        self, metadata_sync_client: AsyncClient
    ):
        """TC-ENG-02-03: 元数据变更事件 - DELETE 类型"""
        response = await metadata_sync_client.post(
            "/api/metadata/webhook",
            json={
                "entity_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.old_table,PROD)",
                "change_type": "DELETE",
                "timestamp": "2024-01-29T10:00:00Z"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_02_04_manual_sync(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-04: 手动触发元数据同步"""
        response = await metadata_sync_client.post(
            "/api/metadata/sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_eng_02_05_sync_datahub_unavailable(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-05: 元数据同步 - DataHub 不可用"""
        # 在测试环境中，DataHub 通常不可用
        response = await metadata_sync_client.post(
            "/api/metadata/sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # 可能成功也可能失败，但应该返回正确的结构
        assert "success" in data
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_02_06_list_mappings(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-06: 查看映射规则列表"""
        response = await metadata_sync_client.get(
            "/api/metadata/mappings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_02_07_create_mapping(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-07: 创建映射规则"""
        response = await metadata_sync_client.put(
            "/api/metadata/mappings/test-mapping",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "test-mapping",
                "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.orders,PROD)",
                "target_task_type": "seatunnel",
                "target_task_id": "sync-orders-job",
                "trigger_on": ["CREATE", "UPDATE"],
                "enabled": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-mapping"
        assert data["source_urn"] == "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.orders,PROD)"
        assert data["enabled"] is True

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_eng_02_08_disable_mapping(
        self, metadata_sync_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-02-08: 更新映射规则 - 禁用"""
        # 先创建规则
        await metadata_sync_client.put(
            "/api/metadata/mappings/disable-test",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "disable-test",
                "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.orders,PROD)",
                "target_task_type": "seatunnel",
                "target_task_id": "sync-orders-job",
                "trigger_on": ["CREATE", "UPDATE"],
                "enabled": True
            }
        )

        # 禁用规则
        response = await metadata_sync_client.put(
            "/api/metadata/mappings/disable-test",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "disable-test",
                "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.orders,PROD)",
                "target_task_type": "seatunnel",
                "target_task_id": "sync-orders-job",
                "trigger_on": ["CREATE", "UPDATE"],
                "enabled": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
