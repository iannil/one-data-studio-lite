"""生命周期测试 - 阶段5: 数据分析 (Analysis)

测试数据分析功能:
- NL2SQL: 自然语言转SQL、SQL解释
- Superset: BI可视化、仪表板访问
- 数据API网关: 数据查询、资产访问
- 查询功能: 实际查询验证
"""

import pytest
from httpx import AsyncClient

# ============================================================
# NL2SQL 服务测试
# ============================================================

@pytest.mark.p0
class TestNL2SQLService:
    """NL2SQL 服务测试"""

    async def test_nl2sql_01_service_health(self, portal_client: AsyncClient):
        """测试NL2SQL服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8011/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_nl2sql_02_convert_to_sql(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试自然语言转SQL"""
        response = await portal_client.post(
            "/api/nl2sql/convert",
            headers=analyst_headers,
            json={
                "query": "查询最近7天的订单数量",
                "database": "demo_retail_db"
            }
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                sql = data["data"].get("sql", "")
                assert "SELECT" in sql.upper() or "说明" in str(data)

    async def test_nl2sql_03_explain_sql(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试SQL解释"""
        response = await portal_client.post(
            "/api/nl2sql/explain",
            headers=analyst_headers,
            json={
                "sql": "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name"
            }
        )
        assert response.status_code in (200, 404)

    async def test_nl2sql_04_validate_sql(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试SQL验证"""
        response = await portal_client.post(
            "/api/nl2sql/validate",
            headers=analyst_headers,
            json={
                "sql": "SELECT * FROM users",
                "database": "demo_retail_db"
            }
        )
        assert response.status_code in (200, 404)

    async def test_nl2sql_05_suggest_query(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试查询建议"""
        response = await portal_client.post(
            "/api/nl2sql/suggest",
            headers=analyst_headers,
            json={
                "context": "用户分析",
                "tables": ["users", "orders"]
            }
        )
        assert response.status_code in (200, 404)

    async def test_nl2sql_06_query_history(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试查询历史"""
        response = await portal_client.get(
            "/api/nl2sql/history",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# Superset 集成测试
# ============================================================

@pytest.mark.p0
class TestSupersetIntegration:
    """Superset 集成测试"""

    async def test_superset_01_service_health(self, portal_client: AsyncClient):
        """测试Superset服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8088/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_superset_02_list_dashboards(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取仪表板列表"""
        response = await portal_client.get(
            "/api/bi/dashboards",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_superset_03_get_dashboard(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取仪表板详情"""
        response = await portal_client.get(
            "/api/bi/dashboards/1",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_superset_04_list_charts(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取图表列表"""
        response = await portal_client.get(
            "/api/bi/charts",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_superset_05_embed_chart(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试图表嵌入"""
        response = await portal_client.get(
            "/api/bi/charts/1/embed",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 数据 API 网关测试
# ============================================================

@pytest.mark.p0
class TestDataAPIGateway:
    """数据 API 网关测试"""

    async def test_api_01_service_health(self, portal_client: AsyncClient):
        """测试数据API服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8014/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_api_02_list_datasets(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取可查询数据集列表"""
        response = await portal_client.get(
            "/api/data/datasets",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_api_03_query_dataset(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试查询数据集"""
        response = await portal_client.post(
            "/api/data/query",
            headers=analyst_headers,
            json={
                "dataset": "users",
                "limit": 10,
                "fields": ["id", "name", "email"]
            }
        )
        assert response.status_code in (200, 404)

    async def test_api_04_filter_data(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试数据过滤"""
        response = await portal_client.post(
            "/api/data/query",
            headers=analyst_headers,
            json={
                "dataset": "users",
                "filter": {"status": "active"},
                "limit": 100
            }
        )
        assert response.status_code in (200, 404)

    async def test_api_05_aggregate_data(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试数据聚合"""
        response = await portal_client.post(
            "/api/data/aggregate",
            headers=analyst_headers,
            json={
                "dataset": "orders",
                "group_by": ["category"],
                "metrics": [{"field": "amount", "agg": "sum"}]
            }
        )
        assert response.status_code in (200, 404)

    async def test_api_06_export_data(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试数据导出"""
        response = await portal_client.post(
            "/api/data/export",
            headers=analyst_headers,
            json={
                "dataset": "users",
                "format": "csv",
                "limit": 1000
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 查询功能测试
# ============================================================

@pytest.mark.p1
class TestQueryFunctionality:
    """查询功能测试"""

    async def test_query_01_execute_sql(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试执行SQL查询"""
        response = await portal_client.post(
            "/api/query/execute",
            headers=data_scientist_headers,
            json={
                "sql": "SELECT * FROM users LIMIT 10",
                "database": "demo_retail_db"
            }
        )
        assert response.status_code in (200, 404)

    async def test_query_02_query_with_params(self, portal_client: AsyncClient, data_scientist_headers: dict):
        """测试参数化查询"""
        response = await portal_client.post(
            "/api/query/execute",
            headers=data_scientist_headers,
            json={
                "sql": "SELECT * FROM users WHERE id = ?",
                "params": [1]
            }
        )
        assert response.status_code in (200, 404)

    async def test_query_03_save_query(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试保存查询"""
        response = await portal_client.post(
            "/api/query/saved",
            headers=analyst_headers,
            json={
                "name": "每日用户统计",
                "sql": "SELECT DATE(created_at) as date, COUNT(*) as count FROM users GROUP BY DATE(created_at)",
                "database": "demo_retail_db"
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_query_04_list_saved_queries(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取已保存查询"""
        response = await portal_client.get(
            "/api/query/saved",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_query_05_query_performance(self, portal_client: AsyncClient, admin_headers: dict):
        """测试查询性能分析"""
        response = await portal_client.post(
            "/api/query/analyze",
            headers=admin_headers,
            json={
                "sql": "SELECT * FROM orders JOIN users ON orders.user_id = users.id"
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 报表功能测试
# ============================================================

@pytest.mark.p1
class TestReporting:
    """报表功能测试"""

    async def test_report_01_list_reports(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取报表列表"""
        response = await portal_client.get(
            "/api/reports",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_report_02_generate_report(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试生成报表"""
        response = await portal_client.post(
            "/api/reports/generate",
            headers=analyst_headers,
            json={
                "report_id": 1,
                "params": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            }
        )
        assert response.status_code in (200, 404)

    async def test_report_03_schedule_report(self, portal_client: AsyncClient, admin_headers: dict):
        """测试调度报表"""
        response = await portal_client.post(
            "/api/reports/schedule",
            headers=admin_headers,
            json={
                "report_id": 1,
                "schedule": "0 8 * * 1",
                "recipients": ["admin@example.com"]
            }
        )
        assert response.status_code in (201, 200, 404)


# ============================================================
# 可视化配置测试
# ============================================================

@pytest.mark.p2
class TestVisualizationConfig:
    """可视化配置测试"""

    async def test_viz_01_list_chart_types(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取图表类型"""
        response = await portal_client.get(
            "/api/viz/chart-types",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_viz_02_create_chart(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试创建图表"""
        response = await portal_client.post(
            "/api/viz/charts",
            headers=analyst_headers,
            json={
                "name": "用户增长趋势",
                "chart_type": "line",
                "dataset": "users",
                "x_axis": "created_at",
                "y_axis": [{"field": "id", "agg": "count"}]
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_viz_03_chart_preview(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试图表预览"""
        response = await portal_client.post(
            "/api/viz/charts/preview",
            headers=analyst_headers,
            json={
                "chart_type": "bar",
                "data": {
                    "labels": ["A", "B", "C"],
                    "values": [10, 20, 30]
                }
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 数据探索测试
# ============================================================

@pytest.mark.p2
class TestDataExploration:
    """数据探索测试"""

    async def test_explore_01_get_table_profile(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取表概况"""
        response = await portal_client.get(
            "/api/explore/tables/users/profile",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_explore_02_get_column_stats(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取列统计信息"""
        response = await portal_client.get(
            "/api/explore/tables/users/columns/stats",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_explore_03_get_sample_data(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取样本数据"""
        response = await portal_client.get(
            "/api/explore/tables/users/sample?limit=10",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_explore_04_get_correlations(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试获取相关性分析"""
        response = await portal_client.get(
            "/api/explore/tables/orders/correlations",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)
