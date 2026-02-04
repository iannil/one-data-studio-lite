"""Unit tests for portal seatunnel router

Tests for services/portal/routers/seatunnel.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from services.common.api_response import ErrorCode
from services.common.auth import TokenPayload
from services.portal.routers.seatunnel import (
    _normalize_job,
    cancel_job,
    fetch_seatunnel,
    get_cluster_status,
    get_job_detail,
    get_job_status,
    list_jobs,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/seatunnel"


class TestFetchSeatunnel:
    """测试 fetch_seatunnel 辅助函数"""

    @pytest.mark.asyncio
    async def test_fetch_seatunnel_get_success(self):
        """测试成功 GET 请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient', return_value=mock_client):
            result = await fetch_seatunnel("/test")

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_seatunnel_post_success(self):
        """测试成功 POST 请求"""
        mock_response = MagicMock()
        mock_response.status_code = 201

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient', return_value=mock_client):
            result = await fetch_seatunnel("/test", method="POST", json_data={"key": "value"})

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_fetch_seatunnel_timeout(self):
        """测试请求超时"""
        class MockClient:
            async def get(self, *args, **kwargs):
                raise httpx.TimeoutException("Timeout")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(HTTPException) as exc_info:
                await fetch_seatunnel("/test")

            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_fetch_seatunnel_connect_error(self):
        """测试连接错误"""
        class MockClient:
            async def get(self, *args, **kwargs):
                raise httpx.ConnectError("Connection failed")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('services.portal.routers.seatunnel.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(HTTPException) as exc_info:
                await fetch_seatunnel("/test")

            assert exc_info.value.status_code == 503


class TestNormalizeJob:
    """测试任务数据标准化"""

    def test_normalize_job_with_jobId(self):
        """测试标准化包含 jobId 的任务"""
        job = {
            "jobId": "job-123",
            "jobName": "Test Job",
            "createTime": "2023-01-01T00:00:00",
        }
        result = _normalize_job(job, "RUNNING")

        assert result["jobId"] == "job-123"
        assert result["jobStatus"] == "RUNNING"
        assert result["jobName"] == "Test Job"

    def test_normalize_job_with_job_id(self):
        """测试标准化包含 job_id 的任务"""
        job = {
            "job_id": "job-456",
            "job_name": "Test Job 2",
            "create_time": "2023-01-01T00:00:00",
        }
        result = _normalize_job(job, "FINISHED")

        assert result["jobId"] == "job-456"
        assert result["jobStatus"] == "FINISHED"
        # When job_name exists, it should be used as jobName
        assert result["jobName"] == "Test Job 2"

    def test_normalize_job_with_id(self):
        """测试标准化包含 id 的任务"""
        job = {
            "id": "job-789",
            "name": "Test Job 3",
        }
        result = _normalize_job(job, "RUNNING")

        assert result["jobId"] == "job-789"
        assert result["jobStatus"] == "RUNNING"

    def test_normalize_job_non_dict(self):
        """测试非字典任务"""
        result = _normalize_job("not a dict", "RUNNING")
        assert result == {}


class TestListJobs:
    """测试获取任务列表"""

    @pytest.mark.asyncio
    async def test_list_jobs_all(self):
        """测试获取所有任务"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_running_response = MagicMock()
        mock_running_response.status_code = 200
        mock_running_response.json.return_value = {}

        mock_finished_response = MagicMock()
        mock_finished_response.status_code = 200
        mock_finished_response.json.return_value = {}

        with patch('services.portal.routers.seatunnel.fetch_seatunnel') as mock_fetch:
            mock_fetch.side_effect = [mock_running_response, mock_finished_response]

            result = await list_jobs(status=None, user=mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_list_jobs_running_only(self):
        """测试仅获取运行中任务"""
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
            {"jobId": "job-1", "jobName": "Running Job 1"}
        ]

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            result = await list_jobs(status="running", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetJobDetail:
    """测试获取任务详情"""

    @pytest.mark.asyncio
    async def test_get_job_detail_success(self):
        """测试成功获取任务详情"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobId": "job-123"}

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            result = await get_job_detail(job_id="job-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetJobStatus:
    """测试获取任务状态"""

    @pytest.mark.asyncio
    async def test_get_job_status_success(self):
        """测试成功获取任务状态"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return data with the job_id in running jobs
        mock_response.json.return_value = {"job-123": {"jobId": "job-123"}}

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            result = await get_job_status(job_id="job-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestCancelJob:
    """测试取消任务"""

    @pytest.mark.asyncio
    async def test_cancel_job_success(self):
        """测试成功取消任务"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            result = await cancel_job(job_id="job-123", user=mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestGetClusterStatus:
    """测试获取集群状态"""

    @pytest.mark.asyncio
    async def test_get_cluster_status_success(self):
        """测试成功获取集群状态"""
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
            "cluster": "healthy",
            "nodes": ["node1", "node2"]
        }

        with patch('services.portal.routers.seatunnel.fetch_seatunnel', return_value=mock_response):
            result = await get_cluster_status(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
