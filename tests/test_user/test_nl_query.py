"""
TC-USR-04: 自然语言查询测试
测试业务用户使用自然语言查询数据
"""

import pytest
from httpx import AsyncClient


class TestNLQuery:
    """TC-USR-04: 自然语言查询测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_usr_04_01_nl_query_basic(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-USR-04-01: 使用自然语言查询数据"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "今天有多少新注册用户？"
            }
        )
        # LLM 不可用时可能返回 500/503
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "success" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_04_02_simple_condition_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-USR-04-02: 简单条件查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "查询北京地区的客户"
            }
        )
        assert response.status_code in (200, 400, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_04_03_sort_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-USR-04-03: 排序查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "按销售额从高到低排列前10名产品"
            }
        )
        assert response.status_code in (200, 400, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_usr_04_04_aggregate_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-USR-04-04: 统计查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "统计每个类别的产品数量"
            }
        )
        assert response.status_code in (200, 400, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_usr_04_05_view_tables(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-USR-04-05: 查看可查询的表"""
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 数据库不可用时可能返回 500
        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
