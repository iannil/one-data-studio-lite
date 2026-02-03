"""Unit tests for portal metadata router

Tests for services/portal/routers/metadata.py
OpenMetadata integration (replaces DataHub)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.metadata import (
    _openmetadata_request,
    _convert_entity_type,
    _convert_om_to_datahub_entity,
    _parse_fqn_from_urn,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀（保持 /api/proxy/datahub 以确保向后兼容）"""
        assert router.prefix == "/api/proxy/datahub"


class TestHelperFunctions:
    """测试辅助函数"""

    def test_convert_entity_type_dataset(self):
        """测试 dataset 类型转换"""
        assert _convert_entity_type("dataset") == "table"

    def test_convert_entity_type_dataflow(self):
        """测试 dataFlow 类型转换"""
        assert _convert_entity_type("dataFlow") == "pipeline"

    def test_convert_entity_type_unknown(self):
        """测试未知类型转换（保持原样）"""
        assert _convert_entity_type("unknown") == "unknown"

    def test_parse_fqn_from_urn_dataset(self):
        """测试从 dataset URN 解析 FQN"""
        urn = "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)"
        assert _parse_fqn_from_urn(urn) == "test_db.users"

    def test_parse_fqn_from_urn_tag(self):
        """测试从 tag URN 解析 FQN"""
        urn = "urn:li:tag:PII"
        assert _parse_fqn_from_urn(urn) == "PII"

    def test_parse_fqn_from_urn_invalid(self):
        """测试无效 URN"""
        assert _parse_fqn_from_urn("invalid") is None
        assert _parse_fqn_from_urn("") is None
        assert _parse_fqn_from_urn(None) is None

    def test_convert_om_to_datahub_entity_table(self):
        """测试 OpenMetadata 实体转换为 DataHub 格式"""
        om_entity = {
            "name": "users",
            "fullyQualifiedName": "test_db.users",
            "description": "User table",
            "serviceType": "MySQL",
            "id": "123",
        }
        result = _convert_om_to_datahub_entity(om_entity, "table")

        assert result["urn"].startswith("urn:li:dataset:")
        assert result["name"] == "users"
        assert result["description"] == "User table"
        assert result["platform"] == "mysql"
        assert result["_openmetadata"]["fqn"] == "test_db.users"


class TestOpenMetadataRequest:
    """测试 OpenMetadata 请求函数"""

    @pytest.mark.asyncio
    async def test_openmetadata_request_get_success(self):
        """测试 GET 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/test",
                method="GET"
            )

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_openmetadata_request_post_success(self):
        """测试 POST 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/create",
                method="POST",
                json_data={"name": "test"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_openmetadata_request_put_success(self):
        """测试 PUT 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/update",
                method="PUT",
                json_data={"name": "test"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_openmetadata_request_delete_success(self):
        """测试 DELETE 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/delete",
                method="DELETE",
                params={"id": "123"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_openmetadata_request_unsupported_method(self):
        """测试不支持的 HTTP 方法"""
        result = await _openmetadata_request(
            path="api/v1/test",
            method="PATCH"
        )

        assert result.code != 20000
        assert "不支持的 HTTP 方法" in result.message

    @pytest.mark.asyncio
    async def test_openmetadata_request_404(self):
        """测试 404 响应"""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/not_found",
                method="GET"
            )

            assert result.code != 20000
            assert "资源不存在" in result.message

    @pytest.mark.asyncio
    async def test_openmetadata_request_http_error(self):
        """测试 HTTP 错误响应"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/test",
                method="GET"
            )

            assert result.code != 20000
            assert "元数据服务请求失败" in result.message

    @pytest.mark.asyncio
    async def test_openmetadata_request_timeout(self):
        """测试超时处理"""
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/test",
                method="GET"
            )

            assert result.code != 20000
            assert "超时" in result.message

    @pytest.mark.asyncio
    async def test_openmetadata_request_exception(self):
        """测试异常处理"""
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            result = await _openmetadata_request(
                path="api/v1/test",
                method="GET"
            )

            assert result.code != 20000
            assert "元数据服务异常" in result.message


class TestListDatasetsV1:
    """测试 v1 列出数据集端点"""

    @pytest.mark.asyncio
    async def test_list_datasets_v1_default_params(self):
        """测试默认参数"""
        from services.portal.routers.metadata import list_datasets_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "hits": {"hits": [], "total": {"value": 0}}
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await list_datasets_v1(user=mock_payload)

            assert result.code == 20000
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_datasets_v1_custom_params(self):
        """测试自定义参数"""
        from services.portal.routers.metadata import list_datasets_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "hits": {"hits": [], "total": {"value": 0}}
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await list_datasets_v1(
                query="users",
                start=10,
                count=50,
                user=mock_payload
            )

            assert result.code == 20000


class TestSearchEntitiesV1:
    """测试 v1 搜索实体端点"""

    @pytest.mark.asyncio
    async def test_search_entities_v1_default(self):
        """测试默认参数"""
        from services.portal.routers.metadata import search_entities_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "hits": {"hits": [], "total": {"value": 0}}
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await search_entities_v1(user=mock_payload)

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_search_entities_v1_custom_entity(self):
        """测试自定义实体类型"""
        from services.portal.routers.metadata import search_entities_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "hits": {"hits": [], "total": {"value": 0}}
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await search_entities_v1(
                entity="dataset",
                query="users",
                user=mock_payload
            )

            assert result.code == 20000


class TestGetEntityAspectV1:
    """测试 v1 获取实体详情端点"""

    @pytest.mark.asyncio
    async def test_get_entity_aspect_v1(self):
        """测试获取实体详情"""
        from services.portal.routers.metadata import get_entity_aspect_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "name": "users",
                "columns": [
                    {"name": "id", "dataType": "INT"},
                    {"name": "name", "dataType": "VARCHAR"},
                ]
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_entity_aspect_v1(
                urn="urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                aspect="schemaMetadata",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_entity_aspect_v1_invalid_urn(self):
        """测试无效 URN"""
        from services.portal.routers.metadata import get_entity_aspect_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        result = await get_entity_aspect_v1(
            urn="invalid_urn",
            aspect="schemaMetadata",
            user=mock_payload
        )

        assert result.code != 20000
        assert "无效的 URN 格式" in result.message


class TestGetLineageV1:
    """测试 v1 获取血缘端点"""

    @pytest.mark.asyncio
    async def test_get_lineage_v1_default(self):
        """测试默认方向"""
        from services.portal.routers.metadata import get_lineage_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "nodes": [],
                "edges": []
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_lineage_v1(
                urn="urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_lineage_v1_incoming(self):
        """测试传入方向"""
        from services.portal.routers.metadata import get_lineage_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "nodes": [],
                "edges": []
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_lineage_v1(
                urn="urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                direction="INCOMING",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_lineage_v1_invalid_direction(self):
        """测试无效方向"""
        from services.portal.routers.metadata import get_lineage_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        result = await get_lineage_v1(
            urn="urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
            direction="INVALID",
            user=mock_payload
        )

        assert result.code != 20000
        assert "direction 必须是 INCOMING 或 OUTGOING" in result.message


class TestCreateTagV1:
    """测试 v1 创建标签端点"""

    @pytest.mark.asyncio
    async def test_create_tag_v1(self):
        """测试创建标签"""
        from services.portal.routers.metadata import create_tag_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"name": "PII"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await create_tag_v1(
                name="PII",
                description="Personally Identifiable Information",
                user=mock_payload
            )

            assert result.code == 20000


class TestSearchTagsV1:
    """测试 v1 搜索标签端点"""

    @pytest.mark.asyncio
    async def test_search_tags_v1(self):
        """测试搜索标签"""
        from services.portal.routers.metadata import search_tags_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.metadata._openmetadata_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={
                "data": [
                    {"name": "PII", "description": "Personal Info"}
                ]
            })

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await search_tags_v1(query="PII", user=mock_payload)

            assert result.code == 20000


class TestMetadataProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_metadata_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.metadata import metadata_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.metadata.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"data": []}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await metadata_proxy("api/v1/tables", mock_request, mock_payload)

            assert result.status_code == 200
