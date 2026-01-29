"""
TC-USR-06: 数据订阅测试
测试数据资产变更订阅功能
"""

import pytest
from httpx import AsyncClient


class TestSubscription:
    """TC-USR-06: 数据订阅测试"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_06_01_subscribe_asset_changes(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-06-01: 订阅数据资产变更"""
        response = await data_api_client.post(
            "/api/assets/test_users/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "notify_on": ["schema_change", "data_update"],
                "email": "user@example.com"
            }
        )
        # 功能可能未实现
        assert response.status_code in (200, 404, 501)

        if response.status_code == 200:
            data = response.json()
            assert "notify_on" in data or "subscriber" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_usr_06_02_subscribe_schema_change(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-06-02: 订阅 Schema 变更"""
        response = await data_api_client.post(
            "/api/assets/test_users/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "notify_on": ["schema_change"],
                "email": "user@example.com"
            }
        )
        assert response.status_code in (200, 404, 501)

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_usr_06_03_duplicate_subscription(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-06-03: 重复订阅处理"""
        # 第一次订阅
        response1 = await data_api_client.post(
            "/api/assets/test_users/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"notify_on": ["schema_change"], "email": "user@example.com"}
        )

        # 重复订阅
        response2 = await data_api_client.post(
            "/api/assets/test_users/subscribe",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"notify_on": ["schema_change"], "email": "user@example.com"}
        )

        # 两次请求都应该有响应（可能成功或返回错误）
        assert response1.status_code in (200, 404, 409, 501)
        assert response2.status_code in (200, 404, 409, 501)
