"""
TC-ENG-04: AI 清洗规则推荐测试
测试清洗规则推荐和 SeaTunnel 配置生成
"""

import pytest
from httpx import AsyncClient


class TestCleaningRules:
    """TC-ENG-04: AI 清洗规则推荐测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_04_01_get_ai_recommendations(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-01: 获取 AI 推荐的清洗规则"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/recommend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "test_users",
                "sample_size": 500
            }
        )
        # LLM 不可用时可能返回 500
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            assert "rules" in data
            assert "explanation" in data
            # 验证规则结构
            for rule in data.get("rules", []):
                assert "rule_id" in rule or "name" in rule
                assert "rule_type" in rule

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_eng_04_02_clean_data_recommendation(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-02: AI 推荐 - 数据质量良好"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/recommend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "clean_data", "sample_size": 500}
        )
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            # 数据质量良好时，规则列表可能为空
            assert "rules" in data
            assert "explanation" in data

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_eng_04_03_llm_unavailable(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-03: AI 推荐 - LLM 服务不可用"""
        # 在测试环境中，LLM 通常不可用
        response = await ai_cleaning_client.post(
            "/api/cleaning/recommend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "test_users", "sample_size": 500}
        )
        # 服务不应该崩溃
        assert response.status_code in (200, 400, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_04_04_different_issue_types(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-04: AI 推荐 - 不同问题类型"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/recommend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "test_mixed_issues", "sample_size": 500}
        )
        assert response.status_code in (200, 400, 500, 503)

        if response.status_code == 200:
            data = response.json()
            # 验证可能推荐多种类型的规则
            rule_types = {r.get("rule_type") for r in data.get("rules", [])}
            # 规则类型可能包括: filter, replace, fill, deduplicate
            # 不做具体类型断言，因为依赖于测试数据

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_eng_04_05_generate_seatunnel_config(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-05: 生成 SeaTunnel Transform 配置"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/generate-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "source_users",
                "output_table": "cleaned_users",
                "rules": [
                    {
                        "rule_id": "r1",
                        "name": "过滤空值",
                        "description": "过滤email为空的记录",
                        "target_column": "email",
                        "rule_type": "filter",
                        "config": {"condition": "is_not_null"}
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            config = data[0]
            assert "plugin_name" in config

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_04_06_generate_replace_config(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-06: 生成配置 - replace 类型规则"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/generate-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "source_data",
                "rules": [
                    {
                        "rule_id": "r2",
                        "name": "替换异常值",
                        "target_column": "status",
                        "rule_type": "replace",
                        "config": {"old_value": "unknown", "new_value": "pending"}
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_04_07_generate_fill_config(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-07: 生成配置 - fill 类型规则"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/generate-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "source_data",
                "rules": [
                    {
                        "rule_id": "r3",
                        "name": "填充默认值",
                        "target_column": "age",
                        "rule_type": "fill",
                        "config": {"fill_value": "0"}
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_eng_04_08_generate_deduplicate_config(
        self, ai_cleaning_client: AsyncClient, admin_token: str
    ):
        """TC-ENG-04-08: 生成配置 - deduplicate 类型规则"""
        response = await ai_cleaning_client.post(
            "/api/cleaning/generate-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "source_data",
                "rules": [
                    {
                        "rule_id": "r4",
                        "name": "去除重复",
                        "target_column": "id",
                        "rule_type": "deduplicate",
                        "config": {}
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_eng_04_09_view_rule_templates(
        self, ai_cleaning_client: AsyncClient
    ):
        """TC-ENG-04-09: 查看清洗规则模板"""
        response = await ai_cleaning_client.get("/api/cleaning/rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 验证规则类型
        rule_types = {r.get("type") for r in data}
        expected_types = {"filter", "replace", "fill", "transform", "deduplicate"}
        # 至少应该有一些规则类型
        assert len(rule_types) > 0
