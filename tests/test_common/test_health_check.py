"""
TC-COM-01: 健康检查测试
测试所有服务的健康检查端点
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """TC-COM-01: 健康检查测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_01_portal_home(self, portal_client: AsyncClient):
        """TC-COM-01-01: Portal 门户首页访问"""
        response = await portal_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ONE-DATA-STUDIO-LITE"
        assert data["version"] == "0.1.0"
        assert "subsystems" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_02_portal_health(self, portal_client: AsyncClient):
        """TC-COM-01-02: Portal 健康检查"""
        response = await portal_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "portal"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_03_nl2sql_health(self, nl2sql_client: AsyncClient):
        """TC-COM-01-03: NL2SQL 服务健康检查"""
        response = await nl2sql_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nl2sql"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_04_ai_cleaning_health(self, ai_cleaning_client: AsyncClient):
        """TC-COM-01-04: AI Cleaning 服务健康检查"""
        response = await ai_cleaning_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-cleaning"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_05_metadata_sync_health(self, metadata_sync_client: AsyncClient):
        """TC-COM-01-05: Metadata Sync 服务健康检查"""
        response = await metadata_sync_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "metadata-sync"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_06_data_api_health(self, data_api_client: AsyncClient):
        """TC-COM-01-06: Data API 服务健康检查"""
        response = await data_api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-api"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_07_sensitive_detect_health(self, sensitive_detect_client: AsyncClient):
        """TC-COM-01-07: Sensitive Detect 服务健康检查"""
        response = await sensitive_detect_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sensitive-detect"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_01_08_audit_log_health(self, audit_log_client: AsyncClient):
        """TC-COM-01-08: Audit Log 服务健康检查"""
        response = await audit_log_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audit-log"
