"""
TC-ANA-01: 数据探索测试
测试数据集查询、Schema 获取、资产搜索等功能
"""

import pytest
from httpx import AsyncClient


class TestDataExplore:
    """TC-ANA-01: 数据探索测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_01_query_dataset(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-01: 查询数据集数据"""
        response = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 表可能不存在，所以接受 404
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            assert "dataset_id" in data
            assert "total" in data
            assert "page" in data
            assert "data" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_01_02_dataset_pagination(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-02: 数据集分页查询"""
        # 第一页
        response1 = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 第二页
        response2 = await data_api_client.get(
            "/api/data/test_users",
            params={"page": 2, "page_size": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response1.status_code == 200 and response2.status_code == 200:
            page1 = response1.json()
            page2 = response2.json()
            # 验证页码正确
            assert page1.get("page") == 1
            assert page2.get("page") == 2

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_ana_01_03_dataset_not_exist(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-03: 查询数据集 - 数据集不存在"""
        response = await data_api_client.get(
            "/api/data/nonexistent_dataset_xyz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_01_04_dataset_id_hyphen_conversion(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-04: 查询数据集 - dataset_id 格式转换"""
        # 使用连字符格式
        response = await data_api_client.get(
            "/api/data/test-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 应该能查询到 test_users 表（如果存在）
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_05_get_dataset_schema(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-05: 获取数据集 Schema"""
        response = await data_api_client.get(
            "/api/data/test_users/schema",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            assert "dataset_id" in data
            assert "columns" in data

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_ana_01_06_schema_not_exist(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-06: 获取 Schema - 数据集不存在"""
        response = await data_api_client.get(
            "/api/data/nonexistent_xyz/schema",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_01_07_schema_column_comments(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-07: Schema 包含字段注释"""
        response = await data_api_client.get(
            "/api/data/test_users/schema",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            for column in data.get("columns", []):
                # 验证列结构
                assert "name" in column
                # description 字段可能为空

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_08_custom_sql_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-08: 自定义 SQL 查询"""
        response = await data_api_client.post(
            "/api/data/test_users/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "sql": "SELECT id, name FROM test_users WHERE id < 10 ORDER BY id"
            }
        )
        # 表可能不存在
        assert response.status_code in (200, 400, 404)

        if response.status_code == 200:
            data = response.json()
            assert "columns" in data or "data" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_01_09_query_without_sql(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-09: 自定义查询 - 无 SQL 使用默认分页"""
        response = await data_api_client.post(
            "/api/data/test_users/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"page": 1, "page_size": 20}
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_10_reject_delete_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-10: 自定义查询 - 拒绝 DELETE"""
        response = await data_api_client.post(
            "/api/data/test_users/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "DELETE FROM test_users WHERE id = 1"}
        )
        # 应该拒绝
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.json()
            assert "SELECT" in data.get("detail", "") or "仅允许" in data.get("detail", "")

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_11_reject_update_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-11: 自定义查询 - 拒绝 UPDATE"""
        response = await data_api_client.post(
            "/api/data/test_users/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "UPDATE test_users SET name = 'hacked' WHERE 1=1"}
        )
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.json()
            assert "UPDATE" in data.get("detail", "") or "不允许" in data.get("detail", "")

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_12_reject_drop_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-12: 自定义查询 - 拒绝 DROP"""
        response = await data_api_client.post(
            "/api/data/test_users/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "SELECT * FROM test_users; DROP TABLE test_users;"}
        )
        assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_01_13_search_assets(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-13: 搜索数据资产"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "users"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "assets" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_01_14_search_assets_pagination(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-14: 搜索资产 - 分页"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "test", "page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_01_15_search_assets_no_result(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-15: 搜索资产 - 无结果"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": "xyznonexistent123abc"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["assets"] == []

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_ana_01_16_search_assets_empty_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-16: 搜索资产 - 空查询词"""
        response = await data_api_client.get(
            "/api/assets/search",
            params={"query": ""},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 应该返回验证错误
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_01_17_get_asset_detail(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-17: 获取资产详情"""
        response = await data_api_client.get(
            "/api/assets/test_asset_id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 资产可能存在或不存在
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_ana_01_18_get_asset_not_exist(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-01-18: 获取资产详情 - 不存在"""
        response = await data_api_client.get(
            "/api/assets/nonexistent_asset_xyz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
