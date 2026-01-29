"""
TC-COM-04: CORS 测试
测试跨域请求处理
"""

import pytest
from httpx import AsyncClient


class TestCORS:
    """TC-COM-04: CORS 测试"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_com_04_01_cors_preflight(self, portal_client: AsyncClient):
        """TC-COM-04-01: CORS 预检请求"""
        response = await portal_client.options(
            "/auth/login",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200
        # 检查 CORS 响应头
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_com_04_02_cors_with_credentials(self, portal_client: AsyncClient):
        """TC-COM-04-02: 跨域请求携带凭证"""
        response = await portal_client.post(
            "/auth/login",
            headers={
                "Origin": "http://example.com",
                "Content-Type": "application/json",
            },
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        # 检查响应中包含 CORS 头
        assert "access-control-allow-origin" in response.headers
