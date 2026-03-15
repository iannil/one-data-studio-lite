"""
Data Collection API Endpoints

Provides REST API for data collection and回流:
- Collection task management
- Execution monitoring
- Connector management
- Quality validation
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.data_collection import (
    CollectionTask,
    CollectionExecution,
    DataSourceConnector,
    QualityValidationResult,
    DataStream,
    WebhookConfig,
    CollectionType,
    SourceType,
    CollectionStatus,
)
from app.services.data_collection.orchestrator import (
    DataCollectionOrchestrator,
    get_collection_orchestrator,
    CollectionResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-collection", tags=["Data Collection"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateCollectionTaskRequest(BaseModel):
    """Request to create a collection task"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    collection_type: str = CollectionType.BATCH
    source_type: str
    source_config: Dict[str, Any]
    destination_type: str = "s3"
    destination_config: Dict[str, Any] = {}
    schedule_cron: Optional[str] = None
    schedule_interval: Optional[int] = None
    batch_size: int = Field(1000, ge=1, le=100000)
    quality_rules: Optional[Dict[str, Any]] = None
    quality_threshold: float = Field(0.8, ge=0, le=1)
    stop_on_error: bool = False
    max_retries: int = Field(3, ge=0, le=10)
    tags: Optional[List[str]] = None


class UpdateCollectionTaskRequest(BaseModel):
    """Request to update a collection task"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_cron: Optional[str] = None
    batch_size: Optional[int] = None
    quality_threshold: Optional[float] = None
    tags: Optional[List[str]] = None


class TriggerCollectionRequest(BaseModel):
    """Request to trigger a collection"""
    parameters: Optional[Dict[str, Any]] = None


class CreateConnectorRequest(BaseModel):
    """Request to create a data source connector"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    source_type: str
    connection_config: Dict[str, Any]
    schema_mapping: Optional[Dict[str, Any]] = None
    test_query: Optional[str] = None


class TestConnectorRequest(BaseModel):
    """Request to test a connector"""
    source_type: str
    config: Dict[str, Any]


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    webhook_path: str
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = None
    target_task_id: Optional[str] = None
    target_stream_id: Optional[str] = None


# ============================================================================
# Collection Task Endpoints
# ============================================================================


@router.post("/tasks", response_model=Dict[str, Any])
async def create_collection_task(
    request: CreateCollectionTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new collection task"""
    try:
        import uuid
        task_id = str(uuid.uuid4())

        task = CollectionTask(
            task_id=task_id,
            name=request.name,
            description=request.description,
            collection_type=request.collection_type,
            source_type=request.source_type,
            source_config=request.source_config,
            destination_type=request.destination_type,
            destination_config=request.destination_config,
            schedule_cron=request.schedule_cron,
            schedule_interval=request.schedule_interval,
            batch_size=request.batch_size,
            quality_rules=request.quality_rules,
            quality_threshold=request.quality_threshold,
            stop_on_error=request.stop_on_error,
            max_retries=request.max_retries,
            tags=request.tags,
            owner_id=str(current_user.id),
            tenant_id=current_user.tenant_id,
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        return {
            "task_id": task.task_id,
            "name": task.name,
            "collection_type": task.collection_type,
            "source_type": task.source_type,
            "enabled": task.enabled,
            "created_at": task.created_at.isoformat(),
            "message": "Collection task created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create collection task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tasks", response_model=List[Dict[str, Any]])
async def list_collection_tasks(
    source_type: Optional[str] = None,
    collection_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List collection tasks"""
    try:
        query = select(CollectionTask).where(
            or_(
                CollectionTask.owner_id == str(current_user.id),
                CollectionTask.tenant_id == current_user.tenant_id,
            )
        )

        if source_type:
            query = query.where(CollectionTask.source_type == source_type)
        if collection_type:
            query = query.where(CollectionTask.collection_type == collection_type)
        if enabled is not None:
            query = query.where(CollectionTask.enabled == enabled)

        query = query.order_by(CollectionTask.updated_at.desc()).limit(limit)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return [
            {
                "task_id": t.task_id,
                "name": t.name,
                "description": t.description,
                "collection_type": t.collection_type,
                "source_type": t.source_type,
                "destination_type": t.destination_type,
                "enabled": t.enabled,
                "schedule_cron": t.schedule_cron,
                "total_runs": t.total_runs,
                "successful_runs": t.successful_runs,
                "failed_runs": t.failed_runs,
                "total_records_collected": t.total_records_collected,
                "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                "tags": t.tags,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]

    except Exception as e:
        logger.error(f"Failed to list collection tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_collection_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get collection task details"""
    try:
        result = await db.execute(
            select(CollectionTask).where(CollectionTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection task {task_id} not found",
            )

        return {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "collection_type": task.collection_type,
            "source_type": task.source_type,
            "source_config": task.source_config,
            "destination_type": task.destination_type,
            "destination_config": task.destination_config,
            "schedule_cron": task.schedule_cron,
            "schedule_interval": task.schedule_interval,
            "batch_size": task.batch_size,
            "quality_rules": task.quality_rules,
            "quality_threshold": task.quality_threshold,
            "stop_on_error": task.stop_on_error,
            "max_retries": task.max_retries,
            "enabled": task.enabled,
            "tags": task.tags,
            "total_runs": task.total_runs,
            "successful_runs": task.successful_runs,
            "failed_runs": task.failed_runs,
            "total_records_collected": task.total_records_collected,
            "total_bytes_collected": task.total_bytes_collected,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "last_success_at": task.last_success_at.isoformat() if task.last_success_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/tasks/{task_id}", response_model=Dict[str, Any])
async def update_collection_task(
    task_id: str,
    request: UpdateCollectionTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update collection task"""
    try:
        result = await db.execute(
            select(CollectionTask).where(CollectionTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection task {task_id} not found",
            )

        # Check ownership
        if task.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can update the task",
            )

        # Update fields
        if request.name is not None:
            task.name = request.name
        if request.description is not None:
            task.description = request.description
        if request.enabled is not None:
            task.enabled = request.enabled
        if request.schedule_cron is not None:
            task.schedule_cron = request.schedule_cron
        if request.batch_size is not None:
            task.batch_size = request.batch_size
        if request.quality_threshold is not None:
            task.quality_threshold = request.quality_threshold
        if request.tags is not None:
            task.tags = request.tags

        task.updated_at = datetime.utcnow()
        await db.commit()

        return {"message": "Collection task updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update collection task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def delete_collection_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete collection task"""
    try:
        from sqlalchemy import delete

        result = await db.execute(
            select(CollectionTask).where(CollectionTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection task {task_id} not found",
            )

        # Check ownership
        if task.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete the task",
            )

        # Delete related executions
        await db.execute(delete(CollectionExecution).where(CollectionExecution.task_id == task_id))

        # Delete task
        await db.delete(task)
        await db.commit()

        return {"message": "Collection task deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete collection task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Execution Endpoints
# ============================================================================


@router.post("/tasks/{task_id}/trigger", response_model=Dict[str, Any])
async def trigger_collection(
    task_id: str,
    request: TriggerCollectionRequest = TriggerCollectionRequest(),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a collection task"""
    try:
        result = await db.execute(
            select(CollectionTask).where(CollectionTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection task {task_id} not found",
            )

        if not task.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is disabled",
            )

        orchestrator = get_collection_orchestrator()

        # Run in background
        async def run_collection():
            await orchestrator.collect_batch(
                db=db,
                task=task,
                trigger_type="api",
                trigger_source=f"user:{current_user.id}",
            )

        if background_tasks:
            background_tasks.add_task(run_collection)
            return {
                "message": "Collection task triggered",
                "task_id": task_id,
                "async": True,
            }
        else:
            result = await run_collection()
            return {
                "message": "Collection completed",
                "execution_id": result.execution_id,
                "status": result.status,
                "records_collected": result.records_collected,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tasks/{task_id}/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    task_id: str,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List executions for a task"""
    try:
        query = select(CollectionExecution).where(CollectionExecution.task_id == task_id)

        if status:
            query = query.where(CollectionExecution.status == status)

        query = query.order_by(CollectionExecution.created_at.desc()).limit(limit)

        result = await db.execute(query)
        executions = result.scalars().all()

        return [
            {
                "execution_id": e.execution_id,
                "task_id": e.task_id,
                "status": e.status,
                "trigger_type": e.trigger_type,
                "trigger_source": e.trigger_source,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration_seconds": e.duration_seconds,
                "records_collected": e.records_collected,
                "records_failed": e.records_failed,
                "bytes_collected": e.bytes_collected,
                "batches_total": e.batches_total,
                "batches_completed": e.batches_completed,
                "quality_score": e.quality_score,
                "quality_level": e.quality_level,
                "error_message": e.error_message,
                "created_at": e.created_at.isoformat(),
            }
            for e in executions
        ]

    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution details"""
    try:
        result = await db.execute(
            select(CollectionExecution).where(CollectionExecution.execution_id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        return {
            "execution_id": execution.execution_id,
            "task_id": execution.task_id,
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "trigger_source": execution.trigger_source,
            "parameters": execution.parameters,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_seconds": execution.duration_seconds,
            "records_collected": execution.records_collected,
            "records_failed": execution.records_failed,
            "bytes_collected": execution.bytes_collected,
            "batches_total": execution.batches_total,
            "batches_completed": execution.batches_completed,
            "output_files": execution.output_files,
            "output_location": execution.output_location,
            "quality_score": execution.quality_score,
            "quality_level": execution.quality_level,
            "quality_details": execution.quality_details,
            "error_message": execution.error_message,
            "error_stack": execution.error_stack,
            "retry_count": execution.retry_count,
            "peak_memory_mb": execution.peak_memory_mb,
            "cpu_time_seconds": execution.cpu_time_seconds,
            "created_at": execution.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Connector Endpoints
# ============================================================================


@router.post("/connectors", response_model=Dict[str, Any])
async def create_connector(
    request: CreateConnectorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a data source connector"""
    try:
        import uuid
        connector_id = str(uuid.uuid4())

        connector = DataSourceConnector(
            connector_id=connector_id,
            name=request.name,
            description=request.description,
            source_type=request.source_type,
            connection_config=request.connection_config,
            schema_mapping=request.schema_mapping,
            test_query=request.test_query,
            owner_id=str(current_user.id),
            tenant_id=current_user.tenant_id,
        )

        db.add(connector)
        await db.commit()

        return {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "source_type": connector.source_type,
            "created_at": connector.created_at.isoformat(),
            "message": "Connector created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/connectors", response_model=List[Dict[str, Any]])
async def list_connectors(
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List data source connectors"""
    try:
        query = select(DataSourceConnector).where(
            or_(
                DataSourceConnector.owner_id == str(current_user.id),
                DataSourceConnector.tenant_id == current_user.tenant_id,
            )
        )

        if source_type:
            query = query.where(DataSourceConnector.source_type == source_type)

        result = await db.execute(query)
        connectors = result.scalars().all()

        return [
            {
                "connector_id": c.connector_id,
                "name": c.name,
                "description": c.description,
                "source_type": c.source_type,
                "enabled": c.enabled,
                "usage_count": c.usage_count,
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
                "last_test_at": c.last_test_at.isoformat() if c.last_test_at else None,
                "last_test_result": c.last_test_result,
                "created_at": c.created_at.isoformat(),
            }
            for c in connectors
        ]

    except Exception as e:
        logger.error(f"Failed to list connectors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/connectors/test", response_model=Dict[str, Any])
async def test_connector(
    request: TestConnectorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test a connector configuration"""
    try:
        orchestrator = get_collection_orchestrator()
        result = await orchestrator.test_connector(
            source_type=request.source_type,
            config=request.config,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to test connector: {e}")
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================================
# Webhook Endpoints
# ============================================================================


@router.post("/webhooks", response_model=Dict[str, Any])
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a webhook for event-driven collection"""
    try:
        import uuid
        webhook_id = str(uuid.uuid4())

        webhook = WebhookConfig(
            webhook_id=webhook_id,
            name=request.name,
            description=request.description,
            webhook_path=request.webhook_path,
            auth_type=request.auth_type,
            auth_config=request.auth_config,
            target_task_id=request.target_task_id,
            target_stream_id=request.target_stream_id,
            owner_id=str(current_user.id),
        )

        db.add(webhook)
        await db.commit()

        return {
            "webhook_id": webhook.webhook_id,
            "name": webhook.name,
            "webhook_path": webhook.webhook_path,
            "created_at": webhook.created_at.isoformat(),
            "message": "Webhook created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/webhooks", response_model=List[Dict[str, Any]])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List webhooks"""
    try:
        result = await db.execute(
            select(WebhookConfig).where(WebhookConfig.owner_id == str(current_user.id))
        )
        webhooks = result.scalars().all()

        return [
            {
                "webhook_id": w.webhook_id,
                "name": w.name,
                "webhook_path": w.webhook_path,
                "auth_type": w.auth_type,
                "target_task_id": w.target_task_id,
                "target_stream_id": w.target_stream_id,
                "enabled": w.enabled,
                "total_calls": w.total_calls,
                "successful_calls": w.successful_calls,
                "failed_calls": w.failed_calls,
                "last_call_at": w.last_call_at.isoformat() if w.last_call_at else None,
                "created_at": w.created_at.isoformat(),
            }
            for w in webhooks
        ]

    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
