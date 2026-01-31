"""
超级管理员测试 - 账号创建阶段

测试用例: TC-SUP-01-*
"""

import pytest
from httpx import AsyncClient


@pytest.mark.super_admin
@pytest.mark.p0
async def test_super_admin_login(portal_client: AsyncClient, super_admin_token: str):
    """TC-SUP-01-02: 超级管理员首次登录"""
    response = await portal_client.post(
        "/auth/login",
        json={"username": "super_admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["role"] == "super_admin"


@pytest.mark.super_admin
@pytest.mark.p0
async def test_super_admin_permissions(portal_client: AsyncClient, super_admin_headers: dict):
    """TC-SUP-01-04: 验证超级管理员权限范围"""
    response = await portal_client.get(
        "/auth/permissions",
        headers=super_admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    # 验证拥有所有权限
    expected_permissions = [
        "data:read", "data:write", "data:delete",
        "pipeline:read", "pipeline:run", "pipeline:manage",
        "system:admin", "system:user:manage", "system:config",
        "metadata:read", "metadata:write",
        "sensitive:read", "sensitive:manage",
        "audit:read",
    ]
    for perm in expected_permissions:
        assert perm in data["permissions"]


@pytest.mark.super_admin
@pytest.mark.p0
async def test_super_admin_can_view_subsystems(portal_client: AsyncClient, super_admin_headers: dict):
    """TC-SUP-04-02-01: 查看子系统状态"""
    response = await portal_client.get(
        "/api/subsystems",
        headers=super_admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.super_admin
@pytest.mark.p0
async def test_super_admin_health_check(portal_client: AsyncClient):
    """TC-COM-01-02-02: Portal 健康检查"""
    response = await portal_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "portal"
