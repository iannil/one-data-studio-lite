"""
TC-ENG-01: 数据工程师登录测试
"""

import pytest
from httpx import AsyncClient


class TestEngineerLogin:
    """TC-ENG-01: 数据工程师登录测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_01_01_login_system(self, portal_client: AsyncClient):
        """TC-ENG-01-01: 登录系统"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"]  # token 非空
