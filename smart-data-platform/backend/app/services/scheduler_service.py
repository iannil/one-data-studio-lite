"""Scheduler service for managing collection task scheduling.

This service supports both APScheduler (legacy) and Celery (new) for
gradual migration. Set USE_CELERY environment variable to "true" to use Celery.

Migration Complete:
- APScheduler fully removed when USE_CELERY=true
- All scheduling handled by Celery Beat
- Task execution handled by Celery Workers
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from celery.schedules import crontab as celery_crontab
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import CollectTask, CollectTaskStatus


def _parse_cron_to_celery(cron_expression: str) -> celery_crontab:
    """Parse a 5-part cron expression to Celery crontab schedule.

    Args:
        cron_expression: Standard cron expression (e.g., "* * * * *")

    Returns:
        Celery crontab schedule instance
    """
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Cron expression must have 5 parts, got {len(parts)}: {cron_expression}"
        )

    minute, hour, day_of_month, month, day_of_week = parts

    return celery_crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month,
        day_of_week=day_of_week,
    )

# Use Celery if environment variable is set
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"

if USE_CELERY:
    from app.celery_worker import celery_app
else:
    from app.core.scheduler import scheduler


# Redis key for storing dynamic beat schedule
_BEAT_SCHEDULE_KEY = "celery:beat_schedule"


class SchedulerService:
    """Service for managing scheduled jobs.

    When USE_CELERY=true: Uses Celery Beat for scheduling
    When USE_CELERY=false: Uses APScheduler (legacy)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_job_id(self, task_id: uuid.UUID) -> str:
        """Generate a consistent job ID from task ID."""
        return f"collect_task_{task_id}"

    def _get_redis_key(self) -> str:
        """Get Redis key for storing beat schedule."""
        return _BEAT_SCHEDULE_KEY

    async def _load_beat_schedule_from_redis(self) -> dict[str, Any]:
        """Load beat schedule from Redis for persistence."""
        if not USE_CELERY:
            return {}

        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL + '/1')
            data = redis_client.get(self._get_redis_key())
            if data:
                return json.loads(data)
        except Exception:
            pass
        return {}

    async def _save_beat_schedule_to_redis(self, schedule: dict[str, Any]) -> None:
        """Save beat schedule to Redis for persistence."""
        if not USE_CELERY:
            return

        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL + '/1')
            redis_client.set(self._get_redis_key(), json.dumps(schedule), ex=86400 * 7)
        except Exception:
            pass

    async def _refresh_beat_schedule(self) -> None:
        """Refresh Celery Beat schedule by updating configuration."""
        if not USE_CELERY:
            return

        # Celery Beat will pick up changes from Redis on next cycle
        # For immediate effect, we update the in-memory config
        schedule = await self._load_beat_schedule_from_redis()
        if schedule:
            celery_app.conf.beat_schedule.update(schedule)

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

        # Validate cron expression
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression: {cron_expression}. Error: {e}")

        job_id = self._get_job_id(task_id)

        if USE_CELERY:
            # Use Celery Beat for scheduling
            schedule_entry = {
                "task": "collect.execute_task",
                "schedule": _parse_cron_to_celery(cron_expression),
                "args": [str(task_id)],
            }

            # Update in-memory schedule
            celery_app.conf.beat_schedule[job_id] = schedule_entry

            # Persist to Redis for Beat to pick up
            current_schedule = await self._load_beat_schedule_from_redis()
            current_schedule[job_id] = schedule_entry
            await self._save_beat_schedule_to_redis(current_schedule)

            task.schedule_cron = cron_expression
            task.is_active = True
            task.status = CollectTaskStatus.PENDING
            await self.db.commit()

            # Calculate next run time for response
            next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))

            return {
                "job_id": job_id,
                "task_id": str(task_id),
                "task_name": task.name,
                "cron_expression": cron_expression,
                "next_run_time": next_run.isoformat() if next_run else None,
                "is_active": True,
                "scheduler": "celery",
            }
        else:
            # Use APScheduler (legacy)
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)

            job = scheduler.add_job(
                func="app.tasks.collect_tasks.execute_collect_task",
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
                "scheduler": "apscheduler",
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
        removed = False

        if USE_CELERY:
            # Remove from in-memory schedule
            if job_id in celery_app.conf.beat_schedule:
                del celery_app.conf.beat_schedule[job_id]
                removed = True

            # Remove from Redis persistence
            current_schedule = await self._load_beat_schedule_from_redis()
            if job_id in current_schedule:
                del current_schedule[job_id]
                await self._save_beat_schedule_to_redis(current_schedule)
        else:
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                removed = True

        await self.db.execute(
            update(CollectTask)
            .where(CollectTask.id == task_id)
            .values(is_active=False, schedule_cron=None)
        )
        await self.db.commit()

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "removed": removed,
            "message": "Schedule removed successfully" if removed else "No schedule found",
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

        if USE_CELERY:
            # In Celery, we remove from schedule but keep task data
            # Job can be resumed by re-adding to schedule
            if job_id in celery_app.conf.beat_schedule:
                del celery_app.conf.beat_schedule[job_id]

            current_schedule = await self._load_beat_schedule_from_redis()
            if job_id in current_schedule:
                del current_schedule[job_id]
                await self._save_beat_schedule_to_redis(current_schedule)
        else:
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
        result = await self.db.execute(
            select(CollectTask).where(CollectTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Collection task not found: {task_id}")

        job_id = self._get_job_id(task_id)
        next_run = None

        if USE_CELERY and task.schedule_cron:
            # Re-add to Celery Beat schedule
            schedule_entry = {
                "task": "collect.execute_task",
                "schedule": _parse_cron_to_celery(task.schedule_cron),
                "args": [str(task_id)],
            }
            celery_app.conf.beat_schedule[job_id] = schedule_entry

            current_schedule = await self._load_beat_schedule_from_redis()
            current_schedule[job_id] = schedule_entry
            await self._save_beat_schedule_to_redis(current_schedule)

            # Calculate next run time
            try:
                trigger = CronTrigger.from_crontab(task.schedule_cron)
                next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            except Exception:
                pass
        else:
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.resume_job(job_id)
                next_run = existing_job.next_run_time

        await self.db.execute(
            update(CollectTask)
            .where(CollectTask.id == task_id)
            .values(status=CollectTaskStatus.PENDING)
        )
        await self.db.commit()

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "resumed": True,
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
        is_scheduled = False
        next_run_time = None

        if USE_CELERY:
            # Check if job is in Celery Beat schedule
            is_scheduled = job_id in celery_app.conf.beat_schedule
            if is_scheduled and task.schedule_cron:
                try:
                    trigger = CronTrigger.from_crontab(task.schedule_cron)
                    next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
                    next_run_time = next_run.isoformat() if next_run else None
                except Exception:
                    pass
        else:
            job = scheduler.get_job(job_id)
            is_scheduled = job is not None
            next_run_time = job.next_run_time.isoformat() if job and job.next_run_time else None

        return {
            "job_id": job_id,
            "task_id": str(task_id),
            "task_name": task.name,
            "cron_expression": task.schedule_cron,
            "is_scheduled": is_scheduled,
            "is_active": task.is_active,
            "status": task.status.value,
            "next_run_time": next_run_time,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "last_success_at": task.last_success_at.isoformat() if task.last_success_at else None,
            "last_error": task.last_error,
            "scheduler": "celery" if USE_CELERY else "apscheduler",
        }

    async def list_jobs(self) -> dict[str, Any]:
        """List all scheduled jobs.

        Returns:
            List of all scheduled jobs with their status
        """
        job_list = []

        if USE_CELERY:
            # List jobs from Celery Beat schedule
            schedule = celery_app.conf.beat_schedule

            for job_id, task_def in schedule.items():
                if job_id.startswith("collect_task_"):
                    task_id_str = job_id.replace("collect_task_", "")
                    try:
                        task_uuid = uuid.UUID(task_id_str)
                        result = await self.db.execute(
                            select(CollectTask).where(CollectTask.id == task_uuid)
                        )
                        task = result.scalar_one_or_none()

                        # Get next run time
                        next_run = None
                        if task and task.schedule_cron:
                            try:
                                trigger = CronTrigger.from_crontab(task.schedule_cron)
                                next_time = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
                                next_run = next_time.isoformat() if next_time else None
                            except Exception:
                                pass

                        job_list.append({
                            "job_id": job_id,
                            "task_id": task_id_str,
                            "task_name": task.name if task else "Unknown",
                            "next_run_time": next_run,
                            "cron_expression": task.schedule_cron if task else None,
                            "is_paused": task.status == CollectTaskStatus.PAUSED if task else False,
                        })
                    except (ValueError, TypeError):
                        continue
        else:
            # List jobs from APScheduler
            jobs = scheduler.get_jobs()

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
            "scheduler": "celery" if USE_CELERY else "apscheduler",
        }

    async def sync_jobs_from_database(self) -> dict[str, Any]:
        """Sync scheduled jobs from database on startup.

        Recreates scheduled jobs for all active tasks with cron expressions.

        Returns:
            Summary of synced jobs
        """
        result = await self.db.execute(
            select(CollectTask).where(
                CollectTask.is_active.is_(True),
                CollectTask.schedule_cron.isnot(None),
                CollectTask.status != CollectTaskStatus.PAUSED,
            )
        )
        tasks = list(result.scalars())

        synced = 0
        failed = 0
        errors = []

        for task in tasks:
            try:
                job_id = self._get_job_id(task.id)

                if USE_CELERY:
                    # Add to Celery Beat schedule
                    schedule_entry = {
                        "task": "collect.execute_task",
                        "schedule": _parse_cron_to_celery(task.schedule_cron),
                        "args": [str(task.id)],
                    }
                    celery_app.conf.beat_schedule[job_id] = schedule_entry
                    synced += 1
                else:
                    # Add to APScheduler
                    trigger = CronTrigger.from_crontab(task.schedule_cron)
                    scheduler.add_job(
                        func="app.tasks.collect_tasks.execute_collect_task",
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

        # Persist to Redis for Celery
        if USE_CELERY and synced > 0:
            await self._save_beat_schedule_to_redis(celery_app.conf.beat_schedule)

        return {
            "total_tasks": len(tasks),
            "synced": synced,
            "failed": failed,
            "errors": errors,
            "scheduler": "celery" if USE_CELERY else "apscheduler",
        }


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


# ============================================================================
# Celery Migration Complete
# ============================================================================
#
# When USE_CELERY=true:
# - Scheduling: Handled by Celery Beat (reads from Redis)
# - Execution: Handled by Celery Workers (app.tasks.collect_tasks)
# - Persistence: Beat schedule stored in Redis
#
# When USE_CELERY=false (legacy):
# - Scheduling & Execution: Handled by APScheduler
#
# To enable Celery mode:
# 1. Set USE_CELERY=true in environment
# 2. Start Celery Beat: celery -A app.celery_worker beat --loglevel=info
# 3. Start Celery Worker: celery -A app.celery_worker worker --loglevel=info
#
# See /docs/reports/completed/2026-02-19-scheduler-migration-plan.md for details.
# ============================================================================
