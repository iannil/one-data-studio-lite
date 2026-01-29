"""
TC-ADM-03: 用户管理测试
测试用户角色权限验证
"""

import pytest
from httpx import AsyncClient


class TestUserManagement:
    """TC-ADM-03: 用户管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_adm_03_01_verify_role_permissions(
        self, audit_log_client: AsyncClient, admin_token: str
    ):
        """TC-ADM-03-01: 验证用户角色权限"""
        # 管理员应该可以访问审计日志
        response = await audit_log_client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 认证通过意味着不是 401
        assert response.status_code != 401
        # 正常情况应该返回 200
        assert response.status_code == 200
