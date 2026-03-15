"""
TensorBoard API Endpoints

Provides REST API for managing TensorBoard instances.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.services.tensorboard.manager import TensorBoardManager
from app.core.config import settings

router = APIRouter(prefix="/tensorboard", tags=["TensorBoard"])


# Request/Response Schemas
class TensorBoardCreate(BaseModel):
    """Request to create a TensorBoard instance"""

    name: str = Field(..., description="TensorBoard instance name")
    experiment_id: Optional[str] = Field(None, description="Associated experiment ID")
    log_dir: str = Field(..., description="Path to log directory")
    description: Optional[str] = Field(None, description="Instance description")


class TensorBoardUpdate(BaseModel):
    """Request to update a TensorBoard instance"""

    name: Optional[str] = Field(None, description="Instance name")
    description: Optional[str] = Field(None, description="Instance description")


class TensorBoardActionRequest(BaseModel):
    """Request to perform action on TensorBoard instance"""

    action: str = Field(..., description="Action to perform: start, stop, restart")


class TensorBoardResponse(BaseModel):
    """TensorBoard instance response"""

    id: str
    name: str
    experiment_id: Optional[str]
    log_dir: str
    status: str
    url: Optional[str]
    created_at: datetime
    updated_at: datetime


class TensorBoardListResponse(BaseModel):
    """Response for TensorBoard list"""

    items: List[TensorBoardResponse]
    total: int
    page: int
    page_size: int


class TensorBoardMetricsResponse(BaseModel):
    """TensorBoard metrics response"""

    instance_id: str
    metrics: Dict[str, Any]


class TensorBoardStatsResponse(BaseModel):
    """TensorBoard statistics response"""

    total_instances: int
    active_instances: int
    total_experiments: int


# Endpoints
@router.post("/", response_model=TensorBoardResponse)
async def create_tensorboard_instance(
    data: TensorBoardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new TensorBoard instance

    Launches a TensorBoard server for viewing training logs.
    """
    manager = TensorBoardManager(db)

    instance = await manager.create_instance(
        name=data.name,
        experiment_id=data.experiment_id,
        log_dir=data.log_dir,
        description=data.description,
        owner_id=str(current_user.id),
    )

    return TensorBoardResponse(
        id=instance.id,
        name=instance.name,
        experiment_id=instance.experiment_id,
        log_dir=instance.log_dir,
        status=instance.status,
        url=instance.url,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("/", response_model=TensorBoardListResponse)
async def list_tensorboard_instances(
    experiment_id: Optional[str] = Query(None, description="Filter by experiment ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List TensorBoard instances

    Returns paginated list of TensorBoard instances.
    """
    manager = TensorBoardManager(db)

    filters = {}
    if experiment_id:
        filters["experiment_id"] = experiment_id
    if status:
        filters["status"] = status

    instances, total = await manager.list_instances(
        filters=filters,
        limit=limit,
        offset=offset,
        owner_id=str(current_user.id),
    )

    return TensorBoardListResponse(
        items=[
            TensorBoardResponse(
                id=inst.id,
                name=inst.name,
                experiment_id=inst.experiment_id,
                log_dir=inst.log_dir,
                status=inst.status,
                url=inst.url,
                created_at=inst.created_at,
                updated_at=inst.updated_at,
            )
            for inst in instances
        ],
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get("/{instance_id}", response_model=TensorBoardResponse)
async def get_tensorboard_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get TensorBoard instance details

    Returns detailed information about a specific TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TensorBoard instance not found",
        )

    return TensorBoardResponse(
        id=instance.id,
        name=instance.name,
        experiment_id=instance.experiment_id,
        log_dir=instance.log_dir,
        status=instance.status,
        url=instance.url,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.put("/{instance_id}", response_model=TensorBoardResponse)
async def update_tensorboard_instance(
    instance_id: str,
    data: TensorBoardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update TensorBoard instance

    Updates name or description of a TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    instance = await manager.update_instance(
        instance_id=instance_id,
        name=data.name,
        description=data.description,
    )

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TensorBoard instance not found",
        )

    return TensorBoardResponse(
        id=instance.id,
        name=instance.name,
        experiment_id=instance.experiment_id,
        log_dir=instance.log_dir,
        status=instance.status,
        url=instance.url,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tensorboard_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete TensorBoard instance

    Permanently deletes a TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    success = await manager.delete_instance(instance_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TensorBoard instance not found",
        )


@router.post("/{instance_id}/actions", response_model=TensorBoardResponse)
async def control_tensorboard_instance(
    instance_id: str,
    action: TensorBoardActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Control TensorBoard instance

    Start, stop, or restart a TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    if action.action == "start":
        instance = await manager.start_instance(instance_id)
    elif action.action == "stop":
        instance = await manager.stop_instance(instance_id)
    elif action.action == "restart":
        instance = await manager.restart_instance(instance_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action.action}",
        )

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TensorBoard instance not found",
        )

    return TensorBoardResponse(
        id=instance.id,
        name=instance.name,
        experiment_id=instance.experiment_id,
        log_dir=instance.log_dir,
        status=instance.status,
        url=instance.url,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("/{instance_id}/url", response_model=Dict[str, str])
async def get_tensorboard_url(
    instance_id: str,
    ttl: int = Query(3600, ge=60, le=86400, description="URL time-to-live in seconds"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get TensorBoard access URL

    Returns a time-limited access URL for the TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    url = await manager.get_instance_url(instance_id, ttl=ttl)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TensorBoard instance not found or not running",
        )

    return {"url": url, "ttl": ttl}


@router.get("/{instance_id}/proxy/{path:path}")
async def proxy_tensorboard(
    instance_id: str,
    request: Request,
    path: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Proxy TensorBoard requests

    Proxies requests to the TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    # In production, this would proxy to the actual TensorBoard server
    return {"message": "TensorBoard proxy", "instance_id": instance_id, "path": path}


@router.get("/{instance_id}/metrics", response_model=TensorBoardMetricsResponse)
async def get_tensorboard_metrics(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get TensorBoard metrics

    Returns metrics from the TensorBoard instance.
    """
    manager = TensorBoardManager(db)

    metrics = await manager.get_instance_metrics(instance_id)

    return TensorBoardMetricsResponse(
        instance_id=instance_id,
        metrics=metrics,
    )


@router.get("/stats/summary", response_model=TensorBoardStatsResponse)
async def get_tensorboard_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get TensorBoard statistics

    Returns overall statistics about TensorBoard instances.
    """
    manager = TensorBoardManager(db)

    stats = await manager.get_statistics()

    return TensorBoardStatsResponse(
        total_instances=stats.get("total_instances", 0),
        active_instances=stats.get("active_instances", 0),
        total_experiments=stats.get("total_experiments", 0),
    )


@router.post("/cleanup/idle", response_model=Dict[str, Any])
async def cleanup_idle_instances(
    idle_timeout_minutes: int = Query(60, ge=1, le=1440, description="Idle timeout in minutes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cleanup idle TensorBoard instances

    Stops TensorBoard instances that have been idle for too long.
    """
    manager = TensorBoardManager(db)

    stopped_count = await manager.cleanup_idle_instances(idle_timeout_minutes)

    return {
        "stopped_count": stopped_count,
        "idle_timeout_minutes": idle_timeout_minutes,
    }
