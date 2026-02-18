"""Tests for scheduler service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import CollectTask, CollectTaskStatus
from app.services.scheduler_service import SchedulerService, get_next_run_times


class TestSchedulerService:
    """Test suite for SchedulerService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a SchedulerService instance with mock database."""
        return SchedulerService(mock_db)

    @pytest.fixture
    def sample_task(self):
        """Create a sample CollectTask for testing."""
        task = MagicMock(spec=CollectTask)
        task.id = uuid.uuid4()
        task.name = "Test Collection Task"
        task.source_id = uuid.uuid4()
        task.source_table = "test_source"
        task.target_table = "test_target"
        task.schedule_cron = "0 0 * * *"
        task.is_active = True
        task.is_incremental = False
        task.status = CollectTaskStatus.PENDING
        task.last_run_at = None
        task.last_success_at = None
        task.last_error = None
        return task

    def test_get_job_id(self, service):
        """Test job ID generation."""
        task_id = uuid.uuid4()
        job_id = service._get_job_id(task_id)
        assert job_id == f"collect_task_{task_id}"

    @pytest.mark.asyncio
    async def test_add_collect_job_task_not_found(self, service, mock_db):
        """Test adding a job for non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Collection task not found"):
            await service.add_collect_job(uuid.uuid4(), "0 0 * * *")

    @pytest.mark.asyncio
    async def test_add_collect_job_invalid_cron(self, service, mock_db, sample_task):
        """Test adding a job with invalid cron expression."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = None

            with pytest.raises(ValueError, match="Invalid cron expression"):
                await service.add_collect_job(sample_task.id, "invalid cron")

    @pytest.mark.asyncio
    async def test_add_collect_job_success(self, service, mock_db, sample_task):
        """Test successfully adding a scheduled job."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        mock_job = MagicMock()
        mock_job.next_run_time = datetime.now(timezone.utc)

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = None
            mock_scheduler.add_job.return_value = mock_job

            result = await service.add_collect_job(sample_task.id, "0 0 * * *")

            assert result["task_id"] == str(sample_task.id)
            assert result["task_name"] == sample_task.name
            assert result["cron_expression"] == "0 0 * * *"
            assert result["is_active"] is True
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_collect_job_replaces_existing(self, service, mock_db, sample_task):
        """Test adding a job replaces existing one."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        mock_existing_job = MagicMock()
        mock_new_job = MagicMock()
        mock_new_job.next_run_time = datetime.now(timezone.utc)

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = mock_existing_job
            mock_scheduler.add_job.return_value = mock_new_job

            result = await service.add_collect_job(sample_task.id, "0 0 * * *")

            mock_scheduler.remove_job.assert_called_once()
            assert result["cron_expression"] == "0 0 * * *"

    @pytest.mark.asyncio
    async def test_remove_collect_job_exists(self, service, mock_db):
        """Test removing an existing scheduled job."""
        task_id = uuid.uuid4()

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = MagicMock()

            result = await service.remove_collect_job(task_id)

            mock_scheduler.remove_job.assert_called_once()
            assert result["removed"] is True
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_collect_job_not_exists(self, service, mock_db):
        """Test removing a non-existent job."""
        task_id = uuid.uuid4()

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = None

            result = await service.remove_collect_job(task_id)

            mock_scheduler.remove_job.assert_not_called()
            assert result["removed"] is False

    @pytest.mark.asyncio
    async def test_pause_collect_job(self, service, mock_db):
        """Test pausing a scheduled job."""
        task_id = uuid.uuid4()

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = MagicMock()

            result = await service.pause_collect_job(task_id)

            mock_scheduler.pause_job.assert_called_once()
            assert result["paused"] is True
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_collect_job(self, service, mock_db):
        """Test resuming a paused job."""
        task_id = uuid.uuid4()
        next_run = datetime.now(timezone.utc)

        mock_job = MagicMock()
        mock_job.next_run_time = next_run

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = mock_job

            result = await service.resume_collect_job(task_id)

            mock_scheduler.resume_job.assert_called_once()
            assert result["resumed"] is True
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status_task_not_found(self, service, mock_db):
        """Test getting status for non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Collection task not found"):
            await service.get_job_status(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_job_status_scheduled(self, service, mock_db, sample_task):
        """Test getting status for a scheduled task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        mock_job = MagicMock()
        mock_job.next_run_time = datetime.now(timezone.utc)

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = mock_job

            result = await service.get_job_status(sample_task.id)

            assert result["is_scheduled"] is True
            assert result["task_name"] == sample_task.name
            assert result["next_run_time"] is not None

    @pytest.mark.asyncio
    async def test_get_job_status_not_scheduled(self, service, mock_db, sample_task):
        """Test getting status for an unscheduled task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = None

            result = await service.get_job_status(sample_task.id)

            assert result["is_scheduled"] is False
            assert result["next_run_time"] is None

    @pytest.mark.asyncio
    async def test_list_jobs(self, service, mock_db, sample_task):
        """Test listing all scheduled jobs."""
        job_id = f"collect_task_{sample_task.id}"

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.next_run_time = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task
        mock_db.execute.return_value = mock_result

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            mock_scheduler.get_jobs.return_value = [mock_job]

            result = await service.list_jobs()

            assert result["total"] == 1
            assert len(result["jobs"]) == 1
            assert result["jobs"][0]["task_name"] == sample_task.name

    @pytest.mark.asyncio
    async def test_sync_jobs_from_database(self, service, mock_db, sample_task):
        """Test syncing jobs from database on startup."""
        mock_result = MagicMock()
        mock_result.scalars.return_value = [sample_task]
        mock_db.execute.return_value = mock_result

        with patch("app.services.scheduler_service.scheduler") as mock_scheduler:
            result = await service.sync_jobs_from_database()

            assert result["total_tasks"] == 1
            assert result["synced"] == 1
            assert result["failed"] == 0
            mock_scheduler.add_job.assert_called_once()


class TestGetNextRunTimes:
    """Test suite for get_next_run_times function."""

    def test_valid_cron_expression(self):
        """Test with valid cron expression."""
        times = get_next_run_times("0 0 * * *", count=3)
        assert len(times) == 3
        for time in times:
            assert "T" in time

    def test_invalid_cron_expression(self):
        """Test with invalid cron expression."""
        times = get_next_run_times("invalid cron", count=3)
        assert times == []

    def test_count_parameter(self):
        """Test different count values."""
        times_1 = get_next_run_times("0 * * * *", count=1)
        times_5 = get_next_run_times("0 * * * *", count=5)

        assert len(times_1) == 1
        assert len(times_5) == 5

    def test_every_minute(self):
        """Test cron expression for every minute."""
        times = get_next_run_times("* * * * *", count=5)
        assert len(times) == 5

    def test_specific_time(self):
        """Test cron expression for specific time."""
        times = get_next_run_times("30 9 * * *", count=2)
        assert len(times) == 2


class TestSchedulerAPI:
    """Test suite for scheduler API endpoints."""

    @pytest.mark.asyncio
    async def test_add_schedule_endpoint(self):
        """Test the add schedule API endpoint format."""
        from pydantic import BaseModel

        class ScheduleRequest(BaseModel):
            cron_expression: str

        request = ScheduleRequest(cron_expression="0 0 * * *")
        assert request.cron_expression == "0 0 * * *"

    def test_cron_presets(self):
        """Test common cron preset expressions."""
        presets = {
            "every_minute": "* * * * *",
            "every_hour": "0 * * * *",
            "daily_midnight": "0 0 * * *",
            "weekly_monday": "0 0 * * 1",
            "monthly_first": "0 0 1 * *",
        }

        for name, cron in presets.items():
            times = get_next_run_times(cron, count=1)
            assert len(times) > 0, f"Preset '{name}' failed to parse"
