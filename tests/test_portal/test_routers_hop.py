"""Unit tests for hop router

Tests for services/portal/routers/hop.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from services.portal.routers.hop import (
    router,
    RunRequest,
    PipelineRequest,
    fetch_hop,
)
from services.common.auth import TokenPayload


# Mock user for testing
MOCK_USER = TokenPayload(
    sub="test",
    username="test",
    role="viewer",
    exp=datetime(2099, 12, 31),
    iat=datetime(2023, 1, 1)
)


async def mock_get_current_user():
    return MOCK_USER


class TestRunRequest:
    """测试RunRequest模型"""

    def test_default_values(self):
        """测试默认值"""
        req = RunRequest()
        assert req.run_configuration == "local"
        assert req.parameters is None
        assert req.variables is None

    def test_with_parameters(self):
        """测试带参数"""
        req = RunRequest(
            run_configuration="prod",
            parameters={"key": "value"},
            variables={"var1": "value1"}
        )
        assert req.run_configuration == "prod"
        assert req.parameters == {"key": "value"}
        assert req.variables == {"var1": "value1"}


class TestPipelineRequest:
    """测试PipelineRequest模型"""

    def test_pipeline_request(self):
        """测试管道请求"""
        req = PipelineRequest(
            name="test-pipeline",
            run_configuration="local",
            parameters={"param1": "value1"}
        )
        assert req.name == "test-pipeline"
        assert req.run_configuration == "local"
        assert req.parameters == {"param1": "value1"}


class TestFetchHop:
    """测试fetch_hop函数"""

    @pytest.mark.asyncio
    async def test_fetch_hop_get_success(self):
        """测试GET请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_hop("/test/path", method="GET")

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_hop_post_success(self):
        """测试POST请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "exec-123"}

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_hop("/test/path", method="POST", data={"key": "value"})

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_hop_timeout(self):
        """测试超时异常"""
        import httpx

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await fetch_hop("/test/path", method="GET")

            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_fetch_hop_connect_error(self):
        """测试连接错误"""
        import httpx

        with patch('services.portal.routers.hop.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await fetch_hop("/test/path", method="GET")

            assert exc_info.value.status_code == 503


class TestWorkflowEndpoints:
    """测试工作流端点"""

    @pytest.mark.asyncio
    async def test_list_workflows_v1_success(self):
        """测试列出工作流成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "workflow1", "description": "Test workflow 1"},
            {"name": "workflow2", "description": "Test workflow 2"},
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            # Override dependency
            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/workflows")

                assert response.status_code == 200
                result = response.json()
                assert result["code"] == 20000
                assert "workflows" in result["data"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_workflow_v1_success(self):
        """测试获取工作流详情成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-workflow", "steps": []}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/workflows/test-workflow")

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["name"] == "test-workflow"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_run_workflow_v1_success(self):
        """测试执行工作流成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "exec-123"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/proxy/hop/v1/workflows/test-workflow/run",
                    json={"run_configuration": "local"}
                )

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["execution_id"] == "exec-123"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_workflow_status_v1_success(self):
        """测试获取工作流状态成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running", "progress": 50}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/workflows/test-workflow/status/exec-123")

                assert response.status_code == 200
                result = response.json()
                assert "status" in result["data"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_stop_workflow_v1_success(self):
        """测试停止工作流成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stopped": True}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post("/api/proxy/hop/v1/workflows/test-workflow/stop/exec-123")

                assert response.status_code == 200
                result = response.json()
                # Message is "工作流执行 exec-123 已停止" in Chinese
                assert "已停止" in result["message"] or "stopped" in result["message"].lower()
            finally:
                app.dependency_overrides.clear()


class TestPipelineEndpoints:
    """测试管道端点"""

    @pytest.mark.asyncio
    async def test_list_pipelines_v1_success(self):
        """测试列出管道成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "pipeline1"},
            {"name": "pipeline2"},
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/pipelines")

                assert response.status_code == 200
                result = response.json()
                assert "pipelines" in result["data"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_pipeline_v1_success(self):
        """测试获取管道详情成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-pipeline"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/pipelines/test-pipeline")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_run_pipeline_v1_success(self):
        """测试执行管道成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"executionId": "exec-456"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/proxy/hop/v1/pipelines/test-pipeline/run",
                    json={"run_configuration": "local"}
                )

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["execution_id"] == "exec-456"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_pipeline_status_v1_success(self):
        """测试获取管道状态成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "finished"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/pipelines/test-pipeline/status/exec-456")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_stop_pipeline_v1_success(self):
        """测试停止管道成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post("/api/proxy/hop/v1/pipelines/test-pipeline/stop/exec-456")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()


class TestServerEndpoints:
    """测试服务器端点"""

    @pytest.mark.asyncio
    async def test_server_status_v1_success(self):
        """测试获取服务器状态成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/server/status")

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["status"] == "online"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_server_info_v1_success(self):
        """测试获取服务器信息成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2.0.0"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/server/info")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_run_configurations_v1_success(self):
        """测试列出运行配置成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "local", "description": "本地执行"}
        ]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/v1/run-configurations")

                assert response.status_code == 200
                result = response.json()
                assert "configurations" in result["data"]
            finally:
                app.dependency_overrides.clear()


class TestLegacyEndpoints:
    """测试旧版端点"""

    @pytest.mark.asyncio
    async def test_list_workflows_legacy(self):
        """测试旧版列出工作流"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "workflow1"}]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/workflows")

                assert response.status_code == 200
                result = response.json()
                assert "workflows" in result
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_pipelines_legacy(self):
        """测试旧版列出管道"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "pipeline1"}]

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/pipelines")

                assert response.status_code == 200
                result = response.json()
                assert "pipelines" in result
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_server_status_legacy(self):
        """测试旧版服务器状态"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}

        with patch('services.portal.routers.hop.fetch_hop', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.hop import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/hop/server/status")

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "online"
            finally:
                app.dependency_overrides.clear()
