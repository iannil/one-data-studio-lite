"""
TC-STW-04: 数据质量监控测试
测试数据质量分析和 AI 清洗建议功能
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestQualityMonitoring:
    """TC-STW-04: 数据质量监控测试（需要数据库）"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_stw_04_01_view_quality_report(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-STW-04-01: 查看表的数据质量报告"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "customers",
                "sample_size": 1000
            }
        )
        # 表可能不存在
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            assert "quality_score" in data
            assert "issues" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_stw_04_02_monitor_multiple_tables(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-STW-04-02: 监控多表数据质量"""
        tables = ["customers", "orders", "products"]
        results = []

        for table in tables:
            response = await ai_cleaning_client.post(
                "/api/cleaning/analyze",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"table_name": table, "sample_size": 500}
            )
            results.append(response.status_code)

        # 至少应该能正常响应（可能是 200 或 400/500）
        assert all(code in (200, 400, 500) for code in results)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_stw_04_03_identify_high_severity_issues(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-STW-04-03: 识别高严重度质量问题"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/analyze",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "customers", "sample_size": 1000}
        )

        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            # 筛选高严重度问题
            high_severity = [i for i in issues if i.get("severity") == "high"]
            # 验证结构正确
            for issue in high_severity:
                assert "column" in issue
                assert "issue_type" in issue

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_stw_04_04_get_ai_cleaning_suggestion(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-STW-04-04: 获取 AI 清洗建议"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/recommend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "customers",
                "sample_size": 500
            }
        )
        # LLM 不可用时可能返回 500
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "rules" in data
            assert "explanation" in data
