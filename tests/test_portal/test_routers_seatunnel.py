"""Unit tests for seatunnel router

Tests for services/portal/routers/seatunnel.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from services.portal.routers.seatunnel import (
    router,
    fetch_seatunnel,
    _normalize_job,
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


class TestNormalizeJob:
    """测试_normalize_job函数"""

    def test_normalize_job_with_job_id(self):
        """测试带job_id的任务"""
        job = {
            "jobId": "job-123",
            "jobName": "Test Job",
            "createTime": "2024-01-01",
        }
        result = _normalize_job(job, "RUNNING")

        assert result["jobId"] == "job-123"
        assert result["jobStatus"] == "RUNNING"
        assert result["jobName"] == "Test Job"
        assert result["raw"] == job

    def test_normalize_job_with_job_id_snake_case(self):
        """测试snake_case的job_id"""
        job = {
            "job_id": "job-456",
            "job_name": "Test Job 2",
        }
        result = _normalize_job(job, "FINISHED")

        assert result["jobId"] == "job-456"
        assert result["jobStatus"] == "FINISHED"
        assert result["jobName"] == "Test Job 2"

    def test_normalize_job_with_id_field(self):
        """测试id字段"""
        job = {
            "id": "job-789",
        }
        result = _normalize_job(job, "RUNNING")

        assert result["jobId"] == "job-789"

    def test_normalize_job_fallback_to_job_id(self):
        """测试jobName回退到job_id"""
        job = {
            "jobId": "job-999",
        }
        result = _normalize_job(job, "RUNNING")

        assert result["jobName"] == "job-999"

    def test_normalize_job_not_dict(self):
        """测试非dict输入"""
        result = _normalize_job(None, "RUNNING")
        assert result == {}

        result = _normalize_job("string", "RUNNING")
        assert result == {}


class TestFetchSeatunnel:
    """测试fetch_seatunnel函数"""

    @pytest.mark.asyncio
    async def test_fetch_get_success(self):
        """测试GET请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_seatunnel("/test/path", method="GET")

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_post_success(self):
        """测试POST请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobId": "123"}

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_seatunnel("/test/path", method="POST", json_data={"key": "value"})

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_delete_success(self):
        """测试DELETE请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.delete.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_seatunnel("/test/path", method="DELETE")

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """测试超时异常"""
        import httpx

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await fetch_seatunnel("/test/path", method="GET")

            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_fetch_connect_error(self):
        """测试连接错误"""
        import httpx

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await fetch_seatunnel("/test/path", method="GET")

            assert exc_info.value.status_code == 503


class TestListJobsEndpoint:
    """测试list_jobs端点"""

    @pytest.mark.asyncio
    async def test_list_jobs_all(self):
        """测试列出所有任务"""
        # Mock running jobs
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "job-1": {"jobName": "Running Job 1"},
            "job-2": {"jobName": "Running Job 2"},
        }

        # Mock finished jobs
        finished_response = MagicMock()
        finished_response.status_code = 200
        finished_response.json.return_value = [
            {"jobId": "job-3", "jobStatus": "FINISHED"},
        ]

        call_count = [0]

        async def mock_fetch(path, method="GET", json_data=None):
            call_count[0] += 1
            if "running-jobs" in path:
                return running_response
            else:
                return finished_response

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', side_effect=mock_fetch):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs")

                assert response.status_code == 200
                result = response.json()
                assert result["code"] == 20000
                assert "jobs" in result["data"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_jobs_running_only(self):
        """测试只列出运行中的任务"""
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"jobId": "job-1", "jobName": "Running Job"},
        ]

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=running_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs?status=running")

                assert response.status_code == 200
                result = response.json()
                assert len(result["data"]["jobs"]) == 1
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_jobs_finished_only(self):
        """测试只列出已完成的任务"""
        finished_response = MagicMock()
        finished_response.status_code = 200
        finished_response.json.return_value = [
            {"jobId": "job-1", "jobStatus": "FINISHED"},
        ]

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=finished_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs?status=finished")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()


class TestGetJobDetailEndpoint:
    """测试get_job_detail端点"""

    @pytest.mark.asyncio
    async def test_get_job_detail_found(self):
        """测试获取任务详情成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobId": "job-123", "jobName": "Test Job"}

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs/job-123")

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["jobId"] == "job-123"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_job_detail_not_found(self):
        """测试任务不存在"""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs/nonexistent")

                assert response.status_code == 200
                result = response.json()
                assert result["code"] != 20000
            finally:
                app.dependency_overrides.clear()


class TestGetJobStatusEndpoint:
    """测试get_job_status端点"""

    @pytest.mark.asyncio
    async def test_get_job_status_running(self):
        """测试获取运行中任务状态"""
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "job-123": {"jobName": "Test Job"}
        }

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=running_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs/job-123/status")

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["jobStatus"] == "RUNNING"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_job_status_finished(self):
        """测试获取已完成任务状态"""
        # Running jobs - empty
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {}

        # Finished jobs - has the job
        finished_response = MagicMock()
        finished_response.status_code = 200
        finished_response.json.return_value = {
            "job-123": {"jobStatus": "SUCCESS"}
        }

        call_count = [0]

        async def mock_fetch(path, method="GET", json_data=None):
            call_count[0] += 1
            if "running-jobs" in path:
                return running_response
            else:
                return finished_response

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', side_effect=mock_fetch):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/jobs/job-123/status")

                assert response.status_code == 200
                result = response.json()
                assert result["data"]["jobStatus"] == "SUCCESS"
            finally:
                app.dependency_overrides.clear()


class TestSubmitJobEndpoint:
    """测试submit_job端点"""

    @pytest.mark.asyncio
    async def test_submit_job_success(self):
        """测试提交任务成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobId": "new-job-123"}
        mock_response.text = ""

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/proxy/seatunnel/v1/jobs",
                    json={"jobName": "New Job"}
                )

                assert response.status_code == 200
                result = response.json()
                assert result["code"] == 20000
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_job_failure(self):
        """测试提交任务失败"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/proxy/seatunnel/v1/jobs",
                    json={"jobName": "New Job"}
                )

                assert response.status_code == 200
                result = response.json()
                assert result["code"] != 20000
            finally:
                app.dependency_overrides.clear()


class TestCancelJobEndpoint:
    """测试cancel_job端点"""

    @pytest.mark.asyncio
    async def test_cancel_job_success(self):
        """测试取消任务成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.delete("/api/proxy/seatunnel/v1/jobs/job-123")

                assert response.status_code == 200
                result = response.json()
                assert result["code"] == 20000
            finally:
                app.dependency_overrides.clear()


class TestGetClusterStatusEndpoint:
    """测试get_cluster_status端点"""

    @pytest.mark.asyncio
    async def test_get_cluster_status_success(self):
        """测试获取集群状态成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [
                {"address": "192.168.1.1:5701", "state": "ACTIVE"}
            ]
        }

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/v1/cluster")

                assert response.status_code == 200
                result = response.json()
                assert result["code"] == 20000
                assert "members" in result["data"]
            finally:
                app.dependency_overrides.clear()


class TestLegacyEndpoints:
    """测试旧版端点"""

    @pytest.mark.asyncio
    async def test_list_jobs_legacy(self):
        """测试旧版列出任务"""
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {}

        finished_response = MagicMock()
        finished_response.status_code = 200
        finished_response.json.return_value = []

        call_count = [0]

        async def mock_fetch(path, method="GET", json_data=None):
            call_count[0] += 1
            if "running-jobs" in path:
                return running_response
            else:
                return finished_response

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', side_effect=mock_fetch):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/api/v1/job/list")

                assert response.status_code == 200
                result = response.json()
                assert "jobs" in result
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cluster_status_legacy(self):
        """测试旧版集群状态"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "ACTIVE"}

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)

            from services.portal.routers.seatunnel import get_current_user
            app.dependency_overrides[get_current_user] = mock_get_current_user
            try:
                client = TestClient(app)
                response = client.get("/api/proxy/seatunnel/api/v1/cluster/status")

                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()
