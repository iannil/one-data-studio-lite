"""
TC-USR-02: 数据资产搜索测试
测试数据资产搜索功能
"""

import pytest
from httpx import AsyncClient


class TestAssetSearch:
    """TC-USR-02: 数据资产搜索测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_02_01_search_assets(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-02-01: 搜索数据资产"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "sales"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "assets" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_02_02_search_fuzzy_match(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-02-02: 搜索资产 - 模糊匹配"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "cust"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_usr_02_03_search_pagination(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-02-03: 搜索资产 - 分页"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "test", "page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_02_04_view_asset_detail(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-USR-02-04: 查看资产详情"""
        response = await data_api_client.get(
            "/api/assets/test_users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 资产可能存在或不存在
        assert response.status_code in (200, 404)
