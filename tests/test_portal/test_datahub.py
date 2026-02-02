"""Unit tests for portal datahub router

Tests for services/portal/routers/datahub.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.datahub import (
    _datahub_request,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/datahub"


class TestDataHubRequest:
    """测试 DataHub 请求函数"""

    @pytest.mark.asyncio
    async def test_datahub_request_get_success(self):
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

            result = await _datahub_request(
                path="api/test",
                method="GET"
            )

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_datahub_request_post_success(self):
        """测试 POST 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"created": True}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _datahub_request(
                path="api/create",
                method="POST",
                json_data={"name": "test"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_datahub_request_with_params(self):
        """测试带查询参数的请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _datahub_request(
                path="api/search",
                method="GET",
                params={"q": "test"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_datahub_request_unsupported_method(self):
        """测试不支持的 HTTP 方法"""
        result = await _datahub_request(
            path="api/test",
            method="DELETE"
        )

        assert result.code != 20000
        assert "不支持的 HTTP 方法" in result.message

    @pytest.mark.asyncio
    async def test_datahub_request_http_error(self):
        """测试 HTTP 错误响应"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _datahub_request(
                path="api/test",
                method="GET"
            )

            assert result.code != 20000
            assert "DataHub 请求失败" in result.message

    @pytest.mark.asyncio
    async def test_datahub_request_exception(self):
        """测试异常处理"""
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            result = await _datahub_request(
                path="api/test",
                method="GET"
            )

            assert result.code != 20000
            assert "DataHub 服务异常" in result.message


class TestListDatasetsV1:
    """测试 v1 列出数据集端点"""

    @pytest.mark.asyncio
    async def test_list_datasets_v1_default_params(self):
        """测试默认参数"""
        from services.portal.routers.datahub import list_datasets_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"datasets": []}

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"datasets": []})

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
        from services.portal.routers.datahub import list_datasets_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"datasets": []}

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"datasets": []})

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
        from services.portal.routers.datahub import search_entities_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"entities": []})

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
        from services.portal.routers.datahub import search_entities_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"entities": []})

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
        from services.portal.routers.datahub import get_entity_aspect_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"aspect": "schema"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_entity_aspect_v1(
                urn="dataset://test",
                aspect="schema",
                user=mock_payload
            )

            assert result.code == 20000


class TestGetLineageV1:
    """测试 v1 获取血缘端点"""

    @pytest.mark.asyncio
    async def test_get_lineage_v1_default(self):
        """测试默认方向"""
        from services.portal.routers.datahub import get_lineage_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"relationships": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_lineage_v1(
                urn="dataset://test",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_lineage_v1_incoming(self):
        """测试传入方向"""
        from services.portal.routers.datahub import get_lineage_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"relationships": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_lineage_v1(
                urn="dataset://test",
                direction="INCOMING",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_lineage_v1_invalid_direction(self):
        """测试无效方向"""
        from services.portal.routers.datahub import get_lineage_v1
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
            urn="dataset://test",
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
        from services.portal.routers.datahub import create_tag_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"tag": "created"})

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
        from services.portal.routers.datahub import search_tags_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.datahub._datahub_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"tags": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await search_tags_v1(query="PII", user=mock_payload)

            assert result.code == 20000


class TestDataHubProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_datahub_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.datahub import datahub_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.datahub.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"data": []}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await datahub_proxy("api/datasets", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_datahub_proxy_post(self):
        """测试 POST 代理"""
        from services.portal.routers.datahub import datahub_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

        with patch('services.portal.routers.datahub.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"created": true}', status_code=201)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await datahub_proxy("api/entities", mock_request, mock_payload)

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_datahub_proxy_put(self):
        """测试 PUT 代理"""
        from services.portal.routers.datahub import datahub_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "PUT"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "updated"}')

        with patch('services.portal.routers.datahub.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"updated": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await datahub_proxy("api/update/1", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_datahub_proxy_delete(self):
        """测试 DELETE 代理"""
        from services.portal.routers.datahub import datahub_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.datahub.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"deleted": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await datahub_proxy("api/delete/1", mock_request, mock_payload)

            assert result.status_code == 200
