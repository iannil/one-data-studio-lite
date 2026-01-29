"""
TC-COM-02: 认证授权测试
测试登录、登出、Token 验证等认证功能
"""

import pytest
from httpx import AsyncClient


class TestAuth:
    """TC-COM-02: 认证授权测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_02_01_login_success(self, portal_client: AsyncClient):
        """TC-COM-02-01: 正常登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"]  # token 非空
        assert data["user"]["user_id"] == "admin"
        assert data["user"]["role"] == "admin"
        assert data["message"] == "登录成功"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_02_02_login_wrong_password(self, portal_client: AsyncClient):
        """TC-COM-02-02: 错误密码登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "用户名或密码错误"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_02_03_login_nonexistent_user(self, portal_client: AsyncClient):
        """TC-COM-02-03: 不存在的用户登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "anypassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "用户名或密码错误"

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_com_02_04_login_empty_password(self, portal_client: AsyncClient):
        """TC-COM-02-04: 空密码登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": ""}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "用户名或密码错误"

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_com_02_05_logout(self, portal_client: AsyncClient):
        """TC-COM-02-05: 登出"""
        response = await portal_client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "已登出"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_02_06_no_auth_access_protected(self, nl2sql_client: AsyncClient):
        """TC-COM-02-06: 无认证访问受保护接口"""
        response = await nl2sql_client.get("/api/nl2sql/tables")
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "未提供认证信息"

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_02_07_invalid_token_access(self, nl2sql_client: AsyncClient):
        """TC-COM-02-07: 无效 Token 访问受保护接口"""
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "无效" in data["detail"] or "令牌" in data["detail"]

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_com_02_08_expired_token_access(
        self, nl2sql_client: AsyncClient, expired_token: str
    ):
        """TC-COM-02-08: 过期 Token 访问受保护接口"""
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "过期" in data["detail"]

    @pytest.mark.asyncio
    @pytest.mark.p0
    @pytest.mark.integration
    async def test_com_02_09_valid_token_access(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-COM-02-09: 有效 Token 访问受保护接口"""
        # 这个测试需要数据库连接，可能会失败
        # 但验证的是认证通过，不是 500 认证错误
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 认证通过意味着不是 401
        assert response.status_code != 401
