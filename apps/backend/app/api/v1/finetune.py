"""
Fine-tuning Pipeline API Endpoints

REST API for managing LLM fine-tuning pipelines.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.finetune import (
    FinetunePipelineCreate,
    FinetunePipelineUpdate,
    FinetunePipelineResponse,
    FinetunePipelineListResponse,
    FinetuneActionRequest,
    FinetuneActionResponse,
    FinetuneExecuteRequest,
    FinetuneExecuteResponse,
    FinetuneStageResponse,
    FinetuneCheckpointResponse,
)
from app.services.finetune import FinetuneOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=FinetunePipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_finetune_pipeline(
    data: FinetunePipelineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new fine-tuning pipeline

    Creates a pipeline for fine-tuning a language model.
    """
    orchestrator = FinetuneOrchestrator(db)

    # Build config from data
    config = data.model_dump(exclude={"name", "base_model_id", "base_model_name", "base_model_type"})
    config["description"] = data.description

    # Create pipeline
    pipeline = await orchestrator.create_pipeline(
        name=data.name,
        base_model_id=data.base_model_id,
        base_model_name=data.base_model_name,
        base_model_type=data.base_model_type,
        config=config,
        owner_id=str(current_user.id),
        dataset_id=data.dataset_id,
        tenant_id=data.tenant_id,
        project_id=data.project_id,
    )

    return FinetunePipelineResponse.model_validate(pipeline)


@router.get("/", response_model=FinetunePipelineListResponse)
async def list_finetune_pipelines(
    status: Optional[str] = Query(None, description="Filter by current stage"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List fine-tuning pipelines

    Returns a paginated list of pipelines.
    """
    orchestrator = FinetuneOrchestrator(db)

    owner_id = str(current_user.id) if not current_user.is_superuser else None
    pipelines, total = await orchestrator.list_pipelines(
        owner_id=owner_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return FinetunePipelineListResponse(
        total=total,
        items=[FinetunePipelineResponse.model_validate(p) for p in pipelines],
    )


@router.get("/{pipeline_id}", response_model=FinetunePipelineResponse)
async def get_finetune_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get fine-tuning pipeline details

    Returns detailed information about a pipeline.
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check access
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this pipeline",
        )

    return FinetunePipelineResponse.model_validate(pipeline)


@router.put("/{pipeline_id}", response_model=FinetunePipelineResponse)
async def update_finetune_pipeline(
    pipeline_id: str,
    data: FinetunePipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update fine-tuning pipeline

    Updates pipeline metadata (not configuration).
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this pipeline",
        )

    # Update allowed fields
    if data.description is not None:
        pipeline.description = data.description
    if data.tags is not None:
        pipeline.tags = data.tags
    if data.labels is not None:
        pipeline.labels = data.labels

    from datetime import datetime
    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)

    return FinetunePipelineResponse.model_validate(pipeline)


@router.post("/{pipeline_id}/execute", response_model=FinetuneExecuteResponse)
async def execute_finetune_pipeline(
    pipeline_id: str,
    data: FinetuneExecuteRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a fine-tuning pipeline

    Starts the execution of a pipeline.
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to execute this pipeline",
        )

    # Check if pipeline can be executed
    if pipeline.current_stage not in ["data_prep", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pipeline is in {pipeline.current_stage} state and cannot be executed",
        )

    # Execute pipeline
    execution_id = await orchestrator.execute_pipeline(
        pipeline_id=pipeline_id,
        auto_advance=data.auto_advance,
        start_from=data.stage,
    )

    return FinetuneExecuteResponse(
        execution_id=execution_id,
        pipeline_id=pipeline_id,
        status="running",
        current_stage=pipeline.current_stage,
        message="Pipeline execution started",
    )


@router.post("/{pipeline_id}/action", response_model=FinetuneActionResponse)
async def finetune_pipeline_action(
    pipeline_id: str,
    data: FinetuneActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform action on pipeline

    Actions: start, stop, retry
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to control this pipeline",
        )

    if data.action == "stop":
        success = await orchestrator.stop_pipeline(pipeline_id)
        if success:
            return FinetuneActionResponse(
                pipeline_id=pipeline_id,
                action=data.action,
                status="stopped",
                message="Pipeline stopped",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop pipeline",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {data.action}",
        )


@router.get("/{pipeline_id}/stages", response_model=list[FinetuneStageResponse])
async def get_pipeline_stages(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline stages

    Returns all stages for a pipeline.
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check access
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this pipeline",
        )

    stages = await orchestrator.get_pipeline_stages(pipeline_id)

    return [FinetuneStageResponse.model_validate(s) for s in stages]


@router.get("/{pipeline_id}/checkpoints", response_model=list[FinetuneCheckpointResponse])
async def get_pipeline_checkpoints(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline checkpoints

    Returns all checkpoints for a pipeline.
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check access
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this pipeline",
        )

    checkpoints = await orchestrator.get_pipeline_checkpoints(pipeline_id)

    return [FinetuneCheckpointResponse.model_validate(c) for c in checkpoints]


@router.delete("/{pipeline_id}")
async def delete_finetune_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a fine-tuning pipeline

    Permanently deletes a pipeline and all associated data.
    """
    orchestrator = FinetuneOrchestrator(db)
    pipeline = await orchestrator.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and pipeline.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this pipeline",
        )

    # Only allow deletion of completed/failed pipelines
    if pipeline.current_stage not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete completed or failed pipelines",
        )

    # Delete pipeline
    from sqlalchemy import delete
    from app.models.finetune import FinetunePipeline

    await db.execute(
        delete(FinetunePipeline).where(FinetunePipeline.pipeline_id == pipeline_id)
    )
    await db.commit()

    return {"success": True, "message": "Pipeline deleted"}
