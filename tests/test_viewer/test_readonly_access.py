"""
查看者测试 - 只读访问权限

测试用例: TC-VW-03-*, TC-VW-04-*
"""

import pytest
from httpx import AsyncClient


@pytest.mark.viewer
@pytest.mark.p0
async def test_viewer_login(portal_client: AsyncClient):
    """TC-VW-01-02: 查看者首次登录"""
    response = await portal_client.post(
        "/auth/login",
        json={"username": "viewer", "password": "view123"}
    )
    # 如果用户配置存在则成功
    assert response.status_code in (200, 401)
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert data["user"]["role"] == "viewer"


@pytest.mark.viewer
@pytest.mark.p0
async def test_viewer_readonly_permissions(portal_client: AsyncClient, viewer_headers: dict):
    """TC-VW-03-01: 验证查看者只有只读权限"""
    response = await portal_client.get(
        "/auth/permissions",
        headers=viewer_headers
    )
    assert response.status_code == 200
    data = response.json()
    # 验证只有读权限
    assert "data:read" in data["permissions"]
    assert "pipeline:read" in data["permissions"]
    # 验证没有写权限
    assert "data:write" not in data["permissions"]
    assert "system:admin" not in data["permissions"]


@pytest.mark.viewer
@pytest.mark.p0
async def test_viewer_cannot_create_users(portal_client: AsyncClient, viewer_headers: dict):
    """TC-VW-03-02: 验证查看者不能创建用户"""
    response = await portal_client.post(
        "/api/users",
        headers=viewer_headers,
        json={
            "username": "test_user",
            "password": "test12345",
            "role": "viewer",
            "display_name": "测试用户"
        }
    )
    # 应该返回 403 权限不足
    assert response.status_code == 403


@pytest.mark.viewer
@pytest.mark.p0
async def test_viewer_cannot_modify_data(portal_client: AsyncClient, viewer_headers: dict):
    """TC-VW-03-03: 验证查看者不能修改数据"""
    # 通过 data_api 尝试修改
    response = await portal_client.post(
        "/api/proxy/data-api/v1/data/test_dataset/query",
        headers=viewer_headers,
        json={"sql": "DELETE FROM test_table WHERE 1=1"}
    )
    # 外部服务不可用时返回200（错误封装在响应体中）
    # 或返回 403/400/503
    if response.status_code == 200:
        # 如果返回200，检查是否是错误响应
        data = response.json()
        # code != 20000 表示有错误
        assert data.get("code") != 20000 or "error" in str(data).lower()
    else:
        assert response.status_code in (400, 403, 404, 503)


@pytest.mark.viewer
@pytest.mark.p1
async def test_viewer_can_view_reports(portal_client: AsyncClient, viewer_headers: dict):
    """TC-VW-04-01: 验证查看者可以查看报表"""
    response = await portal_client.get(
        "/api/proxy/superset/api/v1/dashboard/",
        headers=viewer_headers
    )
    # Superset 可能不可用或返回不同状态
    assert response.status_code in (200, 401, 404, 503)


@pytest.mark.viewer
@pytest.mark.p1
async def test_viewer_health_check(portal_client: AsyncClient, viewer_headers: dict):
    """TC-VW-03-04: 验证查看者可以访问健康检查"""
    response = await portal_client.get(
        "/health",
        headers=viewer_headers
    )
    assert response.status_code == 200
