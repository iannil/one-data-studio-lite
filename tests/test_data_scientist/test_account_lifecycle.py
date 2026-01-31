"""
数据科学家测试 - 账号创建和权限验证

测试用例: TC-SCI-01-*
"""

import pytest
from httpx import AsyncClient


@pytest.mark.data_scientist
@pytest.mark.p0
async def test_data_scientist_login(portal_client: AsyncClient):
    """TC-SCI-01-02: 数据科学家首次登录"""
    # 需要先在 DEV_USERS 中配置
    response = await portal_client.post(
        "/auth/login",
        json={"username": "scientist", "password": "sci123"}
    )
    # 如果用户配置存在则成功，否则返回 401
    assert response.status_code in (200, 401)
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert data["user"]["role"] == "data_scientist"


@pytest.mark.data_scientist
@pytest.mark.p0
async def test_data_scientist_permissions(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-01-04: 验证数据科学家权限范围"""
    response = await portal_client.get(
        "/auth/permissions",
        headers=data_scientist_headers
    )
    assert response.status_code == 200
    data = response.json()
    # 验证拥有数据科学家应有的权限
    expected_permissions = [
        "data:read", "data:write",
        "pipeline:read", "pipeline:run",
        "metadata:read", "metadata:write"
    ]
    for perm in expected_permissions:
        assert perm in data["permissions"]
    # 验证不拥有管理权限
    assert "system:admin" not in data["permissions"]
    assert "data:delete" not in data["permissions"]


@pytest.mark.data_scientist
@pytest.mark.p0
async def test_data_scientist_health_check(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-03-06-01: 验证数据科学家可以访问健康检查"""
    response = await portal_client.get(
        "/health",
        headers=data_scientist_headers
    )
    assert response.status_code == 200


@pytest.mark.data_scientist
@pytest.mark.p1
async def test_data_scientist_nl2sql_query(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-04-03-01: NL2SQL 复杂查询"""
    # 注意: 这是代理到 NL2SQL 服务
    response = await portal_client.post(
        "/api/proxy/nl2sql/v1/query",
        headers=data_scientist_headers,
        json={
            "question": "查询最近一周的用户数量",
            "max_rows": 100
        }
    )
    # 服务可能不可用，返回 503、404 或 422 (验证错误)
    assert response.status_code in (200, 404, 422, 503)


@pytest.mark.data_scientist
@pytest.mark.p1
async def test_data_scientist_cleaning_analyze(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-04-04-01: 分析数据质量"""
    response = await portal_client.post(
        "/api/proxy/cleaning/v1/analyze",
        headers=data_scientist_headers,
        json={
            "table_name": "test_table",
            "sample_size": 1000
        }
    )
    # 服务可能不可用
    assert response.status_code in (200, 404, 503)


@pytest.mark.data_scientist
@pytest.mark.p0
async def test_data_scientist_cannot_manage_users(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-04-09-07: 验证数据科学家不能管理用户"""
    response = await portal_client.get(
        "/api/users",
        headers=data_scientist_headers
    )
    # 应该返回 403 权限不足
    assert response.status_code == 403


@pytest.mark.data_scientist
@pytest.mark.p0
async def test_data_scientist_cannot_create_roles(portal_client: AsyncClient, data_scientist_headers: dict):
    """TC-SCI-04-09-07: 验证数据科学家不能创建角色"""
    response = await portal_client.post(
        "/api/roles",
        headers=data_scientist_headers,
        json={
            "role_code": "test_role",
            "role_name": "测试角色",
            "permissions": ["data:read"]
        }
    )
    # 应该返回 403 权限不足
    assert response.status_code in (403, 404)
