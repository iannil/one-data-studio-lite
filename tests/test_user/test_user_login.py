"""
TC-USR-01: 业务用户登录测试
测试业务用户登录和门户访问功能
"""

import pytest
from httpx import AsyncClient


class TestUserLogin:
    """TC-USR-01: 业务用户登录测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_01_01_user_login(self, portal_client: AsyncClient):
        """TC-USR-01-01: 业务用户登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_01_02_view_portal_home(self, portal_client: AsyncClient):
        """TC-USR-01-02: 查看门户首页"""
        response = await portal_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "subsystems" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_01_03_view_subsystems(
        self, portal_client: AsyncClient, admin_token: str
    ):
        """TC-USR-01-03: 查看可用子系统"""
        response = await portal_client.get(
            "/api/subsystems",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
