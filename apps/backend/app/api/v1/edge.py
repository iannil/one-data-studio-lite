"""
Edge Computing API Endpoints

Provides REST API for edge computing:
- Node management
- Model deployment
- Job execution
- Metrics collection
- Device management
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.edge import (
    EdgeNode,
    EdgeModel,
    EdgeDeployment,
    EdgeJob,
    EdgeDevice,
    EdgeMetrics,
    NodeStatus,
    DeploymentStatus,
    JobStatus,
)
from app.services.edge.manager import (
    EdgeNodeManager,
    EdgeDeploymentManager,
    EdgeJobManager,
    EdgeMetricsCollector,
    DeploymentConfig,
    get_node_manager,
    get_deployment_manager,
    get_job_manager,
    get_metrics_collector,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["Edge Computing"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class RegisterNodeRequest(BaseModel):
    """Request to register an edge node"""
    name: str = Field(..., min_length=1, max_length=256)
    hardware_model: str = Field(..., min_length=1, max_length=100)
    cpu_cores: int = Field(..., ge=1, le=128)
    memory_mb: int = Field(..., ge=512, le=524288)
    ip_address: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[List[str]] = None
    group: Optional[str] = None


class HeartbeatRequest(BaseModel):
    """Edge node heartbeat"""
    status: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_mb: Optional[int] = None
    gpu_percent: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    gpu_temperature: Optional[int] = None


class DeployModelRequest(BaseModel):
    """Request to deploy model to edge"""
    model_id: str
    name: str = Field(..., min_length=1, max_length=256)
    batch_size: int = Field(1, ge=1, le=128)
    precision: str = "fp32"
    num_workers: int = Field(2, ge=1, le=16)
    update_strategy: str = "manual"


class CreateJobRequest(BaseModel):
    """Request to create edge job"""
    name: str = Field(..., min_length=1, max_length=256)
    job_type: str
    node_id: str
    config: Dict[str, Any]
    deployment_id: Optional[str] = None
    schedule_cron: Optional[str] = None


class RecordInferenceRequest(BaseModel):
    """Record inference result"""
    deployment_id: str
    node_id: str
    output: Dict[str, Any]
    latency_ms: int = Field(..., ge=0)
    pre_processing_ms: Optional[int] = None
    inference_ms: Optional[int] = None
    post_processing_ms: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None


# ============================================================================
# Node Endpoints
# ============================================================================


@router.post("/nodes/register", response_model=Dict[str, Any])
async def register_node(
    request: RegisterNodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new edge node"""
    try:
        manager = get_node_manager()

        node = await manager.register_node(
            db=db,
            name=request.name,
            hardware_model=request.hardware_model,
            cpu_cores=request.cpu_cores,
            memory_mb=request.memory_mb,
            owner_id=str(current_user.id),
            ip_address=request.ip_address,
            location=request.location,
            capabilities=request.capabilities,
        )

        return {
            "node_id": node.node_id,
            "name": node.name,
            "status": node.status,
            "created_at": node.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to register node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/nodes", response_model=List[Dict[str, Any]])
async def list_nodes(
    status: Optional[str] = None,
    group: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List edge nodes"""
    try:
        manager = get_node_manager()

        nodes = await manager.list_nodes(
            db=db,
            owner_id=str(current_user.id),
            status=status,
            group=group,
        )

        return [
            {
                "node_id": n.node_id,
                "name": n.name,
                "hardware_model": n.hardware_model,
                "cpu_cores": n.cpu_cores,
                "memory_mb": n.memory_mb,
                "location": n.location,
                "status": n.status,
                "ip_address": n.ip_address,
                "capabilities": n.capabilities,
                "group": n.group,
                "deployment_count": n.deployment_count,
                "job_count": n.job_count,
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in nodes
        ]

    except Exception as e:
        logger.error(f"Failed to list nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/nodes/{node_id}", response_model=Dict[str, Any])
async def get_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get node details"""
    try:
        result = await db.execute(
            select(EdgeNode).where(EdgeNode.node_id == node_id)
        )
        node = result.scalar_one_or_none()

        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node {node_id} not found",
            )

        return {
            "node_id": node.node_id,
            "name": node.name,
            "description": node.description,
            "location": node.location,
            "latitude": node.latitude,
            "longitude": node.longitude,
            "hardware_model": node.hardware_model,
            "cpu_cores": node.cpu_cores,
            "memory_mb": node.memory_mb,
            "storage_gb": node.storage_gb,
            "gpu_model": node.gpu_model,
            "gpu_memory_mb": node.gpu_memory_mb,
            "npu_model": node.npu_model,
            "ip_address": node.ip_address,
            "mac_address": node.mac_address,
            "network_type": node.network_type,
            "os_version": node.os_version,
            "agent_version": node.agent_version,
            "status": node.status,
            "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            "capabilities": node.capabilities,
            "group": node.group,
            "labels": node.labels,
            "deployment_count": node.deployment_count,
            "job_count": node.job_count,
            "created_at": node.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/nodes/{node_id}/heartbeat", response_model=Dict[str, Any])
async def node_heartbeat(
    node_id: str,
    request: HeartbeatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Receive heartbeat from edge node"""
    try:
        manager = get_node_manager()

        success = await manager.update_heartbeat(
            db=db,
            node_id=node_id,
            status=request.status,
            metrics={
                "cpu_percent": request.cpu_percent,
                "memory_percent": request.memory_percent,
                "memory_used_mb": request.memory_used_mb,
                "gpu_percent": request.gpu_percent,
                "gpu_memory_percent": request.gpu_memory_percent,
                "gpu_temperature": request.gpu_temperature,
            },
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node {node_id} not found",
            )

        return {"message": "Heartbeat received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Model Deployment Endpoints
# ============================================================================


@router.post("/deployments", response_model=Dict[str, Any])
async def deploy_model(
    request: DeployModelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy a model to an edge node"""
    try:
        manager = get_deployment_manager()

        config = DeploymentConfig(
            batch_size=request.batch_size,
            precision=request.precision,
            num_workers=request.num_workers,
        )

        result = await manager.deploy_model(
            db=db,
            model_id=request.model_id,
            node_id=current_user.id,  # For demo, use user_id as node_id
            name=request.name,
            config=config,
            update_strategy=request.update_strategy,
        )

        if result.status == DeploymentStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error,
            )

        return {
            "deployment_id": result.deployment_id,
            "status": result.status,
            "message": result.message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/deployments", response_model=List[Dict[str, Any]])
async def list_deployments(
    node_id: Optional[str] = None,
    model_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List model deployments"""
    try:
        manager = get_deployment_manager()

        deployments = await manager.list_deployments(
            db=db,
            node_id=node_id,
            model_id=model_id,
            status=status,
        )

        return [
            {
                "deployment_id": d.deployment_id,
                "model_id": d.model_id,
                "node_id": d.node_id,
                "name": d.name,
                "status": d.status,
                "config": d.config,
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
                "inference_count": d.inference_count,
                "health_status": d.health_status,
                "created_at": d.created_at.isoformat(),
            }
            for d in deployments
        ]

    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/deployments/{deployment_id}", response_model=Dict[str, Any])
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a deployment"""
    try:
        manager = get_deployment_manager()

        success = await manager.delete_deployment(db=db, deployment_id=deployment_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found",
            )

        return {"message": "Deployment deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Job Endpoints
# ============================================================================


@router.post("/jobs", response_model=Dict[str, Any])
async def create_job(
    request: CreateJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new edge job"""
    try:
        manager = get_job_manager()

        job = await manager.create_job(
            db=db,
            name=request.name,
            job_type=request.job_type,
            node_id=request.node_id,
            config=request.config,
            owner_id=str(current_user.id),
            deployment_id=request.deployment_id,
            schedule_cron=request.schedule_cron,
        )

        return {
            "job_id": job.job_id,
            "name": job.name,
            "job_type": job.job_type,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs(
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List edge jobs"""
    try:
        manager = get_job_manager()

        jobs = await manager.list_jobs(
            db=db,
            node_id=node_id,
            status=status,
            owner_id=str(current_user.id),
        )

        return [
            {
                "job_id": j.job_id,
                "name": j.name,
                "job_type": j.job_type,
                "node_id": j.node_id,
                "deployment_id": j.deployment_id,
                "status": j.status,
                "progress": j.progress,
                "current_step": j.current_step,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "duration_seconds": j.duration_seconds,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ]

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/jobs/{job_id}/start", response_model=Dict[str, Any])
async def start_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a job"""
    try:
        manager = get_job_manager()

        success = await manager.start_job(db=db, job_id=job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start job {job_id}",
            )

        return {"message": "Job started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Metrics Endpoints
# ============================================================================


@router.post("/inference", response_model=Dict[str, Any])
async def record_inference(
    request: RecordInferenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record inference result from edge"""
    try:
        collector = get_metrics_collector()

        result_id = await collector.record_inference(
            db=db,
            deployment_id=request.deployment_id,
            node_id=request.node_id,
            output=request.output,
            latency_ms=request.latency_ms,
            pre_processing_ms=request.pre_processing_ms,
            inference_ms=request.inference_ms,
            post_processing_ms=request.post_processing_ms,
            input_data=request.input_data,
        )

        return {
            "result_id": result_id,
            "message": "Inference recorded successfully",
        }

    except Exception as e:
        logger.error(f"Failed to record inference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/nodes/{node_id}/metrics", response_model=Dict[str, Any])
async def get_node_metrics(
    node_id: str,
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated metrics for a node"""
    try:
        collector = get_metrics_collector()

        metrics = await collector.aggregate_metrics(
            db=db,
            node_id=node_id,
            hours=hours,
        )

        return metrics

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
