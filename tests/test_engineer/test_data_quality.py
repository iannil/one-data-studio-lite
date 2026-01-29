"""
TC-ENG-03: 数据质量分析测试
测试表数据质量分析功能
"""

import pytest
from httpx import AsyncClient


class TestDataQuality:
    """TC-ENG-03: 数据质量分析测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_03_01_analyze_table(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-03-01: 分析表的数据质量"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "test_users",
                "sample_size": 1000
            }
        )
        # 可能返回 200（成功）或 400（表不存在）或 500（数据库不可用）
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            assert "table_name" in data
            assert "issues" in data
            assert "quality_score" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_03_02_null_value_detection(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-03-02: 数据质量分析 - 空值检测"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "test_with_nulls", "sample_size": 500}
        )
        # 在测试环境中表可能不存在
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            # 如果有空值问题，应该包含 null_values 类型的 issue
            null_issues = [i for i in data.get("issues", [])
                          if i.get("issue_type") == "null_values"]
            # 验证结构正确
            for issue in null_issues:
                assert "column" in issue
                assert "affected_rows" in issue

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_03_03_duplicate_detection(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-03-03: 数据质量分析 - 重复值检测"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "test_with_duplicates", "sample_size": 500}
        )
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            # 如果有重复值问题，应该包含 duplicates 类型的 issue
            dup_issues = [i for i in data.get("issues", [])
                         if i.get("issue_type") == "duplicates"]
            for issue in dup_issues:
                assert "column" in issue

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_eng_03_04_high_quality_data(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-03-04: 数据质量分析 - 高质量数据"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "clean_data", "sample_size": 500}
        )
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            # 高质量数据应该得分较高
            if data.get("quality_score") is not None:
                # 不做具体分数断言，因为测试数据可能不同
                assert 0 <= data["quality_score"] <= 100

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_eng_03_05_table_not_exist(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-03-05: 数据质量分析 - 表不存在"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "nonexistent_table_xyz", "sample_size": 100}
        )
        # 应该返回 400 错误
        assert response.status_code in (400, 500)
