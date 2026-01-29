"""
TC-ADM-04: 系统监控测试
测试门户运行信息和服务响应时间
"""

import pytest
from httpx import AsyncClient
import time


class TestMonitoring:
    """TC-ADM-04: 系统监控测试"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_04_01_view_portal_info(self, portal_client: AsyncClient):
        """TC-ADM-04-01: 查看门户运行信息"""
        response = await portal_client.get("/")
        assert response.status_code == 200
        data = response.json()

        # 验证响应包含必要字段
        assert "name" in data
        assert data["name"] == "ONE-DATA-STUDIO-LITE"
        assert "version" in data
        assert "subsystems" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_adm_04_02_monitor_response_time(self, portal_client: AsyncClient):
        """TC-ADM-04-02: 监控服务响应时间"""
        start_time = time.time()
        response = await portal_client.get("/health")
        end_time = time.time()

        assert response.status_code == 200

        # 响应时间应该小于 500ms
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        assert response_time < 500, f"响应时间 {response_time:.2f}ms 超过 500ms"
