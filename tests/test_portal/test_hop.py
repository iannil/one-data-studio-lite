"""Unit tests for portal hop router

Tests for services/portal/routers/hop.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.common.api_response import ErrorCode
from services.common.auth import TokenPayload
from services.portal.routers.hop import (
    RunRequest,
    fetch_hop,
    get_pipeline_status_v1,
    get_pipeline_v1,
    get_workflow_status_v1,
    get_workflow_v1,
    list_pipelines_v1,
    list_run_configurations_v1,
    list_workflows_v1,
    router,
    run_pipeline_v1,
    run_workflow_v1,
    server_info_v1,
    server_status_v1,
    stop_pipeline_v1,
    stop_workflow_v1,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/hop"


# ============================================================
# fetch_hop Helper Tests
# ============================================================

class TestFetchHop:
    """测试 fetch_hop 辅助函数"""

    @pytest.mark.asyncio
    async def test_fetch_hop_get_success(self):
        """测试成功 GET 请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await fetch_hop("/test", method="GET")

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_hop_post_success(self):
        """测试成功 POST 请求"""
        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await fetch_hop("/test", method="POST", data={"key": "value"})

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_fetch_hop_timeout(self):
        """测试请求超时"""
        class MockClient:
            async def __aenter__(self):
                raise HTTPException(status_code=504, detail="Hop 请求超时")

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.hop.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(HTTPException) as exc_info:
                await fetch_hop("/test", method="GET")

            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_fetch_hop_connect_error(self):
        """测试连接错误"""
        class MockClient:
            async def __aenter__(self):
                raise HTTPException(status_code=503, detail="无法连接 Hop Server")

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.hop.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(HTTPException) as exc_info:
                await fetch_hop("/test", method="GET")

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_fetch_hop_http_error(self):
        """测试 HTTP 错误"""
        class MockClient:
            async def __aenter__(self):
                raise HTTPException(status_code=502, detail="Hop 请求失败")

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.hop.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(HTTPException) as exc_info:
                await fetch_hop("/test", method="GET")

            assert exc_info.value.status_code == 502


# ============================================================
# Workflow API Tests
# ============================================================

class TestListWorkflowsV1:
    """测试获取工作流列表"""

    @pytest.mark.asyncio
    async def test_list_workflows_success(self):
        """测试成功获取工作流列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "wf1", "description": "Workflow 1"},
            {"name": "wf2", "description": "Workflow 2"}
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await list_workflows_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "workflows" in result.data
            assert result.data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_workflows_empty(self):
        """测试获取空工作流列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await list_workflows_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_workflows_error(self):
        """测试获取工作流列表失败"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await list_workflows_v1(user=mock_user)

            assert result.code == ErrorCode.HOP_ERROR


class TestGetWorkflowV1:
    """测试获取工作流详情"""

    @pytest.mark.asyncio
    async def test_get_workflow_success(self):
        """测试成功获取工作流详情"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "wf1", "type": "workflow"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await get_workflow_v1(name="wf1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["name"] == "wf1"


class TestRunWorkflowV1:
    """测试执行工作流"""

    @pytest.mark.asyncio
    async def test_run_workflow_success(self):
        """测试成功执行工作流"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "exec-123", "status": "running"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            req = RunRequest(run_configuration="local")
            result = await run_workflow_v1(name="wf1", req=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["execution_id"] == "exec-123"

    @pytest.mark.asyncio
    async def test_run_workflow_with_parameters(self):
        """测试带参数执行工作流"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"executionId": "exec-456"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            req = RunRequest(
                run_configuration="prod",
                parameters={"param1": "value1"},
                variables={"var1": "value2"}
            )
            result = await run_workflow_v1(name="wf1", req=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetWorkflowStatusV1:
    """测试获取工作流执行状态"""

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self):
        """测试成功获取工作流状态"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "finished", "result": "success"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await get_workflow_status_v1(
                name="wf1",
                execution_id="exec-123",
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS
            assert result.data["execution_id"] == "exec-123"


class TestStopWorkflowV1:
    """测试停止工作流执行"""

    @pytest.mark.asyncio
    async def test_stop_workflow_success(self):
        """测试成功停止工作流"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await stop_workflow_v1(
                name="wf1",
                execution_id="exec-123",
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS
            assert "已停止" in result.message


# ============================================================
# Pipeline API Tests
# ============================================================

class TestListPipelinesV1:
    """测试获取管道列表"""

    @pytest.mark.asyncio
    async def test_list_pipelines_success(self):
        """测试成功获取管道列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "pipeline1", "type": "pipeline"},
            {"name": "pipeline2", "type": "pipeline"}
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await list_pipelines_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "pipelines" in result.data
            assert result.data["total"] == 2


class TestGetPipelineV1:
    """测试获取管道详情"""

    @pytest.mark.asyncio
    async def test_get_pipeline_success(self):
        """测试成功获取管道详情"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "pipeline1", "type": "pipeline"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await get_pipeline_v1(name="pipeline1", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestRunPipelineV1:
    """测试执行管道"""

    @pytest.mark.asyncio
    async def test_run_pipeline_success(self):
        """测试成功执行管道"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "pipe-exec-123"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            req = RunRequest(run_configuration="local")
            result = await run_pipeline_v1(name="pipeline1", req=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["execution_id"] == "pipe-exec-123"


class TestGetPipelineStatusV1:
    """测试获取管道执行状态"""

    @pytest.mark.asyncio
    async def test_get_pipeline_status_success(self):
        """测试成功获取管道状态"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await get_pipeline_status_v1(
                name="pipeline1",
                execution_id="pipe-exec-123",
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS


class TestStopPipelineV1:
    """测试停止管道执行"""

    @pytest.mark.asyncio
    async def test_stop_pipeline_success(self):
        """测试成功停止管道"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await stop_pipeline_v1(
                name="pipeline1",
                execution_id="pipe-exec-123",
                user=mock_user
            )

            assert result.code == ErrorCode.SUCCESS


# ============================================================
# Server API Tests
# ============================================================

class TestServerStatusV1:
    """测试获取服务器状态"""

    @pytest.mark.asyncio
    async def test_server_status_success(self):
        """测试成功获取服务器状态"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running", "uptime": 3600}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await server_status_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestServerInfoV1:
    """测试获取服务器信息"""

    @pytest.mark.asyncio
    async def test_server_info_success(self):
        """测试成功获取服务器信息"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2.0.0", "hostname": "hop-server"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await server_info_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestListRunConfigurationsV1:
    """测试获取运行配置"""

    @pytest.mark.asyncio
    async def test_list_run_configurations_success(self):
        """测试成功获取运行配置"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "local", "description": "Local execution"},
            {"name": "prod", "description": "Production execution"}
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            result = await list_run_configurations_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
