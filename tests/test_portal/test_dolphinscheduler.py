"""Unit tests for portal dolphinscheduler router

Tests for services/portal/routers/dolphinscheduler.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.dolphinscheduler import (
    _ds_request,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/dolphinscheduler"


class TestDSRequest:
    """测试 DolphinScheduler 请求函数"""

    @pytest.mark.asyncio
    async def test_ds_request_get_success(self):
        """测试 GET 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": {"projects": []}, "msg": "success"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _ds_request(
                path="projects",
                method="GET"
            )

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_ds_request_post_success(self):
        """测试 POST 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": {"created": True}, "msg": "success"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _ds_request(
                path="projects/create",
                method="POST",
                json_data={"name": "test"}
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_ds_request_delete_success(self):
        """测试 DELETE 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": None, "msg": "deleted"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _ds_request(
                path="projects/1",
                method="DELETE"
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_ds_request_unsupported_method(self):
        """测试不支持的 HTTP 方法"""
        result = await _ds_request(
            path="api/test",
            method="PUT"
        )

        assert result.code != 20000
        assert "不支持的 HTTP 方法" in result.message

    @pytest.mark.asyncio
    async def test_ds_request_http_error(self):
        """测试 HTTP 错误响应"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"code": -1, "msg": "Internal error"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _ds_request(
                path="api/test",
                method="GET"
            )

            assert result.code != 20000
            # The message comes from ds_data.get("msg") when code != 0
            assert result.message == "Internal error"

    @pytest.mark.asyncio
    async def test_ds_request_exception(self):
        """测试异常处理"""
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            result = await _ds_request(
                path="api/test",
                method="GET"
            )

            assert result.code != 20000
            assert "DolphinScheduler 服务异常" in result.message


class TestGetProjectsV1:
    """测试 v1 获取项目列表端点"""

    @pytest.mark.asyncio
    async def test_get_projects_v1_default(self):
        """测试默认参数"""
        from services.portal.routers.dolphinscheduler import get_projects_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"projects": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_projects_v1(user=mock_payload)

            assert result.code == 20000
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_projects_v1_pagination(self):
        """测试分页参数"""
        from services.portal.routers.dolphinscheduler import get_projects_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"projects": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_projects_v1(pageNo=2, pageSize=50, user=mock_payload)

            assert result.code == 20000


class TestGetProcessDefinitionsV1:
    """测试 v1 获取流程定义端点"""

    @pytest.mark.asyncio
    async def test_get_process_definitions_v1(self):
        """测试获取流程定义"""
        from services.portal.routers.dolphinscheduler import get_process_definitions_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"processDefinitions": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_process_definitions_v1(
                project_code="my_project",
                user=mock_payload
            )

            assert result.code == 20000


class TestGetSchedulesV1:
    """测试 v1 获取调度列表端点"""

    @pytest.mark.asyncio
    async def test_get_schedules_v1(self):
        """测试获取调度列表"""
        from services.portal.routers.dolphinscheduler import get_schedules_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"schedules": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_schedules_v1(
                project_code="my_project",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_schedules_v1_with_filter(self):
        """测试带流程定义过滤"""
        from services.portal.routers.dolphinscheduler import get_schedules_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"schedules": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_schedules_v1(
                project_code="my_project",
                processDefinitionCode=123,
                user=mock_payload
            )

            assert result.code == 20000


class TestUpdateScheduleStateV1:
    """测试 v1 更新调度状态端点"""

    @pytest.mark.asyncio
    async def test_update_schedule_state_v1_online(self):
        """测试上线调度"""
        from services.portal.routers.dolphinscheduler import update_schedule_state_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"updated": True})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await update_schedule_state_v1(
                project_code="my_project",
                schedule_id=1,
                releaseState="ONLINE",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_update_schedule_state_v1_offline(self):
        """测试下线调度"""
        from services.portal.routers.dolphinscheduler import update_schedule_state_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"updated": True})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await update_schedule_state_v1(
                project_code="my_project",
                schedule_id=1,
                releaseState="OFFLINE",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_update_schedule_state_v1_invalid_state(self):
        """测试无效状态"""
        from services.portal.routers.dolphinscheduler import update_schedule_state_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        result = await update_schedule_state_v1(
            project_code="my_project",
            schedule_id=1,
            releaseState="INVALID",
            user=mock_payload
        )

        assert result.code != 20000
        assert "releaseState 必须是 ONLINE 或 OFFLINE" in result.message


class TestGetTaskInstancesV1:
    """测试 v1 获取任务实例端点"""

    @pytest.mark.asyncio
    async def test_get_task_instances_v1(self):
        """测试获取任务实例"""
        from services.portal.routers.dolphinscheduler import get_task_instances_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"taskInstances": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_task_instances_v1(
                project_code="my_project",
                user=mock_payload
            )

            assert result.code == 20000

    @pytest.mark.asyncio
    async def test_get_task_instances_v1_with_filters(self):
        """测试带过滤条件"""
        from services.portal.routers.dolphinscheduler import get_task_instances_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"taskInstances": []})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_task_instances_v1(
                project_code="my_project",
                stateType="SUCCESS",
                searchVal="my_task",
                user=mock_payload
            )

            assert result.code == 20000


class TestGetTaskLogV1:
    """测试 v1 获取任务日志端点"""

    @pytest.mark.asyncio
    async def test_get_task_log_v1(self):
        """测试获取任务日志"""
        from services.portal.routers.dolphinscheduler import get_task_log_v1
        from services.common.auth import TokenPayload
        from datetime import datetime

        with patch('services.portal.routers.dolphinscheduler._ds_request', new_callable=AsyncMock) as mock_request:
            from services.common.api_response import success
            mock_request.return_value = success(data={"log": "Task log content"})

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_task_log_v1(
                project_code="my_project",
                task_instance_id=12345,
                user=mock_payload
            )

            assert result.code == 20000
            assert result.data == {"log": "Task log content"}


class TestDSProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_ds_proxy_get(self):
        """测试 GET 代理"""
        from services.portal.routers.dolphinscheduler import ds_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.dolphinscheduler.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"data": []}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await ds_proxy("api/projects", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_ds_proxy_post(self):
        """测试 POST 代理"""
        from services.portal.routers.dolphinscheduler import ds_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

        with patch('services.portal.routers.dolphinscheduler.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"created": true}', status_code=201)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await ds_proxy("api/create", mock_request, mock_payload)

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_ds_proxy_put(self):
        """测试 PUT 代理"""
        from services.portal.routers.dolphinscheduler import ds_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "PUT"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "updated"}')

        with patch('services.portal.routers.dolphinscheduler.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"updated": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await ds_proxy("api/update/1", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_ds_proxy_delete(self):
        """测试 DELETE 代理"""
        from services.portal.routers.dolphinscheduler import ds_proxy
        from fastapi import Request
        from services.common.auth import TokenPayload
        from datetime import datetime

        mock_request = MagicMock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.dolphinscheduler.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"deleted": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await ds_proxy("api/delete/1", mock_request, mock_payload)

            assert result.status_code == 200
