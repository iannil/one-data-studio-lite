"""
GPU Resource Management API Endpoints

Provides REST API for GPU pool management, VGPU allocation, and scheduling.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.models.user import User
from app.services.gpu import (
    GPUType,
    GPUAllocationStrategy,
    SchedulingPolicy,
    TaskPriority,
    get_gpu_pool_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gpu", tags=["GPU Resource Management"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class GPURequestRequest(BaseModel):
    """Request for GPU allocation"""
    resource_name: str = Field(..., description="Name of the resource requesting GPU")
    vgpu_count: int = Field(1, ge=1, le=64, description="Number of virtual GPUs")
    gpu_type: Optional[GPUType] = Field(None, description="Preferred GPU type")
    memory_mb: Optional[int] = Field(None, ge=1024, description="Memory required per VGPU in MB")
    strategy: GPUAllocationStrategy = Field(
        GPUAllocationStrategy.EXCLUSIVE,
        description="Allocation strategy",
    )
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority")
    estimated_duration_minutes: Optional[int] = Field(
        None,
        ge=1,
        description="Estimated task duration in minutes",
    )


class GPUReleaseRequest(BaseModel):
    """Request to release GPU allocation"""
    resource_name: str = Field(..., description="Name of the resource to release")


class VGPUCreateRequest(BaseModel):
    """Request to create VGPU instances"""
    gpu_id: str = Field(..., description="Physical GPU ID")
    count: int = Field(1, ge=1, le=16, description="Number of VGPU instances to create")
    memory_per_vgpu: int = Field(..., ge=1024, description="Memory per VGPU in MB")
    cpu_cores_per_vgpu: float = Field(1.0, ge=0.1, description="CPU cores per VGPU")


class GPUMetricsUpdate(BaseModel):
    """Update GPU metrics"""
    gpu_id: str
    utilization_percent: float = Field(..., ge=0, le=100)
    memory_used_mb: int = Field(..., ge=0)
    temperature_celsius: float = Field(..., ge=0, le=120)
    power_draw_watts: float = Field(..., ge=0)


class TaskSubmitRequest(BaseModel):
    """Submit a GPU task"""
    task_id: Optional[str] = None  # Auto-generated if not provided
    resource_name: str
    vgpu_count: int = Field(1, ge=1, le=64)
    gpu_type: Optional[GPUType] = None
    memory_mb: Optional[int] = None
    strategy: GPUAllocationStrategy = GPUAllocationStrategy.EXCLUSIVE
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration_minutes: Optional[int] = None
    allowed_gpu_ids: Optional[List[str]] = None
    forbidden_gpu_ids: Optional[List[str]] = None


# ============================================================================
# Pool Management Endpoints
# ============================================================================


@router.get("/pool/status")
async def get_pool_status(
    current_user: User = Depends(get_current_user),
):
    """Get overall GPU pool status"""
    try:
        manager = get_gpu_pool_manager()
        status = manager.get_pool_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/gpus")
async def list_gpus(
    gpu_type: Optional[GPUType] = None,
    healthy_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List physical GPUs"""
    try:
        manager = get_gpu_pool_manager()
        allocator = manager.allocator

        gpus = allocator.list_gpus(gpu_type)
        if healthy_only:
            gpus = [g for g in gpus if g.is_healthy]

        return [
            {
                "gpu_id": g.gpu_id,
                "name": g.name,
                "type": g.gpu_type.value,
                "total_memory_mb": g.total_memory_mb,
                "used_memory_mb": g.memory_used_mb,
                "available_memory_mb": g.available_memory_mb,
                "utilization_percent": g.utilization_percent,
                "temperature_celsius": g.temperature_celsius,
                "power_draw_watts": g.power_draw_watts,
                "healthy": g.is_healthy,
                "utilization_status": g.utilization_status,
                "max_vgpu_instances": g.max_vgpu_instances,
                "vgpu_instances": len(g.vgpu_instances),
                "active_vgpus": len([v for v in g.vgpu_instances if not v.is_available]),
                "available_vgpu_slots": g.available_vgpu_slots,
                "mig_enabled": g.mig_enabled,
                "driver_version": g.driver_version,
                "cuda_version": g.cuda_version,
            }
            for g in gpus
        ]
    except Exception as e:
        logger.error(f"Failed to list GPUs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/gpus/{gpu_id}")
async def get_gpu_details(
    gpu_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific GPU"""
    try:
        manager = get_gpu_pool_manager()
        details = manager.get_gpu_details(gpu_id)

        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU {gpu_id} not found",
            )

        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GPU details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/gpus/{gpu_id}/metrics")
async def update_gpu_metrics(
    gpu_id: str,
    metrics: GPUMetricsUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update GPU metrics (called by monitoring agent)"""
    try:
        manager = get_gpu_pool_manager()
        manager.allocator.update_gpu_metrics(
            gpu_id=gpu_id,
            utilization_percent=metrics.utilization_percent,
            memory_used_mb=metrics.memory_used_mb,
            temperature_celsius=metrics.temperature_celsius,
            power_draw_watts=metrics.power_draw_watts,
        )
        return {"message": "Metrics updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update GPU metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# VGPU Management Endpoints
# ============================================================================


@router.post("/vgpu/create")
async def create_vgpu_instances(
    request: VGPUCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create virtual GPU instances on a physical GPU"""
    try:
        manager = get_gpu_pool_manager()
        vgpu_instances = manager.allocator.create_vgpu_instances(
            gpu_id=request.gpu_id,
            count=request.count,
            memory_per_vgpu=request.memory_per_vgpu,
            cpu_cores_per_vgpu=request.cpu_cores_per_vgpu,
        )

        return {
            "message": f"Created {len(vgpu_instances)} VGPU instances",
            "vgpu_ids": [v.vgpu_id for v in vgpu_instances],
            "gpu_id": request.gpu_id,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create VGPU instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/vgpu/instances")
async def list_vgpu_instances(
    gpu_id: Optional[str] = None,
    allocated_only: bool = False,
    available_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List VGPU instances"""
    try:
        manager = get_gpu_pool_manager()
        allocator = manager.allocator

        instances = []
        for vgpu_id, vgpu in allocator.vgpu_instances.items():
            if gpu_id and vgpu.parent_gpu_id != gpu_id:
                continue
            if allocated_only and vgpu.is_available:
                continue
            if available_only and not vgpu.is_available:
                continue

            instances.append({
                "vgpu_id": vgpu.vgpu_id,
                "parent_gpu_id": vgpu.parent_gpu_id,
                "memory_mb": vgpu.memory_mb,
                "cpu_cores": vgpu.cpu_cores,
                "vgpu_index": vgpu.vgpu_index,
                "allocated_to": vgpu.allocated_to,
                "allocated_at": vgpu.allocated_at.isoformat() if vgpu.allocated_at else None,
                "allocation_type": vgpu.allocation_type.value if vgpu.allocation_type else None,
                "is_available": vgpu.is_available,
                "utilization_percent": vgpu.utilization_percent,
                "memory_used_mb": vgpu.memory_used_mb,
                "memory_utilization": vgpu.memory_utilization,
            })

        return instances
    except Exception as e:
        logger.error(f"Failed to list VGPU instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Allocation Endpoints
# ============================================================================


@router.post("/allocate")
async def allocate_gpu(
    request: GPURequestRequest,
    current_user: User = Depends(get_current_user),
):
    """Allocate GPU for a resource"""
    try:
        manager = get_gpu_pool_manager()
        result = manager.request_gpu(
            resource_name=request.resource_name,
            vgpu_count=request.vgpu_count,
            gpu_type=request.gpu_type,
            memory_mb=request.memory_mb,
            strategy=request.strategy,
            priority=request.priority,
            estimated_duration_minutes=request.estimated_duration_minutes,
        )

        return result
    except Exception as e:
        logger.error(f"Failed to allocate GPU: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/release")
async def release_gpu(
    request: GPUReleaseRequest,
    current_user: User = Depends(get_current_user),
):
    """Release GPU allocation for a resource"""
    try:
        manager = get_gpu_pool_manager()
        released = manager.release_gpu(request.resource_name)

        if not released:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No allocation found for resource: {request.resource_name}",
            )

        return {"message": f"Released GPU allocation for {request.resource_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to release GPU: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/allocations")
async def list_allocations(
    resource_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List GPU allocations"""
    try:
        manager = get_gpu_pool_manager()
        allocator = manager.allocator

        allocations = allocator.list_allocations(resource_name)

        return [
            {
                "allocation_id": a.allocation_id,
                "request_id": a.request_id,
                "resource_name": a.resource_name,
                "gpu_id": a.gpu_id,
                "vgpu_ids": a.vgpu_ids,
                "vgpu_count": len(a.vgpu_ids),
                "allocated_at": a.allocated_at.isoformat(),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                "strategy": a.strategy.value,
                "memory_mb": a.memory_mb,
            }
            for a in allocations
        ]
    except Exception as e:
        logger.error(f"Failed to list allocations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/allocations/{allocation_id}")
async def deallocate_gpu(
    allocation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Deallocate a specific GPU allocation"""
    try:
        manager = get_gpu_pool_manager()
        success = manager.allocator.deallocate(allocation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Allocation {allocation_id} not found",
            )

        return {"message": f"Deallocated GPU allocation: {allocation_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deallocate GPU: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Scheduling Endpoints
# ============================================================================


@router.post("/tasks/submit")
async def submit_task(
    request: TaskSubmitRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit a task to the GPU scheduler"""
    try:
        import uuid

        manager = get_gpu_pool_manager()

        task_id = request.task_id or f"task-{uuid.uuid4()}"
        from app.services.gpu import GPUTask

        task = GPUTask(
            task_id=task_id,
            resource_name=request.resource_name,
            gpu_type=request.gpu_type,
            vgpu_count=request.vgpu_count,
            memory_mb=request.memory_mb,
            strategy=request.strategy,
            priority=request.priority,
            estimated_duration_minutes=request.estimated_duration_minutes,
            allowed_gpu_ids=set(request.allowed_gpu_ids) if request.allowed_gpu_ids else None,
            forbidden_gpu_ids=set(request.forbidden_gpu_ids) if request.forbidden_gpu_ids else None,
        )

        decision = manager.scheduler.submit_task(task)

        return {
            "task_id": task_id,
            "scheduled": decision.scheduled,
            "allocation_id": decision.allocation_id,
            "gpu_ids": decision.gpu_ids,
            "reason": decision.reason,
            "estimated_start_time": decision.estimated_start_time.isoformat() if decision.estimated_start_time else None,
            "queue_position": decision.queue_position,
        }
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed"),
    resource_name: Optional[str] = Query(None, description="Filter by resource name"),
    current_user: User = Depends(get_current_user),
):
    """List GPU tasks"""
    try:
        manager = get_gpu_pool_manager()
        tasks = manager.scheduler.list_tasks(status=status, resource_name=resource_name)
        return tasks
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of a specific task"""
    try:
        manager = get_gpu_pool_manager()
        status = manager.scheduler.get_task_status(task_id)

        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or running task"""
    try:
        manager = get_gpu_pool_manager()
        success = manager.scheduler.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        return {"message": f"Task {task_id} cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    success: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Mark a task as complete (called by task execution system)"""
    try:
        manager = get_gpu_pool_manager()
        task_success = manager.scheduler.complete_task(task_id, success)

        if not task_success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or not running",
            )

        return {"message": f"Task {task_id} marked as complete"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/queue/stats")
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
):
    """Get scheduling queue statistics"""
    try:
        manager = get_gpu_pool_manager()
        stats = manager.scheduler.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/scheduler/policy")
async def set_scheduling_policy(
    policy: SchedulingPolicy,
    current_user: User = Depends(get_current_user),
):
    """Set the scheduling policy"""
    try:
        manager = get_gpu_pool_manager()
        manager.scheduler.set_scheduling_policy(policy)
        return {"message": f"Scheduling policy set to {policy.value}"}
    except Exception as e:
        logger.error(f"Failed to set scheduling policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Monitoring Endpoints
# ============================================================================


@router.get("/monitoring/summary")
async def get_monitoring_summary(
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive GPU monitoring summary"""
    try:
        manager = get_gpu_pool_manager()
        pool_status = manager.get_pool_status()

        # Calculate additional metrics
        total_gpus = pool_status["cluster_stats"]["total_gpus"]
        healthy_gpus = pool_status["cluster_stats"]["healthy_gpus"]
        avg_utilization = 0.0

        if pool_status["gpus"]:
            avg_utilization = sum(g["utilization_percent"] for g in pool_status["gpus"]) / len(
                pool_status["gpus"]
            )

        # Get utilization status breakdown
        utilization_status_counts: Dict[str, int] = {}
        for gpu in pool_status["gpus"]:
            status = gpu["utilization_status"]
            utilization_status_counts[status] = utilization_status_counts.get(status, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "total_gpus": total_gpus,
            "healthy_gpus": healthy_gpus,
            "unhealthy_gpus": total_gpus - healthy_gpus,
            "avg_utilization_percent": avg_utilization,
            "utilization_status_counts": utilization_status_counts,
            "total_memory_mb": pool_status["cluster_stats"]["total_memory_mb"],
            "used_memory_mb": pool_status["cluster_stats"]["used_memory_mb"],
            "memory_utilization_percent": pool_status["cluster_stats"]["memory_utilization_percent"],
            "total_vgpu_instances": pool_status["cluster_stats"]["total_vgpu_instances"],
            "active_allocations": pool_status["cluster_stats"]["active_allocations"],
            "pending_tasks": pool_status["queue_stats"]["pending_tasks"],
            "running_tasks": pool_status["queue_stats"]["running_tasks"],
            "avg_wait_time_seconds": pool_status["queue_stats"]["avg_wait_time_seconds"],
        }
    except Exception as e:
        logger.error(f"Failed to get monitoring summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/gpu-types")
async def list_gpu_types(
    current_user: User = Depends(get_current_user),
):
    """List supported GPU types"""
    return {
        "gpu_types": [
            {
                "type": GPUType.NVIDIA_H100.value,
                "name": "NVIDIA H100 Hopper",
                "memory_gb": 80,
                "cuda_cores": 18432,
                "supports_mig": True,
                "max_mig_instances": 7,
            },
            {
                "type": GPUType.NVIDIA_A100.value,
                "name": "NVIDIA A100 Ampere",
                "memory_gb": 40,
                "cuda_cores": 6912,
                "supports_mig": True,
                "max_mig_instances": 7,
            },
            {
                "type": GPUType.NVIDIA_A30.value,
                "name": "NVIDIA A30 Ampere",
                "memory_gb": 24,
                "cuda_cores": 5888,
                "supports_mig": False,
                "max_mig_instances": 8,
            },
            {
                "type": GPUType.NVIDIA_A10G.value,
                "name": "NVIDIA A10G Ampere",
                "memory_gb": 24,
                "cuda_cores": 15360,
                "supports_mig": False,
                "max_mig_instances": 8,
            },
            {
                "type": GPUType.NVIDIA_V100.value,
                "name": "NVIDIA V100 Volta",
                "memory_gb": 32,
                "cuda_cores": 5120,
                "supports_mig": False,
                "max_mig_instances": 8,
            },
            {
                "type": GPUType.NVIDIA_T4.value,
                "name": "NVIDIA T4 Turing",
                "memory_gb": 16,
                "cuda_cores": 2560,
                "supports_mig": False,
                "max_mig_instances": 8,
            },
        ]
    }
