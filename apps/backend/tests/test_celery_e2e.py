"""End-to-end tests for Celery task scheduling and execution.

These tests verify the complete workflow from API request to task execution.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import (
    DataSource,
    CollectTask,
    CollectTaskStatus,
    User,
    UserRole,
)


# Skip these tests if not in Celery mode
pytestmark = pytest.mark.skipif(
    os.getenv("USE_CELERY", "false").lower() != "true",
    reason="Celery E2E tests require USE_CELERY=true"
)


@pytest.fixture
async def auth_headers() -> dict[str, str]:
    """Create authenticated headers for API requests."""
    async with AsyncSessionLocal() as db:
        # Create admin user
        user = User(
            email="e2e_test@example.com",
            hashed_password="hashed",
            full_name="E2E Test",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()

        # Create JWT token
        from app.core.security import create_access_token
        token = create_access_token({"sub": user.email})
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_data_source(auth_headers: dict[str, str]) -> DataSource:
    """Create a test data source."""
    async with AsyncSessionLocal() as db:
        source = DataSource(
            name="E2E Test Source",
            type="postgresql",
            connection_config={
                "host": "localhost",
                "port": 3102,
                "database": "test_db",
                "user": "test",
                "password": "test",
            },
            is_active=True,
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)
        return source


@pytest.mark.asyncio
class TestCeleryTaskScheduling:
    """Test Celery task scheduling workflows."""

    async def test_schedule_collection_task(self, async_client: AsyncClient, test_data_source: DataSource) -> None:
        """Test scheduling a collection task via API."""
        # Create task
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "E2E Test Task",
                "source_id": str(test_data_source.id),
                "source_table": "test_table",
                "target_table": "target_table",
                "schedule_cron": "0 0 * * *",  # Daily at midnight
                "is_active": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "E2E Test Task"
        assert data["schedule_cron"] == "0 0 * * *"

        # Verify job was added to scheduler
        from app.services.scheduler_service import SchedulerService

        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            status = await scheduler_svc.get_job_status(uuid.UUID(data["id"]))
            assert status["is_scheduled"] is True
            assert status["scheduler"] == "celery"

    async def test_pause_and_resume_task(self, async_client: AsyncClient, test_data_source: DataSource) -> None:
        """Test pausing and resuming a scheduled task."""
        # Create task
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "Pause Test Task",
                "source_id": str(test_data_source.id),
                "source_table": "test_table",
                "target_table": "target_table",
                "schedule_cron": "0 * * * *",
                "is_active": True,
            },
        )
        task_id = response.json()["id"]

        # Pause task
        response = await async_client.post(f"/api/v1/collect/tasks/{task_id}/pause")
        assert response.status_code == 200

        # Verify task is paused
        from app.services.scheduler_service import SchedulerService

        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            status = await scheduler_svc.get_job_status(uuid.UUID(task_id))
            assert status["is_scheduled"] is False  # Not in beat schedule

        # Resume task
        response = await async_client.post(f"/api/v1/collect/tasks/{task_id}/resume")
        assert response.status_code == 200

        # Verify task is resumed
        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            status = await scheduler_svc.get_job_status(uuid.UUID(task_id))
            assert status["is_scheduled"] is True

    async def test_remove_scheduled_task(self, async_client: AsyncClient, test_data_source: DataSource) -> None:
        """Test removing a scheduled task."""
        # Create task
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "Remove Test Task",
                "source_id": str(test_data_source.id),
                "source_table": "test_table",
                "target_table": "target_table",
                "schedule_cron": "0 0 * * *",
                "is_active": True,
            },
        )
        task_id = response.json()["id"]

        # Remove schedule
        response = await async_client.delete(f"/api/v1/collect/tasks/{task_id}/schedule")
        assert response.status_code == 200

        # Verify schedule was removed
        from app.services.scheduler_service import SchedulerService

        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            status = await scheduler_svc.get_job_status(uuid.UUID(task_id))
            assert status["is_scheduled"] is False

    async def test_list_scheduled_jobs(self, async_client: AsyncClient, test_data_source: DataSource) -> None:
        """Test listing all scheduled jobs."""
        # Create multiple tasks
        for i in range(3):
            await async_client.post(
                "/api/v1/collect/tasks",
                json={
                    "name": f"List Test Task {i}",
                    "source_id": str(test_data_source.id),
                    "source_table": "test_table",
                    "target_table": f"target_table_{i}",
                    "schedule_cron": f"{i} * * * *",
                    "is_active": True,
                },
            )

        # List jobs
        from app.services.scheduler_service import SchedulerService

        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            jobs = await scheduler_svc.list_jobs()
            assert jobs["total"] >= 3
            assert jobs["scheduler"] == "celery"
            assert len(jobs["jobs"]) >= 3

    async def test_sync_jobs_from_database(self, async_client: AsyncClient, test_data_source: DataSource) -> None:
        """Test syncing jobs from database on startup."""
        # Create tasks directly in database
        async with AsyncSessionLocal() as db:
            for i in range(2):
                task = CollectTask(
                    name=f"Sync Test Task {i}",
                    source_id=test_data_source.id,
                    source_table="test_table",
                    target_table=f"target_table_{i}",
                    schedule_cron=f"{i} * * * *",
                    is_active=True,
                    status=CollectTaskStatus.PENDING,
                )
                db.add(task)
            await db.commit()

        # Sync jobs
        from app.services.scheduler_service import SchedulerService

        async with AsyncSessionLocal() as db:
            scheduler_svc = SchedulerService(db)
            result = await scheduler_svc.sync_jobs_from_database()
            assert result["synced"] >= 2
            assert result["scheduler"] == "celery"


@pytest.mark.asyncio
class TestCeleryTaskExecution:
    """Test Celery task execution."""

    @patch("app.tasks.collect_tasks.get_connector")
    async def test_execute_collect_task_success(
        self,
        mock_get_connector: Mock,
        async_client: AsyncClient,
        test_data_source: DataSource,
    ) -> None:
        """Test successful execution of a collect task."""
        # Mock connector
        import pandas as pd
        from app.connectors import BaseConnector

        mock_connector = Mock(spec=BaseConnector)
        mock_connector.read_data.return_value = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"],
        })
        mock_connector.test_connection.return_value = True
        mock_get_connector.return_value = mock_connector

        # Create task
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "Execute Test Task",
                "source_id": str(test_data_source.id),
                "source_table": "test_table",
                "target_table": "target_table",
                "is_active": True,
            },
        )
        task_id = response.json()["id"]

        # Execute task directly via Celery
        from app.tasks.collect_tasks import execute_collect_task

        result = execute_collect_task(task_id)
        assert result["status"] == "success"
        assert result["task_id"] == task_id
        assert result["rows_processed"] == 3

    @patch("app.tasks.collect_tasks.get_connector")
    async def test_execute_collect_task_failure(
        self,
        mock_get_connector: Mock,
        async_client: AsyncClient,
        test_data_source: DataSource,
    ) -> None:
        """Test failed execution of a collect task."""
        # Mock connector to raise error
        from app.connectors import BaseConnector

        mock_connector = Mock(spec=BaseConnector)
        mock_connector.read_data.side_effect = Exception("Connection failed")
        mock_get_connector.return_value = mock_connector

        # Create task
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "Fail Test Task",
                "source_id": str(test_data_source.id),
                "source_table": "test_table",
                "target_table": "target_table",
                "is_active": True,
            },
        )
        task_id = response.json()["id"]

        # Execute task
        from app.tasks.collect_tasks import execute_collect_task

        result = execute_collect_task(task_id)
        assert result["status"] == "error"
        assert "error" in result


@pytest.mark.asyncio
class TestCeleryHealthChecks:
    """Test Celery health check endpoints."""

    async def test_health_check_sources(self) -> None:
        """Test health check for data sources."""
        from app.tasks.system_tasks import health_check_sources

        result = health_check_sources()
        assert "total_sources" in result
        assert "healthy" in result
        assert "unhealthy" in result

    async def test_task_monitor(self) -> None:
        """Test task monitoring."""
        from app.tasks.system_tasks import task_monitor

        result = task_monitor()
        assert "timestamp" in result
        assert "workers" in result
        assert "active_tasks" in result


@pytest.fixture
async def async_client() -> AsyncClient:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
