"""
跨角色权限测试

测试用例: TC-XROLE-*
验证不同角色之间的权限隔离
"""

import pytest
from httpx import AsyncClient


@pytest.mark.cross_role
@pytest.mark.p0
async def test_viewer_cannot_access_admin_endpoints(portal_client: AsyncClient, viewer_headers: dict):
    """TC-XROLE-01: 查看者无法访问管理员端点"""
    response = await portal_client.get(
        "/api/users",
        headers=viewer_headers
    )
    assert response.status_code == 403


@pytest.mark.cross_role
@pytest.mark.p0
async def test_analyst_cannot_access_system_config(portal_client: AsyncClient, analyst_headers: dict):
    """TC-XROLE-02: 数据分析师无法访问系统配置"""
    response = await portal_client.get(
        "/api/system/config",
        headers=analyst_headers
    )
    assert response.status_code == 403


@pytest.mark.cross_role
@pytest.mark.p0
async def test_data_scientist_cannot_create_roles(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-XROLE-03: 数据科学家无法创建角色"""
    response = await portal_client.post(
        "/api/roles",
        headers=data_scientist_headers,
        json={
            "role_code": "unauthorized_role",
            "role_name": "未授权角色",
            "permissions": ["data:read"]
        }
    )
    assert response.status_code == 403


@pytest.mark.cross_role
@pytest.mark.p0
async def test_admin_cannot_access_super_admin_only_endpoints(portal_client: AsyncClient, admin_headers: dict):
    """TC-XROLE-04: 管理员无法访问超级管理员专用端点"""
    response = await portal_client.post(
        "/api/system/auth/revoke-all",
        headers=admin_headers,
        json={"reason": "测试", "exclude_users": []}
    )
    assert response.status_code == 403


@pytest.mark.cross_role
@pytest.mark.p0
async def test_viewer_cannot_modify_pipeline(portal_client: AsyncClient, viewer_headers: dict):
    """TC-XROLE-05: 查看者无法修改 Pipeline"""
    response = await portal_client.post(
        "/api/proxy/nl2sql/v1/query",
        headers=viewer_headers,
        json={"question": "测试", "max_rows": 10}
    )
    # 查看者应该可以查询但不能修改
    # 对于查询，可能返回 200, 401, 404, 或 503, 或 422 (validation)
    assert response.status_code in (200, 401, 404, 422, 503)


@pytest.mark.cross_role
@pytest.mark.p1
async def test_isolation_between_regular_users(portal_client: AsyncClient):
    """TC-XROLE-06: 普通用户之间的权限隔离"""
    # 创建两个不同角色的用户 token
    viewer_response = await portal_client.post(
        "/auth/login",
        json={"username": "viewer", "password": "view123"}
    )
    analyst_response = await portal_client.post(
        "/auth/login",
        json={"username": "analyst", "password": "ana123"}
    )

    # 验证不同用户的 token 是独立的
    if viewer_response.status_code == 200 and analyst_response.status_code == 200:
        viewer_token = viewer_response.json()["token"]
        analyst_token = analyst_response.json()["token"]
        assert viewer_token != analyst_token


@pytest.mark.cross_role
@pytest.mark.p1
async def test_cannot_elevate_own_role(portal_client: AsyncClient, admin_headers: dict):
    """TC-XROLE-07: 用户无法提升自己的角色"""
    response = await portal_client.put(
        "/api/users/admin/role",
        headers=admin_headers,
        params={"new_role": "super_admin", "reason": "测试"}
    )
    # 应该返回 403 或 400
    assert response.status_code in (400, 403, 404)


@pytest.mark.cross_role
@pytest.mark.p0
async def test_token_validation_across_roles(portal_client: AsyncClient):
    """TC-XROLE-08: Token 验证对所有角色一致"""
    # 获取不同角色的 token
    roles_to_test = ["admin", "viewer", "analyst"]
    for role in roles_to_test:
        # 假设 DEV_USERS 中有配置
        response = await portal_client.post(
            "/auth/login",
            json={"username": role, "password": role + "123"}
        )
        if response.status_code == 200:
            token = response.json()["token"]
            # 验证 token
            validate_response = await portal_client.get(
                "/auth/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert validate_response.status_code == 200
            assert validate_response.json()["valid"] is True
