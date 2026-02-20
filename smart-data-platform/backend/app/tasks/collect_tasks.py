"""Celery tasks for data collection operations.

This module contains Celery tasks that replace APScheduled jobs for
data collection task execution.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.celery_worker import celery_app
from app.core.database import AsyncSessionLocal
from app.models import DataSource, CollectTask, CollectExecution, CollectTaskStatus
from app.connectors import get_connector
from sqlalchemy import select, update
from sqlalchemy import create_engine


@celery_app.task(name="collect.execute_task", bind=True)
def execute_collect_task(self, task_id: str) -> dict[str, Any]:
    """Execute a data collection task.

    This task is called by Celery Beat based on the schedule configuration.

    Args:
        task_id: The collection task ID to execute.

    Returns:
        Execution summary with status and metrics.
    """
    import asyncio

    async def _execute() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            try:
                # Get task
                result = await db.execute(
                    select(CollectTask).where(CollectTask.id == uuid.UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if not task:
                    return {"status": "error", "message": f"Task not found: {task_id}"}

                if not task.is_active:
                    return {"status": "skipped", "message": "Task is not active"}

                # Get source
                source_result = await db.execute(
                    select(DataSource).where(DataSource.id == task.source_id)
                )
                source = source_result.scalar_one_or_none()

                if not source:
                    return {"status": "error", "message": f"Source not found: {task.source_id}"}

                # Create execution record
                execution = CollectExecution(
                    task_id=task.id,
                    status=CollectTaskStatus.RUNNING,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(execution)

                task.status = CollectTaskStatus.RUNNING
                task.last_run_at = datetime.now(timezone.utc)
                await db.commit()

                rows_processed = 0
                rows_inserted = 0
                error_message = None

                try:
                    # Execute collection
                    connector = get_connector(source.type, source.connection_config)

                    if task.source_query:
                        df = await connector.read_data(query=task.source_query)
                    else:
                        df = await connector.read_data(table_name=task.source_table)

                    # Apply incremental filtering if configured
                    if task.is_incremental and task.incremental_field and task.last_sync_value:
                        last_value = task.last_sync_value
                        col_dtype = df[task.incremental_field].dtype
                        if col_dtype in ('int64', 'int32', 'int'):
                            last_value = int(last_value)
                        elif col_dtype in ('float64', 'float32', 'float'):
                            last_value = float(last_value)
                        df = df[df[task.incremental_field] > last_value]

                    rows_processed = len(df)

                    # Write to target table
                    if rows_processed > 0:
                        from app.core.config import settings
                        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
                        sync_engine = create_engine(sync_url)

                        df.to_sql(
                            task.target_table,
                            sync_engine,
                            if_exists="append",
                            index=False,
                        )
                        rows_inserted = rows_processed

                        # Update incremental sync value
                        if task.is_incremental and task.incremental_field:
                            task.last_sync_value = str(df[task.incremental_field].max())

                    # Update execution as success
                    execution.status = CollectTaskStatus.SUCCESS
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.rows_processed = rows_processed
                    execution.rows_inserted = rows_inserted

                    task.status = CollectTaskStatus.SUCCESS
                    task.last_success_at = datetime.now(timezone.utc)
                    task.last_error = None

                except Exception as e:
                    error_message = str(e)
                    execution.status = CollectTaskStatus.FAILED
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.error_message = error_message

                    task.status = CollectTaskStatus.FAILED
                    task.last_error = error_message

                await db.commit()

                return {
                    "status": "success",
                    "task_id": task_id,
                    "task_name": task.name,
                    "rows_processed": rows_processed,
                    "rows_inserted": rows_inserted,
                    "error": error_message,
                }

            except Exception as e:
                return {
                    "status": "error",
                    "task_id": task_id,
                    "error": str(e),
                }

    return asyncio.run(_execute())


@celery_app.task(name="collect.sync_all_active")
def sync_all_active_tasks() -> dict[str, Any]:
    """Execute all active collection tasks.

    This is a manual trigger task that runs all active collection tasks.
    Useful for manual sync operations.

    Returns:
        Summary of all task executions.
    """
    import asyncio

    async def _sync_all() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            # Get all active tasks with schedules
            result = await db.execute(
                select(CollectTask).where(
                    CollectTask.is_active.is_(True),
                    CollectTask.schedule_cron.isnot(None),
                )
            )
            tasks = list(result.scalars())

            results = []
            for task in tasks:
                # Execute each task asynchronously
                task_result = execute_collect_task.delay(str(task.id))
                results.append({
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "celery_task_id": task_result.id,
                })

            return {
                "total_tasks": len(tasks),
                "triggered": results,
            }

    return asyncio.run(_sync_all())


@celery_app.task(name="collect.health_check")
def health_check_sources() -> dict[str, Any]:
    """Health check for all data sources.

    Tests connection to each configured data source.

    Returns:
        Health check results for each source.
    """
    import asyncio

    async def _check() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DataSource))
            sources = list(result.scalars())

            health_results = []
            for source in sources:
                try:
                    connector = get_connector(source.type, source.connection_config)
                    await connector.test_connection()
                    health_results.append({
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "status": "healthy",
                    })
                except Exception as e:
                    health_results.append({
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "status": "unhealthy",
                        "error": str(e),
                    })

            return {
                "total_sources": len(sources),
                "healthy": sum(1 for r in health_results if r["status"] == "healthy"),
                "unhealthy": sum(1 for r in health_results if r["status"] == "unhealthy"),
                "details": health_results,
            }

    return asyncio.run(_check())
