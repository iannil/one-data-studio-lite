"""Scheduler service for managing collection task scheduling."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import scheduler
from app.models import CollectTask, CollectTaskStatus


class SchedulerService:
    """Service for managing scheduled jobs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_job_id(self, task_id: uuid.UUID) -> str:
        """Generate a consistent job ID from task ID."""
        return f"collect_task_{task_id}"

    async def add_collect_job(
        self,
        task_id: uuid.UUID,
        cron_expression: str,
    ) -> dict[str, Any]:
        """Add a scheduled job for a collection task.

        Args:
            task_id: The collection task ID
            cron_expression: Cron expression (e.g., "0 0 * * *" for daily at midnight)

        Returns:
            Job information including next run time
        """
        result = await self.db.execute(
            select(CollectTask).where(CollectTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Collection task not found: {task_id}")

        job_id = self._get_job_id(task_id)

        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)

        try:
            trigger = CronTrigger.from_crontab(cron_expression)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression: {cron_expression}. Error: {e}")

        job = scheduler.add_job(
            func="app.services.scheduler_service:execute_collect_task",
            trigger=trigger,
            id=job_id,
            args=[str(task_id)],
            name=f"Collect: {task.name}",
            replace_existing=True,
            misfire_grace_time=300,
        )

        task.schedule_cron = cron_expression
        task.is_active = True
        await self.db.commit()

        next_run = job.next_run_time
        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "task_name": task.name,
            "cron_expression": cron_expression,
            "next_run_time": next_run.isoformat() if next_run else None,
            "is_active": True,
        }

    async def remove_collect_job(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Remove a scheduled job for a collection task.

        Args:
            task_id: The collection task ID

        Returns:
            Status message
        """
        job_id = self._get_job_id(task_id)

        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)

        await self.db.execute(
            update(CollectTask)
            .where(CollectTask.id == task_id)
            .values(is_active=False)
        )
        await self.db.commit()

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "removed": existing_job is not None,
            "message": "Schedule removed successfully" if existing_job else "No schedule found",
        }

    async def pause_collect_job(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Pause a scheduled job without removing it.

        Args:
            task_id: The collection task ID

        Returns:
            Status message
        """
        job_id = self._get_job_id(task_id)

        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.pause_job(job_id)

        await self.db.execute(
            update(CollectTask)
            .where(CollectTask.id == task_id)
            .values(status=CollectTaskStatus.PAUSED)
        )
        await self.db.commit()

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "paused": True,
        }

    async def resume_collect_job(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Resume a paused scheduled job.

        Args:
            task_id: The collection task ID

        Returns:
            Job information including next run time
        """
        job_id = self._get_job_id(task_id)

        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.resume_job(job_id)

        await self.db.execute(
            update(CollectTask)
            .where(CollectTask.id == task_id)
            .values(status=CollectTaskStatus.PENDING)
        )
        await self.db.commit()

        next_run = existing_job.next_run_time if existing_job else None
        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "resumed": existing_job is not None,
            "next_run_time": next_run.isoformat() if next_run else None,
        }

    async def get_job_status(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get the status of a scheduled job.

        Args:
            task_id: The collection task ID

        Returns:
            Job status information
        """
        result = await self.db.execute(
            select(CollectTask).where(CollectTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Collection task not found: {task_id}")

        job_id = self._get_job_id(task_id)
        job = scheduler.get_job(job_id)

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "task_name": task.name,
            "cron_expression": task.schedule_cron,
            "is_scheduled": job is not None,
            "is_active": task.is_active,
            "status": task.status.value,
            "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "last_success_at": task.last_success_at.isoformat() if task.last_success_at else None,
            "last_error": task.last_error,
        }

    async def list_jobs(self) -> dict[str, Any]:
        """List all scheduled jobs.

        Returns:
            List of all scheduled jobs with their status
        """
        jobs = scheduler.get_jobs()

        job_list = []
        for job in jobs:
            if job.id.startswith("collect_task_"):
                task_id = job.id.replace("collect_task_", "")
                try:
                    task_uuid = uuid.UUID(task_id)
                    result = await self.db.execute(
                        select(CollectTask).where(CollectTask.id == task_uuid)
                    )
                    task = result.scalar_one_or_none()

                    job_list.append({
                        "job_id": job.id,
                        "task_id": task_id,
                        "task_name": task.name if task else "Unknown",
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "cron_expression": task.schedule_cron if task else None,
                        "is_paused": job.next_run_time is None,
                    })
                except (ValueError, TypeError):
                    continue

        return {
            "total": len(job_list),
            "jobs": job_list,
        }

    async def sync_jobs_from_database(self) -> dict[str, Any]:
        """Sync scheduled jobs from database on startup.

        Recreates APScheduler jobs for all active tasks with cron expressions.

        Returns:
            Summary of synced jobs
        """
        result = await self.db.execute(
            select(CollectTask).where(
                CollectTask.is_active.is_(True),
                CollectTask.schedule_cron.isnot(None),
            )
        )
        tasks = list(result.scalars())

        synced = 0
        failed = 0
        errors = []

        for task in tasks:
            try:
                job_id = self._get_job_id(task.id)
                trigger = CronTrigger.from_crontab(task.schedule_cron)

                scheduler.add_job(
                    func="app.services.scheduler_service:execute_collect_task",
                    trigger=trigger,
                    id=job_id,
                    args=[str(task.id)],
                    name=f"Collect: {task.name}",
                    replace_existing=True,
                    misfire_grace_time=300,
                )
                synced += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "error": str(e),
                })

        return {
            "total_tasks": len(tasks),
            "synced": synced,
            "failed": failed,
            "errors": errors,
        }


async def execute_collect_task(task_id: str) -> None:
    """Execute a collection task (called by scheduler).

    This function is called by APScheduler when a job triggers.
    """
    from app.core.database import async_session_factory
    from app.connectors import get_connector
    from app.models import DataSource, CollectExecution

    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(CollectTask).where(CollectTask.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                return

            source_result = await db.execute(
                select(DataSource).where(DataSource.id == task.source_id)
            )
            source = source_result.scalar_one_or_none()

            if not source:
                return

            execution = CollectExecution(
                task_id=task.id,
                status=CollectTaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            db.add(execution)

            task.status = CollectTaskStatus.RUNNING
            task.last_run_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                connector = get_connector(source.type, source.connection_config)

                if task.source_query:
                    df = await connector.read_data(query=task.source_query)
                else:
                    df = await connector.read_data(table_name=task.source_table)

                if task.is_incremental and task.incremental_field and task.last_sync_value:
                    last_value = task.last_sync_value
                    col_dtype = df[task.incremental_field].dtype
                    if col_dtype in ('int64', 'int32', 'int'):
                        last_value = int(last_value)
                    elif col_dtype in ('float64', 'float32', 'float'):
                        last_value = float(last_value)
                    df = df[df[task.incremental_field] > last_value]

                rows_processed = len(df)

                from sqlalchemy import create_engine
                from app.core.config import settings

                sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
                sync_engine = create_engine(sync_url)

                df.to_sql(
                    task.target_table,
                    sync_engine,
                    if_exists="append",
                    index=False,
                )

                if task.is_incremental and task.incremental_field and len(df) > 0:
                    task.last_sync_value = str(df[task.incremental_field].max())

                execution.status = CollectTaskStatus.SUCCESS
                execution.completed_at = datetime.now(timezone.utc)
                execution.rows_processed = rows_processed
                execution.rows_inserted = rows_processed

                task.status = CollectTaskStatus.SUCCESS
                task.last_success_at = datetime.now(timezone.utc)
                task.last_error = None

            except Exception as e:
                execution.status = CollectTaskStatus.FAILED
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = str(e)

                task.status = CollectTaskStatus.FAILED
                task.last_error = str(e)

            await db.commit()

        except Exception:
            pass


def get_next_run_times(
    cron_expression: str,
    count: int = 5,
) -> list[str]:
    """Get the next N run times for a cron expression.

    Args:
        cron_expression: Cron expression to evaluate
        count: Number of run times to return

    Returns:
        List of ISO formatted datetime strings
    """
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
    except ValueError:
        return []

    now = datetime.now(timezone.utc)
    times = []

    for _ in range(count):
        next_time = trigger.get_next_fire_time(None, now)
        if next_time:
            times.append(next_time.isoformat())
            now = next_time
        else:
            break

    return times
