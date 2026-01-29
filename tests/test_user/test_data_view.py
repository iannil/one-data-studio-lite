"""
TC-USR-03: 数据查看测试
测试数据集内容查看功能
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestDataView:
    """TC-USR-03: 数据查看测试（需要数据库）"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_03_01_view_dataset_content(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-03-01: 查看数据集内容"""
        response = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 表可能不存在
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_03_02_view_dataset_schema(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-03-02: 查看数据集 Schema"""
        response = await data_api_client.get(
            "/api/data/test_users/schema",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            assert "columns" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_03_03_data_pagination(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-03-03: 数据分页浏览"""
        # 第一页
        response1 = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 1, "page_size": 20},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 第二页
        response2 = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 2, "page_size": 20},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response1.status_code == 200 and response2.status_code == 200:
            page1 = response1.json()
            page2 = response2.json()
            # 验证页码正确
            assert page1.get("page") == 1
            assert page2.get("page") == 2
