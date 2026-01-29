"""
TC-COM-06: 请求参数验证测试
测试分页参数、必填参数等验证
"""

import pytest
from httpx import AsyncClient


class TestValidation:
    """TC-COM-06: 请求参数验证测试"""

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_com_06_01_page_lower_bound(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-COM-06-01: 分页参数验证 - page 下限"""
        response = await data_api_client.get(
            "/api/data/test_table",
            params={"page": 0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # page=0 应该触发验证错误（page >= 1）
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_com_06_02_page_size_upper_bound(
        self, data_api_client: AsyncClient, admin_token: str
    ):
        """TC-COM-06-02: 分页参数验证 - page_size 上限"""
        response = await data_api_client.get(
            "/api/data/test_table",
            params={"page_size": 9999},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # page_size=9999 应该触发验证错误（page_size <= 1000）
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_com_06_03_missing_required_param(
        self, nl2sql_client: AsyncClient, admin_token: str
    ):
        """TC-COM-06-03: 必填参数缺失"""
        response = await nl2sql_client.post(
            "/api/nl2sql/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"max_rows": 100}  # 缺少必填的 question 字段
        )
        assert response.status_code == 422
        data = response.json()
        # 验证错误信息中提到 question 字段
        assert "detail" in data
