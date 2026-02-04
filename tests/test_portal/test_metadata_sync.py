"""Unit tests for portal metadata_sync router

Tests for services/portal/routers/metadata_sync.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.api_response import ErrorCode
from services.common.auth import TokenPayload
from services.portal.routers.metadata_sync import (
    ETLMappingBase,
    ETLMappingCreate,
    ETLMappingUpdate,
    MetadataChangeEvent,
    create_mapping_v1,
    delete_mapping_v1,
    get_mapping_v1,
    get_mappings_v1,
    router,
    send_metadata_event_v1,
    trigger_sync_v1,
    update_mapping_v1,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/metadata-sync"


class TestETLMappingBase:
    """测试 ETL 映射基础模型"""

    def test_default_values(self):
        """测试默认值"""
        mapping = ETLMappingBase(
            source_urn="urn:li:dataset:(urn:li:dataPlatform:hive,test,PROD)",
            target_task_type="dolphinscheduler",
            target_task_id="task-123",
            trigger_on=["CREATE", "UPDATE"]
        )
        assert mapping.source_urn.startswith("urn:li:dataset:")
        assert mapping.target_task_type == "dolphinscheduler"
        assert mapping.target_task_id == "task-123"
        assert mapping.auto_update_config is True
        assert mapping.enabled is True
        assert mapping.description is None

    def test_with_all_values(self):
        """测试带所有值的映射"""
        mapping = ETLMappingBase(
            source_urn="urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)",
            target_task_type="seatunnel",
            target_task_id="pipeline-456",
            trigger_on=["CREATE", "UPDATE", "SCHEMA_CHANGE"],
            auto_update_config=False,
            description="Sync users table",
            enabled=False
        )
        assert mapping.description == "Sync users table"
        assert mapping.auto_update_config is False
        assert mapping.enabled is False


class TestETLMappingCreate:
    """测试创建 ETL 映射模型"""

    def test_create_mapping(self):
        """测试创建映射"""
        mapping = ETLMappingCreate(
            source_urn="urn:li:dataset:(urn:li:dataPlatform:hive,orders,PROD)",
            target_task_type="hop",
            target_task_id="workflow-789",
            trigger_on=["CREATE"]
        )
        assert mapping.target_task_type == "hop"
        assert len(mapping.trigger_on) == 1


class TestETLMappingUpdate:
    """测试更新 ETL 映射模型"""

    def test_update_mapping_partial(self):
        """测试部分更新"""
        update = ETLMappingUpdate(
            target_task_id="new-task-id",
            enabled=False
        )
        assert update.target_task_id == "new-task-id"
        assert update.enabled is False
        assert update.target_task_type is None
        assert update.trigger_on is None

    def test_update_mapping_all_fields(self):
        """测试更新所有字段"""
        update = ETLMappingUpdate(
            target_task_type="seatunnel",
            target_task_id="updated-task",
            trigger_on=["DELETE"],
            auto_update_config=False,
            description="Updated description",
            enabled=True
        )
        assert update.target_task_type == "seatunnel"
        assert update.description == "Updated description"


class TestMetadataChangeEvent:
    """测试元数据变更事件模型"""

    def test_create_event(self):
        """测试创建事件"""
        event = MetadataChangeEvent(
            entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,users,PROD)",
            change_type="UPDATE"
        )
        assert event.change_type == "UPDATE"
        assert event.changed_fields is None
        assert event.new_schema is None

    def test_create_event_with_details(self):
        """测试创建带详情的事件"""
        event = MetadataChangeEvent(
            entity_urn="urn:li:dataset:(urn:li:dataPlatform:mysql,orders,PROD)",
            change_type="SCHEMA_CHANGE",
            changed_fields=["email", "phone"],
            new_schema={
                "columns": [
                    {"name": "id", "type": "int"},
                    {"name": "email", "type": "varchar", "length": 255}
                ]
            }
        )
        assert event.changed_fields == ["email", "phone"]
        assert "columns" in event.new_schema


class TestGetMappingsV1:
    """测试获取映射规则列表"""

    @pytest.mark.asyncio
    async def test_get_mappings_success(self):
        """测试成功获取映射列表"""
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
            "mappings": [
                {
                    "id": "1",
                    "source_urn": "urn:li:dataset:(urn:li:dataPlatform:hive,users,PROD)",
                    "target_task_type": "dolphinscheduler",
                    "target_task_id": "task-123"
                },
                {
                    "id": "2",
                    "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,orders,PROD)",
                    "target_task_type": "seatunnel",
                    "target_task_id": "pipeline-456"
                }
            ],
            "total": 2
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_mappings_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "mappings" in result.data
            assert result.data["total"] == 2


class TestGetMappingV1:
    """测试获取单个映射规则"""

    @pytest.mark.asyncio
    async def test_get_mapping_success(self):
        """测试成功获取映射"""
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
            "source_urn": "urn:li:dataset:(urn:li:dataPlatform:hive,users,PROD)",
            "target_task_type": "dolphinscheduler",
            "target_task_id": "task-123",
            "trigger_on": ["CREATE", "UPDATE"],
            "enabled": True
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await get_mapping_v1(mapping_id="1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["target_task_type"] == "dolphinscheduler"


class TestCreateMappingV1:
    """测试创建映射规则"""

    @pytest.mark.asyncio
    async def test_create_mapping_success(self):
        """测试成功创建映射"""
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
            "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,products,PROD)",
            "target_task_type": "hop",
            "target_task_id": "workflow-789",
            "trigger_on": ["CREATE"],
            "enabled": True
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            mapping = ETLMappingCreate(
                source_urn="urn:li:dataset:(urn:li:dataPlatform:mysql,products,PROD)",
                target_task_type="hop",
                target_task_id="workflow-789",
                trigger_on=["CREATE"]
            )
            result = await create_mapping_v1(mapping=mapping, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["id"] == "3"


class TestUpdateMappingV1:
    """测试更新映射规则"""

    @pytest.mark.asyncio
    async def test_update_mapping_success(self):
        """测试成功更新映射"""
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
            "id": "1",
            "target_task_id": "updated-task-id",
            "enabled": False
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.put.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            update = ETLMappingUpdate(
                target_task_id="updated-task-id",
                enabled=False
            )
            result = await update_mapping_v1(mapping_id="1", mapping=update, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["enabled"] is False


class TestDeleteMappingV1:
    """测试删除映射规则"""

    @pytest.mark.asyncio
    async def test_delete_mapping_success(self):
        """测试成功删除映射"""
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

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.delete.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await delete_mapping_v1(mapping_id="1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["deleted"] is True


class TestTriggerSyncV1:
    """测试手动触发同步"""

    @pytest.mark.asyncio
    async def test_trigger_sync_success(self):
        """测试成功触发同步"""
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
            "sync_id": "sync-123",
            "status": "running",
            "message": "元数据同步已启动"
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await trigger_sync_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "sync_id" in result.data

    @pytest.mark.asyncio
    async def test_trigger_sync_service_error(self):
        """测试同步服务错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await trigger_sync_v1(user=mock_user)

            assert result.code == ErrorCode.EXTERNAL_SERVICE_ERROR


class TestSendMetadataEventV1:
    """测试发送元数据变更事件"""

    @pytest.mark.asyncio
    async def test_send_event_success(self):
        """测试成功发送事件"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="system",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event_id": "event-456",
            "status": "processed"
        }

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            event = MetadataChangeEvent(
                entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,users,PROD)",
                change_type="SCHEMA_CHANGE",
                changed_fields=["email"],
                new_schema={"columns": [{"name": "email", "type": "varchar"}]}
            )
            result = await send_metadata_event_v1(event=event, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["status"] == "processed"

    @pytest.mark.asyncio
    async def test_send_event_create_type(self):
        """测试发送创建类型事件"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="system",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "event-789", "status": "processed"}

        with patch('services.portal.routers.metadata_sync.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            event = MetadataChangeEvent(
                entity_urn="urn:li:dataset:(urn:li:dataPlatform:mysql,new_table,PROD)",
                change_type="CREATE"
            )
            result = await send_metadata_event_v1(event=event, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
