"""Celery tasks for ETL pipeline operations.

This module contains Celery tasks for executing ETL pipelines
as background jobs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.celery_worker import celery_app
from app.core.database import AsyncSessionLocal
from app.services import ETLEngine
from app.models import ETLPipeline, ETLExecution, ExecutionStatus
from sqlalchemy import select


@celery_app.task(name="etl.run_pipeline", bind=True)
def run_etl_pipeline(self, pipeline_id: str, preview_mode: bool = False) -> dict[str, Any]:
    """Execute an ETL pipeline.

    Args:
        pipeline_id: The pipeline ID to execute.
        preview_mode: If True, run in preview mode without persisting results.

    Returns:
        Execution result with status and metrics.
    """
    import asyncio

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            try:
                # Get pipeline
                result = await db.execute(
                    select(ETLPipeline).where(ETLPipeline.id == uuid.UUID(pipeline_id))
                )
                pipeline = result.scalar_one_or_none()

                if not pipeline:
                    return {"status": "error", "message": f"Pipeline not found: {pipeline_id}"}

                # Create execution record
                execution = ETLExecution(
                    pipeline_id=pipeline.id,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                # Run pipeline
                engine = ETLEngine(db)
                exec_result = await engine.run_pipeline(pipeline.id, preview_mode=preview_mode)

                # Update execution
                execution.status = exec_result.get("status", ExecutionStatus.SUCCESS)
                execution.completed_at = datetime.now(timezone.utc)
                execution.rows_output = exec_result.get("rows_processed", 0)
                execution.step_metrics = exec_result.get("step_metrics", [])
                execution.error_message = exec_result.get("error_message")

                await db.commit()
                await db.refresh(execution)

                return {
                    "status": "success",
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline.name,
                    "execution_id": str(execution.id),
                    "rows_processed": execution.rows_output,
                    "preview_mode": preview_mode,
                    "step_metrics": execution.step_metrics,
                }

            except Exception as e:
                # Update execution as failed if we got this far
                try:
                    result = await db.execute(
                        select(ETLExecution)
                        .where(ETLExecution.pipeline_id == uuid.UUID(pipeline_id))
                        .order_by(ETLExecution.started_at.desc())
                        .limit(1)
                    )
                    execution = result.scalar_one_or_none()
                    if execution:
                        execution.status = ExecutionStatus.FAILED
                        execution.completed_at = datetime.now(timezone.utc)
                        execution.error_message = str(e)
                        await db.commit()
                except Exception:
                    pass

                return {
                    "status": "error",
                    "pipeline_id": pipeline_id,
                    "error": str(e),
                }

    return asyncio.run(_run())


@celery_app.task(name="etl.run_scheduled")
def run_scheduled_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Execute a scheduled ETL pipeline.

    This task is intended to be triggered by Celery Beat for
    pipelines with scheduled execution.

    Args:
        pipeline_id: The pipeline ID to execute.

    Returns:
        Execution result.
    """
    return run_etl_pipeline(pipeline_id, preview_mode=False)


@celery_app.task(name="etl.run_all_scheduled")
def run_all_scheduled_pipelines() -> dict[str, Any]:
    """Execute all pipelines with active schedules.

    Returns:
        Summary of triggered pipeline executions.
    """
    import asyncio

    async def _run_all() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            # Get all pipelines with schedules
            result = await db.execute(
                select(ETLPipeline).where(
                    ETLPipeline.is_active.is_(True),
                    ETLPipeline.schedule_cron.isnot(None),
                )
            )
            pipelines = list(result.scalars())

            results = []
            for pipeline in pipelines:
                # Execute each pipeline
                task_result = run_etl_pipeline.delay(str(pipeline.id))
                results.append({
                    "pipeline_id": str(pipeline.id),
                    "pipeline_name": pipeline.name,
                    "celery_task_id": task_result.id,
                })

            return {
                "total_pipelines": len(pipelines),
                "triggered": results,
            }

    return asyncio.run(_run_all())
