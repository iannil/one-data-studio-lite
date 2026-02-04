"""
TC-ADM-01: 管理员登录测试
测试管理员账号初始化和用户信息获取
"""

import base64
import json

import pytest
from httpx import AsyncClient


class TestAdminLogin:
    """TC-ADM-01: 管理员账号初始化测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_adm_01_01_admin_first_login(self, portal_client: AsyncClient):
        """TC-ADM-01-01: 管理员首次登录"""
        response = await portal_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"]  # token 非空
        assert data["user"]["role"] == "admin"
        assert data["user"]["display_name"] == "管理员"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_01_02_get_current_user_info(
        self, portal_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-01-02: 获取当前用户信息（通过解码 Token）"""
        # JWT token 格式: header.payload.signature
        # 解码 payload 部分
        parts = admin_token.split(".")
        assert len(parts) == 3, "Token 应该是有效的 JWT 格式"

        # 添加 padding 并解码
        payload_b64 = parts[1]
        # 添加必要的 padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # 验证 payload 内容
        assert payload.get("sub") == "admin"
        assert payload.get("username") == "admin"
        assert payload.get("role") == "admin"
        assert "exp" in payload  # 过期时间存在
