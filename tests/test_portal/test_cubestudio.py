"""Unit tests for portal cubestudio router

Tests for services/portal/routers/cubestudio.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.api_response import ErrorCode
from services.common.auth import TokenPayload
from services.portal.routers.cubestudio import (
    DataSourceRequest,
    ModelInferenceRequest,
    NotebookCreateRequest,
    PipelineRunRequest,
    chat_completion_v1,
    create_data_source_v1,
    create_notebook_v1,
    delete_pipeline_v1,
    get_metrics_v1,
    get_pipeline_v1,
    get_pipelines_v1,
    get_services_status_v1,
    list_alerts_v1,
    list_data_sources_v1,
    list_datasets_v1,
    list_models_v1,
    list_notebooks_v1,
    model_inference_v1,
    router,
    run_pipeline_v1,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/cubestudio"


# ============================================================
# Pipeline API Tests
# ============================================================

class TestGetPipelinesV1:
    """测试获取 Pipeline 列表"""

    @pytest.mark.asyncio
    async def test_get_pipelines_success(self):
        """测试成功获取 Pipeline 列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"pipelines": [{"id": 1, "name": "test_pipeline"}]}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_pipelines_v1(page=1, page_size=20, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data is not None
            assert "pipelines" in result.data

    @pytest.mark.asyncio
    async def test_get_pipelines_service_error(self):
        """测试 Cube-Studio 服务错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_pipelines_v1(page=1, page_size=20, user=mock_user)

            assert result.code == ErrorCode.CUBE_STUDIO_ERROR

    @pytest.mark.asyncio
    async def test_get_pipelines_exception(self):
        """测试服务异常"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Make AsyncClient itself raise an error
        async def raise_error_on_init(*args, **kwargs):
            raise ConnectionError("Connection failed")

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', side_effect=raise_error_on_init):
            result = await get_pipelines_v1(page=1, page_size=20, user=mock_user)

            assert result.code == ErrorCode.CUBE_STUDIO_ERROR


class TestGetPipelineV1:
    """测试获取单个 Pipeline"""

    @pytest.mark.asyncio
    async def test_get_pipeline_success(self):
        """测试成功获取 Pipeline 详情"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "test_pipeline"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_pipeline_v1(pipeline_id=1, user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["id"] == 1


class TestRunPipelineV1:
    """测试运行 Pipeline"""

    @pytest.mark.asyncio
    async def test_run_pipeline_success(self):
        """测试成功运行 Pipeline"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"run_id": "run_123", "status": "running"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = PipelineRunRequest(
            run_configuration="local",
            parameters={"key": "value"}
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await run_pipeline_v1(pipeline_id=1, request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestDeletePipelineV1:
    """测试删除 Pipeline"""

    @pytest.mark.asyncio
    async def test_delete_pipeline_success(self):
        """测试成功删除 Pipeline"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await delete_pipeline_v1(pipeline_id=1, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_delete_pipeline_204_success(self):
        """测试删除 Pipeline 返回 204"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await delete_pipeline_v1(pipeline_id=1, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


# ============================================================
# Model Inference API Tests
# ============================================================

class TestListModelsV1:
    """测试获取模型列表"""

    @pytest.mark.asyncio
    async def test_list_models_success(self):
        """测试成功获取模型列表"""
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
            "models": [
                {"name": "llama2:latest", "size": 1000000},
                {"name": "mistral:7b", "size": 2000000},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_models_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "models" in result.data
            assert "llama2" in result.data["models"]

    @pytest.mark.asyncio
    async def test_list_models_ollama_error(self):
        """测试 Ollama 服务错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_models_v1(user=mock_user)

            assert result.code == ErrorCode.CUBE_STUDIO_ERROR


class TestModelInferenceV1:
    """测试模型推理"""

    @pytest.mark.asyncio
    async def test_model_inference_non_stream_success(self):
        """测试非流式推理成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test output", "model": "llama2"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = ModelInferenceRequest(
            model_name="llama2",
            prompt="Hello",
            stream=False
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await model_inference_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_model_inference_stream_success(self):
        """测试流式推理成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Stream output"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = ModelInferenceRequest(
            model_name="llama2",
            prompt="Hello",
            stream=True
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await model_inference_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_model_inference_with_options(self):
        """测试带参数的推理"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Output"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = ModelInferenceRequest(
            model_name="llama2",
            prompt="Hello",
            max_tokens=4096,
            temperature=0.7,
            top_p=0.95,
            stream=False
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await model_inference_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestChatCompletionV1:
    """测试对话补全"""

    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """测试对话补全成功"""
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
            "message": {"role": "assistant", "content": "Hello!"},
            "model": "llama2"
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = ModelInferenceRequest(
            model_name="llama2",
            prompt="Hello, how are you?"
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await chat_completion_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_chat_completion_error(self):
        """测试对话补全错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = ModelInferenceRequest(
            model_name="llama2",
            prompt="Hello"
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await chat_completion_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.CUBE_STUDIO_ERROR


# ============================================================
# Data Management API Tests
# ============================================================

class TestListDataSourcesV1:
    """测试获取数据源列表"""

    @pytest.mark.asyncio
    async def test_list_data_sources_success(self):
        """测试成功获取数据源列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data_sources": [{"id": 1, "name": "mysql_src"}]}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_data_sources_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_list_data_sources_endpoint_not_found(self):
        """测试数据源端点不存在时返回空列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_data_sources_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["data_sources"] == []

    @pytest.mark.asyncio
    async def test_list_data_sources_exception(self):
        """测试数据源异常时返回带提示的空列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Make AsyncClient raise error
        async def raise_error_on_init(*args, **kwargs):
            raise ConnectionError("Service unavailable")

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', side_effect=raise_error_on_init):
            result = await list_data_sources_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "note" in result.data


class TestCreateDataSourceV1:
    """测试创建数据源"""

    @pytest.mark.asyncio
    async def test_create_data_source_success(self):
        """测试成功创建数据源"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1, "name": "new_source"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = DataSourceRequest(
            name="mysql_prod",
            type="mysql",
            connection_params={"host": "localhost", "port": 3306}
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await create_data_source_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestListDatasetsV1:
    """测试获取数据集列表"""

    @pytest.mark.asyncio
    async def test_list_datasets_success(self):
        """测试成功获取数据集列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"datasets": [{"id": 1, "name": "sales_data"}]}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_datasets_v1(page=1, page_size=20, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


# ============================================================
# Notebook API Tests
# ============================================================

class TestListNotebooksV1:
    """测试获取 Notebook 列表"""

    @pytest.mark.asyncio
    async def test_list_notebooks_success(self):
        """测试成功获取 Notebook 列表"""
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
            "content": {
                "items": [
                    {"name": "analysis.ipynb", "type": "notebook"}
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_notebooks_v1(path="/", user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_list_notebooks_with_custom_path(self):
        """测试获取指定路径的 Notebook"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": {"items": []}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_notebooks_v1(path="/work", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestCreateNotebookV1:
    """测试创建 Notebook"""

    @pytest.mark.asyncio
    async def test_create_notebook_success(self):
        """测试成功创建 Notebook"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "analysis.ipynb",
            "type": "notebook",
            "path": "/analysis.ipynb"
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = NotebookCreateRequest(
            name="analysis",
            kernel_type="python3",
            parent_folder="/"
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await create_notebook_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_create_notebook_in_folder(self):
        """测试在文件夹中创建 Notebook"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "test.ipynb"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        req = NotebookCreateRequest(
            name="test",
            parent_folder="/work"
        )

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await create_notebook_v1(request=req, user=mock_user)

            assert result.code == ErrorCode.SUCCESS


# ============================================================
# Monitoring API Tests
# ============================================================

class TestGetMetricsV1:
    """测试获取监控指标"""

    @pytest.mark.asyncio
    async def test_get_metrics_success(self):
        """测试成功获取监控指标"""
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
            "status": "success",
            "data": {"result": [{"metric": {}, "value": [1234567890, "1"]}]}
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_metrics_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_get_metrics_prometheus_not_available(self):
        """测试 Prometheus 不可用时"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_metrics_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "note" in result.data


class TestListAlertsV1:
    """测试获取告警列表"""

    @pytest.mark.asyncio
    async def test_list_alerts_success(self):
        """测试成功获取告警列表"""
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
            "status": "success",
            "data": [
                {
                    "labels": {"alertname": "HighCPU", "instance": "server1"},
                    "state": "firing"
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await list_alerts_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetServicesStatusV1:
    """测试获取服务状态"""

    @pytest.mark.asyncio
    async def test_get_services_status_all_online(self):
        """测试所有服务在线"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_services_status_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "services" in result.data

    @pytest.mark.asyncio
    async def test_get_services_status_mixed(self):
        """测试服务状态混合"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            mock_resp = MagicMock()
            # First service online, others offline
            mock_resp.status_code = 200 if call_count[0] == 1 else 503
            return mock_resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_services_status_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_get_services_status_all_offline(self):
        """测试所有服务离线"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Create a mock client that raises on get()
        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, *args, **kwargs):
                raise ConnectionError("Service unavailable")

        mock_client = MockAsyncClient()

        with patch('services.portal.routers.cubestudio.httpx.AsyncClient', return_value=mock_client):
            result = await get_services_status_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            # All services should be offline
            for name, info in result.data["services"].items():
                assert info["status"] == "offline"
