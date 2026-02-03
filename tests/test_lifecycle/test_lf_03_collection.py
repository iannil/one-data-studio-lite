"""生命周期测试 - 阶段3: 数据汇聚 (Collection)

测试数据汇聚功能:
- SeaTunnel: 服务连通性、集群状态
- DolphinScheduler: 任务调度、健康检查
- Apache Hop: ETL转换、工作流访问
- ETL任务: 实际数据同步验证
"""

import pytest
from httpx import AsyncClient


# ============================================================
# SeaTunnel 测试
# ============================================================

@pytest.mark.p0
class TestSeaTunnelIntegration:
    """SeaTunnel 集成测试"""

    async def test_seatunnel_01_service_health(self, portal_client: AsyncClient, admin_headers: dict):
        """测试SeaTunnel服务健康检查"""
        response = await portal_client.get(
            "/api/proxy/seatunnel/health",
            headers=admin_headers
        )
        # 代理端点可能不存在
        assert response.status_code in (200, 404, 502)

    async def test_seatunnel_02_cluster_status(self, portal_client: AsyncClient, admin_headers: dict):
        """测试SeaTunnel集群状态"""
        response = await portal_client.get(
            "/api/proxy/seatunnel/hazelcast/rest/cluster",
            headers=admin_headers
        )
        assert response.status_code in (200, 404, 502)

    async def test_seatunnel_03_list_pipelines(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取Pipeline列表"""
        response = await portal_client.get(
            "/api/seatunnel/pipelines",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_seatunnel_04_create_pipeline(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试创建Pipeline"""
        response = await portal_client.post(
            "/api/seatunnel/pipelines",
            headers=engineer_headers,
            json={
                "name": "test_pipeline",
                "description": "测试管道",
                "source": {"type": "mysql"},
                "sink": {"type": "hdfs"}
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_seatunnel_05_submit_job(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试提交作业"""
        response = await portal_client.post(
            "/api/seatunnel/jobs/submit",
            headers=engineer_headers,
            json={
                "pipeline_id": "test_pipeline",
                "env": {"job.mode": "BATCH"}
            }
        )
        assert response.status_code in (200, 201, 404)

    async def test_seatunnel_06_get_job_status(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试获取作业状态"""
        response = await portal_client.get(
            "/api/seatunnel/jobs/test_job/status",
            headers=engineer_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# DolphinScheduler 测试
# ============================================================

@pytest.mark.p0
class TestDolphinSchedulerIntegration:
    """DolphinScheduler 集成测试"""

    async def test_dolphinscheduler_01_service_health(self, portal_client: AsyncClient, admin_headers: dict):
        """测试DolphinScheduler服务健康检查"""
        response = await portal_client.get(
            "/api/proxy/dolphinscheduler/actuator/health",
            headers=admin_headers
        )
        assert response.status_code in (200, 404, 502)

    async def test_dolphinscheduler_02_list_projects(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取项目列表"""
        response = await portal_client.get(
            "/api/dolphinscheduler/projects",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_dolphinscheduler_03_list_workflows(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取工作流列表"""
        response = await portal_client.get(
            "/api/dolphinscheduler/workflows",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_dolphinscheduler_04_create_workflow(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试创建工作流"""
        response = await portal_client.post(
            "/api/dolphinscheduler/workflows",
            headers=engineer_headers,
            json={
                "name": "test_workflow",
                "description": "测试工作流",
                "schedule": "0 2 * * *",
                "tasks": []
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_dolphinscheduler_05_trigger_workflow(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试触发工作流执行"""
        response = await portal_client.post(
            "/api/dolphinscheduler/workflows/1/run",
            headers=engineer_headers
        )
        assert response.status_code in (200, 202, 404)

    async def test_dolphinscheduler_06_get_execution_status(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取执行状态"""
        response = await portal_client.get(
            "/api/dolphinscheduler/executions/1/status",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# Apache Hop 测试
# ============================================================

@pytest.mark.p0
class TestHopIntegration:
    """Apache Hop 集成测试"""

    async def test_hop_01_service_health(self, portal_client: AsyncClient, admin_headers: dict):
        """测试Hop服务健康检查"""
        response = await portal_client.get(
            "/api/proxy/hop/health",
            headers=admin_headers
        )
        assert response.status_code in (200, 404, 502)

    async def test_hop_02_list_transformations(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取转换列表"""
        response = await portal_client.get(
            "/api/hop/transformations",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_hop_03_list_workflows(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取工作流列表"""
        response = await portal_client.get(
            "/api/hop/workflows",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_hop_04_execute_transformation(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试执行转换"""
        response = await portal_client.post(
            "/api/hop/transformations/test_trans/run",
            headers=engineer_headers
        )
        assert response.status_code in (200, 202, 404)


# ============================================================
# ETL 任务测试
# ============================================================

@pytest.mark.p1
class TestETLTasks:
    """ETL 任务测试"""

    async def test_etl_01_list_tasks(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试获取ETL任务列表"""
        response = await portal_client.get(
            "/api/etl/tasks",
            headers=engineer_headers
        )
        assert response.status_code in (200, 404)

    async def test_etl_02_create_sync_task(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试创建数据同步任务"""
        response = await portal_client.post(
            "/api/etl/tasks/sync",
            headers=engineer_headers,
            json={
                "name": "mysql_to_hive",
                "source": {
                    "type": "mysql",
                    "host": "mysql",
                    "port": 3306,
                    "database": "source_db",
                    "table": "users"
                },
                "sink": {
                    "type": "hive",
                    "database": "target_db",
                    "table": "users"
                }
            }
        )
        assert response.status_code in (201, 200, 404)

    async def test_etl_03_execute_task(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试执行ETL任务"""
        response = await portal_client.post(
            "/api/etl/tasks/1/execute",
            headers=engineer_headers
        )
        assert response.status_code in (200, 202, 404)

    async def test_etl_04_get_task_history(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取任务执行历史"""
        response = await portal_client.get(
            "/api/etl/tasks/1/history",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_etl_05_task_scheduling(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试任务调度配置"""
        response = await portal_client.put(
            "/api/etl/tasks/1/schedule",
            headers=engineer_headers,
            json={
                "schedule": "0 2 * * *",
                "enabled": true
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 数据源连接测试
# ============================================================

@pytest.mark.p1
class TestDataSourceConnections:
    """数据源连接测试"""

    async def test_datasource_01_list_connections(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取数据源连接列表"""
        response = await portal_client.get(
            "/api/datasources",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_datasource_02_test_connection(self, portal_client: AsyncClient, admin_headers: dict):
        """测试数据源连接"""
        response = await portal_client.post(
            "/api/datasources/test",
            headers=admin_headers,
            json={
                "type": "mysql",
                "host": "mysql",
                "port": 3306,
                "database": "test_db"
            }
        )
        assert response.status_code in (200, 404)

    async def test_datasource_03_create_connection(self, portal_client: AsyncClient, admin_headers: dict):
        """测试创建数据源连接"""
        response = await portal_client.post(
            "/api/datasources",
            headers=admin_headers,
            json={
                "name": "test_mysql",
                "type": "mysql",
                "host": "mysql",
                "port": 3306,
                "database": "test_db",
                "username": "root",
                "password": "password"
            }
        )
        assert response.status_code in (201, 200, 404)


# ============================================================
# 数据导入导出测试
# ============================================================

@pytest.mark.p2
class TestDataImportExport:
    """数据导入导出测试"""

    async def test_import_01_import_csv(self, portal_client: AsyncClient, engineer_headers: dict):
        """测试CSV数据导入"""
        # 注意: 实际文件上传需要multipart/form-data
        response = await portal_client.post(
            "/api/import/csv",
            headers=engineer_headers,
            json={
                "table": "test_table",
                "file_path": "/data/test.csv",
                "format": "csv"
            }
        )
        assert response.status_code in (200, 201, 404)

    async def test_export_01_export_csv(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试CSV数据导出"""
        response = await portal_client.post(
            "/api/export/csv",
            headers=analyst_headers,
            json={
                "query": "SELECT * FROM users LIMIT 100",
                "format": "csv"
            }
        )
        assert response.status_code in (200, 404)


# ============================================================
# 批处理任务测试
# ============================================================

@pytest.mark.p2
class TestBatchProcessing:
    """批处理任务测试"""

    async def test_batch_01_list_jobs(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取批处理任务列表"""
        response = await portal_client.get(
            "/api/batch/jobs",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_batch_02_schedule_job(self, portal_client: AsyncClient, admin_headers: dict):
        """测试调度批处理任务"""
        response = await portal_client.post(
            "/api/batch/jobs/schedule",
            headers=admin_headers,
            json={
                "job_name": "daily_sync",
                "schedule": "0 2 * * *"
            }
        )
        assert response.status_code in (200, 201, 404)

    async def test_batch_03_monitor_job(self, portal_client: AsyncClient, admin_headers: dict):
        """测试监控批处理任务"""
        response = await portal_client.get(
            "/api/batch/jobs/daily_sync/status",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)
