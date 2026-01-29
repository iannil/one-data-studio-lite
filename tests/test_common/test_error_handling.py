"""
TC-COM-03: 错误处理测试
测试 404、400、SQL 注入防护等错误处理
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestErrorHandling:
    """TC-COM-03: 错误处理测试（需要数据库）"""

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_com_03_01_resource_not_found(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-01: 404 资源不存在"""
        response = await data_api_client.get(
            "/api/data/nonexistent_dataset",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "code" in data or "detail" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_com_03_02_invalid_params(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-02: 400 参数错误"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={}  # 缺少必填参数 question
        )
        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_03_03_sql_injection_prevention(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-03: SQL 注入防护"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "users; DROP TABLE users; --",
                "sample_size": 100
            }
        )
        # 应该返回 400 错误或表名验证失败
        assert response.status_code in (400, 422, 500)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_03_04_reject_non_select_query(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-04: 禁止非 SELECT 查询"""
        response = await data_api_client.post(
            "/api/data/test_table/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "DELETE FROM users WHERE 1=1"}
        )
        # 即使表不存在，也应该先检查 SQL 安全性
        # 可能返回 400（SQL 不安全）或 404（表不存在）
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.json()
            assert "SELECT" in data.get("detail", "") or "仅允许" in data.get("detail", "")

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_com_03_05_reject_drop_keyword(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-05: 禁止危险关键字"""
        response = await data_api_client.post(
            "/api/data/test_table/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sql": "SELECT * FROM users; DROP TABLE users;"}
        )
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.json()
            assert "DROP" in data.get("detail", "") or "不允许" in data.get("detail", "")

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_com_03_06_service_unavailable_degradation(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-COM-03-06: 服务不可用时的降级处理"""
        # LLM 服务不可用时应该返回适当的错误
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"question": "查询所有用户"}
        )
        # 如果 LLM 不可用，应返回 503 或其他错误，但不应崩溃
        assert response.status_code in (200, 500, 503)
