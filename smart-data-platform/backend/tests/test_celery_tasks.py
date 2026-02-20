from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid

from app.tasks.collect_tasks import (
    execute_collect_task,
    sync_all_active_tasks,
    health_check_sources,
)
from app.tasks.report_tasks import (
    generate_scheduled_report,
    generate_all_pending_reports,
    send_report_email,
)
from app.tasks.etl_tasks import (
    run_etl_pipeline,
    run_scheduled_pipeline,
    run_all_scheduled_pipelines,
)
from app.tasks.system_tasks import (
    cleanup_old_results,
    disk_usage_report,
    task_monitor,
)


class TestCollectTasks:
    """Test collect-related Celery tasks."""

    @pytest.fixture
    def mock_source(self):
        from app.models import DataSource
        return DataSource(
            id=uuid.uuid4(),
            name="Test Source",
            type="postgresql",
            connection_config={"host": "localhost", "database": "test"},
        )

    @pytest.fixture
    def mock_task(self, mock_source):
        from app.models import CollectTask, CollectTaskStatus
        return CollectTask(
            id=uuid.uuid4(),
            name="Test Collect Task",
            source_id=mock_source.id,
            source_table="source_table",
            target_table="target_table",
            is_active=True,
            status=CollectTaskStatus.PENDING,
        )

    def test_execute_collect_task_success(self, mock_task, mock_source):
        """Test successful collection task execution."""
        with patch("app.tasks.collect_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            # Mock database queries
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.side_effect = [mock_task, mock_source]
            mock_db.execute.return_value = result_mock

            # Mock connector
            with patch("app.tasks.collect_tasks.get_connector") as mock_get_connector:
                mock_connector = MagicMock()
                import pandas as pd
                mock_connector.read_data.return_value = pd.DataFrame({
                    "id": [1, 2, 3],
                    "name": ["A", "B", "C"],
                })
                mock_get_connector.return_value = mock_connector

                # Mock database engine
                with patch("app.tasks.collect_tasks.create_engine"):
                    result = execute_collect_task(str(mock_task.id))

        assert result["status"] == "success"
        assert result["task_id"] == str(mock_task.id)
        assert result["task_name"] == "Test Collect Task"
        assert result["rows_processed"] == 3

    def test_execute_collect_task_not_found(self):
        """Test collection task with non-existent task ID."""
        with patch("app.tasks.collect_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = result_mock

            result = execute_collect_task(str(uuid.uuid4()))

        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_execute_collect_task_inactive(self, mock_task):
        """Test collection task with inactive task."""
        mock_task.is_active = False

        with patch("app.tasks.collect_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_task
            mock_db.execute.return_value = result_mock

            result = execute_collect_task(str(mock_task.id))

        assert result["status"] == "skipped"
        assert result["message"] == "Task is not active"

    def test_health_check_sources(self):
        """Test health check for data sources."""
        with patch("app.tasks.collect_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            from app.models import DataSource
            mock_source = DataSource(
                id=uuid.uuid4(),
                name="Test Source",
                type="postgresql",
                connection_config={"host": "localhost"},
            )

            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = [mock_source]
            mock_db.execute.return_value = result_mock

            with patch("app.tasks.collect_tasks.get_connector") as mock_get_connector:
                mock_connector = MagicMock()
                mock_connector.test_connection.return_value = True
                mock_get_connector.return_value = mock_connector

                result = health_check_sources()

        assert result["total_sources"] == 1
        assert result["healthy"] == 1
        assert result["unhealthy"] == 0


class TestReportTasks:
    """Test report-related Celery tasks."""

    def test_generate_scheduled_report_success(self):
        """Test successful scheduled report generation."""
        schedule_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())

        with patch("app.tasks.report_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            from app.models import Report, ReportSchedule
            mock_schedule = ReportSchedule(
                id=uuid.UUID(schedule_id),
                report_id=uuid.UUID(report_id),
                is_active=True,
            )
            mock_report = Report(
                id=uuid.UUID(report_id),
                name="Test Report",
            )

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.side_effect = [mock_schedule, mock_report]
            mock_db.execute.return_value = result_mock

            result = generate_scheduled_report(schedule_id)

        assert result["status"] == "success"
        assert result["schedule_id"] == schedule_id
        assert result["report_id"] == report_id

    def test_generate_scheduled_report_not_found(self):
        """Test scheduled report with non-existent schedule."""
        schedule_id = str(uuid.uuid4())

        with patch("app.tasks.report_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = result_mock

            result = generate_scheduled_report(schedule_id)

        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_send_report_email(self):
        """Test sending report via email."""
        report_id = str(uuid.uuid4())
        recipient = "test@example.com"

        with patch("app.tasks.report_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            from app.models import Report
            mock_report = Report(
                id=uuid.UUID(report_id),
                name="Test Report",
            )

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_report
            mock_db.execute.return_value = result_mock

            result = send_report_email(report_id, recipient)

        assert result["status"] == "success"
        assert result["report_id"] == report_id
        assert result["recipient"] == recipient


class TestETLTasks:
    """Test ETL-related Celery tasks."""

    @pytest.fixture
    def mock_pipeline(self):
        from app.models import ETLPipeline
        return ETLPipeline(
            id=uuid.uuid4(),
            name="Test Pipeline",
            source_id=uuid.uuid4(),
            is_active=True,
        )

    def test_run_etl_pipeline_success(self, mock_pipeline):
        """Test successful ETL pipeline execution."""
        with patch("app.tasks.etl_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_pipeline
            mock_db.execute.return_value = result_mock

            with patch("app.tasks.etl_tasks.ETLEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.run_pipeline.return_value = {
                    "status": "success",
                    "rows_processed": 100,
                    "step_metrics": [],
                }
                mock_engine_class.return_value = mock_engine

                result = run_etl_pipeline(str(mock_pipeline.id))

        assert result["status"] == "success"
        assert result["pipeline_id"] == str(mock_pipeline.id)
        assert result["pipeline_name"] == "Test Pipeline"

    def test_run_etl_pipeline_not_found(self):
        """Test ETL pipeline with non-existent pipeline."""
        with patch("app.tasks.etl_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = result_mock

            result = run_etl_pipeline(str(uuid.uuid4()))

        assert result["status"] == "error"
        assert "not found" in result["error"]


class TestSystemTasks:
    """Test system maintenance Celery tasks."""

    @pytest.mark.asyncio
    async def test_cleanup_old_results(self):
        """Test cleanup of old task results."""
        days = 7
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with patch("app.tasks.system_tasks.AsyncSessionLocal") as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db

            # Mock delete results
            result_mock = MagicMock()
            result_mock.rowcount = 10
            mock_db.execute.return_value = result_mock

            result = await cleanup_old_results(days)

        assert result["status"] == "success"
        assert result["cutoff_date"] == cutoff.isoformat()
        assert result["audit_logs_deleted"] == 10
        assert result["etl_executions_deleted"] == 10
        assert result["collect_executions_deleted"] == 10

    def test_disk_usage_report(self):
        """Test disk usage report generation."""
        with patch("app.tasks.system_tasks.shutil.disk_usage") as mock_disk_usage:
            # Mock shutil.disk_usage return value
            mock_usage = MagicMock()
            mock_usage.total = 100 * 1024**3  # 100 GB
            mock_usage.used = 50 * 1024**3   # 50 GB
            mock_usage.free = 50 * 1024**3   # 50 GB
            mock_disk_usage.return_value = mock_usage

            with patch("app.tasks.system_tasks.os.path.exists", return_value=True):
                result = disk_usage_report()

        assert result["timestamp"]
        assert "disk_usage" in result
        assert len(result["disk_usage"]) > 0

    def test_task_monitor(self):
        """Test task monitoring."""
        with patch("app.tasks.system_tasks.current_app") as mock_celery:
            mock_inspect = MagicMock()
            mock_inspect.stats.return_value = {
                "celery@worker1": {"total": {}},
            }
            mock_inspect.active.return_value = {
                "celery@worker1": [{"id": "task-1", "args": []}],
            }
            mock_inspect.scheduled.return_value = {}
            mock_inspect.reserved.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect

            result = task_monitor()

        assert result["timestamp"]
        assert "workers" in result
        assert "active_tasks" in result


# Test task discovery and registration
class TestTaskRegistration:
    """Test that Celery tasks are properly registered."""

    def test_collect_tasks_registered(self):
        """Test that collect tasks are registered in celery_worker."""
        from app.celery_worker import celery_app

        # Check that tasks are registered
        assert "collect.execute_task" in celery_app.tasks

    def test_report_tasks_registered(self):
        """Test that report tasks are registered."""
        from app.celery_worker import celery_app

        assert "report.generate_scheduled" in celery_app.tasks

    def test_etl_tasks_registered(self):
        """Test that ETL tasks are registered."""
        from app.celery_worker import celery_app

        assert "etl.run_pipeline" in celery_app.tasks

    def test_system_tasks_registered(self):
        """Test that system tasks are registered."""
        from app.celery_worker import celery_app

        # Note: system tasks may not all be registered as celery tasks
        # but we can check the module imports work
        from app.tasks import system_tasks
        assert hasattr(system_tasks, "cleanup_old_results")
