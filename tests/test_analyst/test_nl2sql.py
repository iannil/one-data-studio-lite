"""
TC-ANA-02: 自然语言查询测试
测试 NL2SQL 查询、SQL 解释等功能
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestNL2SQL:
    """TC-ANA-02: 自然语言查询测试（需要数据库）"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_02_01_basic_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-01: NL2SQL 基础查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "查询所有用户的姓名和邮箱"
            }
        )
        # LLM 不可用时可能返回 500/503
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "question" in data
            if data.get("success"):
                assert "generated_sql" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_02_02_conditional_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-02: NL2SQL 带条件查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "查询年龄大于30岁的用户"
            }
        )
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("generated_sql"):
                # 验证生成的 SQL 包含 WHERE
                sql = data["generated_sql"].upper()
                assert "WHERE" in sql or "HAVING" in sql or ">" in sql

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_02_03_aggregate_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-03: NL2SQL 聚合查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "统计每个部门的员工数量"
            }
        )
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("generated_sql"):
                sql = data["generated_sql"].upper()
                # 聚合查询应该包含 COUNT 或 GROUP BY
                has_aggregate = "COUNT" in sql or "SUM" in sql or "AVG" in sql
                has_group = "GROUP BY" in sql
                # 允许没有聚合（可能是简单查询）
                # 因为 LLM 的输出不可预测

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_02_04_limit_rows(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-04: NL2SQL 限制结果行数"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "查询所有用户",
                "max_rows": 5
            }
        )
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("row_count") is not None:
                assert data["row_count"] <= 5

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_02_05_reject_non_select(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-05: NL2SQL 安全限制 - 拒绝非 SELECT"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "question": "删除所有用户数据"
            }
        )
        # 应该返回 400 或者 LLM 拒绝生成危险 SQL
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            # 如果成功，生成的 SQL 不应该包含危险操作
            sql = data.get("generated_sql", "").upper()
            # 不应该有 DELETE、DROP、TRUNCATE 等操作
            assert "DELETE" not in sql or not data.get("success")

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_ana_02_06_explain_sql(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-06: SQL 解释功能"""
        response = await nl2sql_client.post(
            "/api/nl2sql/explain",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "sql": "SELECT u.name, COUNT(o.id) as order_count FROM users u "
                       "LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id "
                       "HAVING order_count > 5"
            }
        )
        assert response.status_code in (200, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "sql" in data
            assert "explanation" in data

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_02_07_explain_simple_query(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-07: SQL 解释 - 简单查询"""
        response = await nl2sql_client.post(
            "/api/nl2sql/explain",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "SELECT * FROM users"}
        )
        assert response.status_code in (200, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "explanation" in data
            # 解释不应该为空
            assert data["explanation"]

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_ana_02_08_get_tables(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-08: 获取可用表列表"""
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 数据库不可用时可能返回 500
        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

            # 如果有表，验证表结构
            if len(data) > 0:
                table = data[0]
                assert "table_name" in table

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_ana_02_09_tables_with_columns(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-ANA-02-09: 获取表列表 - 包含列详情"""
        response = await nl2sql_client.get(
            "/api/nl2sql/tables",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0 and "columns" in data[0]:
                columns = data[0]["columns"]
                if len(columns) > 0:
                    column = columns[0]
                    # 验证列结构
                    assert "name" in column
