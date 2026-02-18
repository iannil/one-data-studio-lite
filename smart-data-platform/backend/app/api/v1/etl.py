from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models import (
    ETLPipeline,
    ETLStep,
    ETLExecution,
    PipelineStatus,
    ExecutionStatus,
)
from app.schemas import (
    ETLPipelineCreate,
    ETLPipelineResponse,
    ETLPipelineUpdate,
    ETLStepCreate,
    ETLStepResponse,
    ETLStepUpdate,
    ETLExecutionResponse,
    ETLRunRequest,
    ETLPreviewResponse,
    AISuggestRulesRequest,
    AISuggestRulesResponse,
    AIPredictFillRequest,
    AIPredictFillResponse,
)
from app.services import ETLEngine, AIService

router = APIRouter(prefix="/etl", tags=["ETL"])


def _build_pipeline_response(pipeline: ETLPipeline) -> dict:
    """Build pipeline response with last execution info."""
    response = {
        "id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description,
        "status": pipeline.status,
        "source_type": pipeline.source_type,
        "source_config": pipeline.source_config,
        "target_type": pipeline.target_type,
        "target_config": pipeline.target_config,
        "schedule_cron": pipeline.schedule_cron,
        "is_scheduled": pipeline.is_scheduled,
        "tags": pipeline.tags,
        "version": pipeline.version,
        "created_at": pipeline.created_at,
        "created_by": pipeline.created_by,
        "steps": pipeline.steps,
        "last_execution_status": None,
        "last_run_at": None,
    }

    # Get last execution if available
    if pipeline.executions:
        # Sort by started_at descending and get the first one
        sorted_executions = sorted(
            pipeline.executions,
            key=lambda e: e.started_at,
            reverse=True
        )
        last_exec = sorted_executions[0]
        response["last_execution_status"] = last_exec.status
        response["last_run_at"] = last_exec.started_at

    return response


@router.post("/pipelines", response_model=ETLPipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    request: ETLPipelineCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLPipeline:
    """Create a new ETL pipeline."""
    pipeline = ETLPipeline(
        name=request.name,
        description=request.description,
        source_type=request.source_type,
        source_config=request.source_config,
        target_type=request.target_type,
        target_config=request.target_config,
        schedule_cron=request.schedule_cron,
        is_scheduled=request.is_scheduled,
        tags=request.tags,
        created_by=current_user.id,
    )
    db.add(pipeline)
    await db.flush()

    for idx, step_data in enumerate(request.steps):
        step = ETLStep(
            pipeline_id=pipeline.id,
            name=step_data.name,
            step_type=step_data.step_type,
            config=step_data.config,
            order=step_data.order if step_data.order else idx,
            is_enabled=step_data.is_enabled,
            description=step_data.description,
        )
        db.add(step)

    await db.commit()

    result = await db.execute(
        select(ETLPipeline)
        .options(selectinload(ETLPipeline.steps))
        .where(ETLPipeline.id == pipeline.id)
    )
    return result.scalar_one()


@router.get("/pipelines", response_model=list[ETLPipelineResponse])
async def list_pipelines(
    db: DBSession,
    current_user: CurrentUser,
    status: PipelineStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List ETL pipelines."""
    query = select(ETLPipeline).options(
        selectinload(ETLPipeline.steps),
        selectinload(ETLPipeline.executions)
    )

    if status:
        query = query.where(ETLPipeline.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    pipelines = list(result.scalars())
    return [_build_pipeline_response(p) for p in pipelines]


@router.get("/pipelines/{pipeline_id}", response_model=ETLPipelineResponse)
async def get_pipeline(
    pipeline_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLPipeline:
    """Get a specific ETL pipeline."""
    result = await db.execute(
        select(ETLPipeline)
        .options(selectinload(ETLPipeline.steps))
        .where(ETLPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return pipeline


@router.patch("/pipelines/{pipeline_id}", response_model=ETLPipelineResponse)
async def update_pipeline(
    pipeline_id: UUID,
    request: ETLPipelineUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLPipeline:
    """Update an ETL pipeline."""
    result = await db.execute(
        select(ETLPipeline)
        .options(selectinload(ETLPipeline.steps))
        .where(ETLPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pipeline, field, value)

    await db.commit()
    await db.refresh(pipeline)

    return pipeline


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_pipeline(
    pipeline_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete an ETL pipeline."""
    result = await db.execute(select(ETLPipeline).where(ETLPipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    await db.delete(pipeline)
    await db.commit()


@router.post("/pipelines/{pipeline_id}/steps", response_model=ETLStepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    pipeline_id: UUID,
    request: ETLStepCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLStep:
    """Add a step to a pipeline."""
    result = await db.execute(select(ETLPipeline).where(ETLPipeline.id == pipeline_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pipeline not found")

    step = ETLStep(
        pipeline_id=pipeline_id,
        name=request.name,
        step_type=request.step_type,
        config=request.config,
        order=request.order,
        is_enabled=request.is_enabled,
        description=request.description,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)

    return step


@router.patch("/pipelines/{pipeline_id}/steps/{step_id}", response_model=ETLStepResponse)
async def update_step(
    pipeline_id: UUID,
    step_id: UUID,
    request: ETLStepUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLStep:
    """Update a pipeline step."""
    result = await db.execute(
        select(ETLStep).where(ETLStep.id == step_id, ETLStep.pipeline_id == pipeline_id)
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)

    await db.commit()
    await db.refresh(step)

    return step


@router.delete("/pipelines/{pipeline_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_step(
    pipeline_id: UUID,
    step_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a pipeline step."""
    result = await db.execute(
        select(ETLStep).where(ETLStep.id == step_id, ETLStep.pipeline_id == pipeline_id)
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    await db.delete(step)
    await db.commit()


@router.post("/pipelines/{pipeline_id}/run", response_model=ETLExecutionResponse)
async def run_pipeline(
    pipeline_id: UUID,
    request: ETLRunRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ETLExecution:
    """Execute an ETL pipeline."""
    result = await db.execute(
        select(ETLPipeline)
        .options(selectinload(ETLPipeline.steps))
        .where(ETLPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    execution = ETLExecution(
        pipeline_id=pipeline.id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        triggered_by=current_user.id,
    )
    db.add(execution)
    await db.flush()

    engine = ETLEngine(db)
    exec_result = await engine.execute_pipeline(
        pipeline,
        preview_mode=request.preview_mode,
        preview_rows=request.preview_rows,
    )

    execution.status = (
        ExecutionStatus.SUCCESS
        if exec_result["status"] == "success"
        else ExecutionStatus.FAILED
    )
    execution.completed_at = datetime.now(timezone.utc)
    execution.rows_input = exec_result.get("rows_input", 0)
    execution.rows_output = exec_result.get("rows_output", 0)
    execution.error_message = exec_result.get("error_message")
    execution.step_metrics = exec_result.get("step_metrics")

    await db.commit()
    await db.refresh(execution)

    return execution


@router.post("/pipelines/{pipeline_id}/preview", response_model=ETLPreviewResponse)
async def preview_pipeline(
    pipeline_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    rows: int = 100,
) -> ETLPreviewResponse:
    """Preview pipeline execution results."""
    result = await db.execute(
        select(ETLPipeline)
        .options(selectinload(ETLPipeline.steps))
        .where(ETLPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    engine = ETLEngine(db)
    exec_result = await engine.execute_pipeline(
        pipeline,
        preview_mode=True,
        preview_rows=rows,
    )

    if exec_result["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail=exec_result.get("error_message", "Preview failed"),
        )

    preview_data = exec_result.get("preview_data", [])
    columns = list(preview_data[0].keys()) if preview_data else []

    return ETLPreviewResponse(
        columns=columns,
        data=preview_data,
        row_count=len(preview_data),
    )


@router.get("/pipelines/{pipeline_id}/executions", response_model=list[ETLExecutionResponse])
async def list_executions(
    pipeline_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
) -> list[ETLExecution]:
    """List execution history for a pipeline."""
    result = await db.execute(
        select(ETLExecution)
        .where(ETLExecution.pipeline_id == pipeline_id)
        .order_by(ETLExecution.started_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(result.scalars())


# AI-powered ETL endpoints
ai_router = APIRouter(prefix="/etl/ai", tags=["ETL AI"])


@ai_router.post("/suggest-rules", response_model=AISuggestRulesResponse)
async def suggest_cleaning_rules(
    request: AISuggestRulesRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AISuggestRulesResponse:
    """Get AI-suggested data cleaning rules."""
    ai_service = AIService(db)
    result = await ai_service.suggest_cleaning_rules(
        request.source_id,
        request.table_name,
        request.sample_size,
    )

    return AISuggestRulesResponse(**result)


@ai_router.post("/predict-fill", response_model=AIPredictFillResponse)
async def predict_fill_missing(
    request: AIPredictFillRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AIPredictFillResponse:
    """Use AI to predict and fill missing values."""
    ai_service = AIService(db)
    result = await ai_service.predict_missing_values(
        request.source_id,
        request.table_name,
        request.target_column,
        request.feature_columns,
    )

    return AIPredictFillResponse(**result)
