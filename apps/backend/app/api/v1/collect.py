from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models import CollectTask, CollectTaskStatus, CollectExecution, DataSource
from app.schemas import (
    CollectTaskCreate,
    CollectTaskResponse,
    CollectTaskUpdate,
    CollectExecutionResponse,
    CollectRunRequest,
)

router = APIRouter(prefix="/collect", tags=["Data Collection"])


@router.post("/tasks", response_model=CollectTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CollectTaskCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CollectTask:
    """Create a new collection task."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == request.source_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Data source not found")

    task = CollectTask(
        name=request.name,
        description=request.description,
        source_id=request.source_id,
        source_table=request.source_table,
        source_query=request.source_query,
        target_table=request.target_table,
        schedule_cron=request.schedule_cron,
        is_incremental=request.is_incremental,
        incremental_field=request.incremental_field,
        column_mapping=request.column_mapping,
        created_by=current_user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


@router.get("/tasks", response_model=list[CollectTaskResponse])
async def list_tasks(
    db: DBSession,
    current_user: CurrentUser,
    source_id: UUID | None = None,
    status: CollectTaskStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CollectTask]:
    """List collection tasks."""
    query = select(CollectTask)

    if source_id:
        query = query.where(CollectTask.source_id == source_id)
    if status:
        query = query.where(CollectTask.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars())


@router.get("/tasks/{task_id}", response_model=CollectTaskResponse)
async def get_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> CollectTask:
    """Get a specific collection task."""
    result = await db.execute(select(CollectTask).where(CollectTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.patch("/tasks/{task_id}", response_model=CollectTaskResponse)
async def update_task(
    task_id: UUID,
    request: CollectTaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> CollectTask:
    """Update a collection task."""
    result = await db.execute(select(CollectTask).where(CollectTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a collection task."""
    result = await db.execute(select(CollectTask).where(CollectTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()


@router.post("/tasks/{task_id}/run", response_model=CollectExecutionResponse)
async def run_task(
    task_id: UUID,
    request: CollectRunRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> CollectExecution:
    """Execute a collection task."""
    from datetime import datetime, timezone
    from app.connectors import get_connector

    result = await db.execute(select(CollectTask).where(CollectTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    source_result = await db.execute(
        select(DataSource).where(DataSource.id == task.source_id)
    )
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

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

        if task.is_incremental and task.incremental_field and task.last_sync_value and not request.force_full_sync:
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
    await db.refresh(execution)

    return execution


@router.get("/tasks/{task_id}/executions", response_model=list[CollectExecutionResponse])
async def list_executions(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
) -> list[CollectExecution]:
    """List execution history for a task."""
    result = await db.execute(
        select(CollectExecution)
        .where(CollectExecution.task_id == task_id)
        .order_by(CollectExecution.started_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(result.scalars())


@router.post("/tasks/{task_id}/schedule")
async def add_task_schedule(
    task_id: UUID,
    cron_expression: str,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Add or update a schedule for a collection task.

    Args:
        task_id: The task ID
        cron_expression: Cron expression (e.g., "0 0 * * *" for daily at midnight)
    """
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    try:
        return await service.add_collect_job(task_id, cron_expression)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/{task_id}/schedule")
async def remove_task_schedule(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Remove the schedule for a collection task."""
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    return await service.remove_collect_job(task_id)


@router.get("/tasks/{task_id}/schedule")
async def get_task_schedule(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Get the schedule status for a collection task."""
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    try:
        return await service.get_job_status(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tasks/{task_id}/schedule/pause")
async def pause_task_schedule(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Pause the schedule for a collection task."""
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    return await service.pause_collect_job(task_id)


@router.post("/tasks/{task_id}/schedule/resume")
async def resume_task_schedule(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Resume a paused schedule for a collection task."""
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    return await service.resume_collect_job(task_id)


@router.get("/jobs")
async def list_scheduled_jobs(
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """List all scheduled collection jobs."""
    from app.services.scheduler_service import SchedulerService

    service = SchedulerService(db)
    return await service.list_jobs()


@router.get("/schedule/preview")
async def preview_schedule(
    cron_expression: str,
    count: int = 5,
) -> dict:
    """Preview the next run times for a cron expression.

    Args:
        cron_expression: Cron expression to evaluate
        count: Number of run times to return (default 5, max 10)
    """
    from app.services.scheduler_service import get_next_run_times

    count = min(count, 10)
    times = get_next_run_times(cron_expression, count)

    if not times:
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    return {
        "cron_expression": cron_expression,
        "next_run_times": times,
    }
