"""
GPU Scheduling API Endpoints

Provides REST API for GPU allocation, monitoring,
and resource pool management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.gpu.gpu_scheduler import (
    get_gpu_scheduler,
    GPUScheduler,
    GPUType,
    GPUVendor,
    GPUMemory,
    GPUSpec,
    GPUAllocation,
)
from app.services.gpu.gpu_monitoring import (
    get_gpu_monitor,
    GPUMonitor,
    MetricType,
)
from app.services.gpu.resource_pool import (
    get_resource_pool_manager,
    ResourcePoolManager,
    ResourceType,
    PoolQuotaType,
    AllocationPolicy,
    ResourceQuota,
    ResourceRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gpu", tags=["GPU"])


# ============================================================================
# Request/Response Models
# ============================================================================


class GPUMemoryRequest(BaseModel):
    """GPU memory specification"""
    value: float
    unit: str = "GB"


class GPUSpecRequest(BaseModel):
    """GPU specification request"""
    gpu_type: GPUType
    vendor: GPUVendor = GPUVendor.NVIDIA
    count: int = 1
    memory: Optional[GPUMemoryRequest] = None


class GPUAllocateRequest(BaseModel):
    """GPU allocation request"""
    spec: GPUSpecRequest
    task_id: Optional[str] = None
    ttl_minutes: Optional[int] = None
    preferred_gpu_ids: Optional[List[str]] = None


class GPUResourceResponse(BaseModel):
    """GPU resource response"""
    gpu_id: str
    gpu_type: str
    vendor: str
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_percent: float
    temperature: Optional[int]
    power_usage_w: Optional[float]
    is_allocated: bool
    node_name: str


class GPUAllocationResponse(BaseModel):
    """GPU allocation response"""
    allocation_id: str
    gpu_ids: List[str]
    gpu_type: str
    count: int
    allocated_to: str
    allocated_at: datetime
    expires_at: Optional[datetime]


class GPUSummaryResponse(BaseModel):
    """Cluster GPU summary response"""
    total_gpus: int
    allocated_gpus: int
    free_gpus: int
    by_vendor: Dict[str, Dict[str, int]]
    by_type: Dict[str, Dict[str, int]]
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int


class ResourceQuotaRequest(BaseModel):
    """Resource quota request"""
    resource_type: ResourceType
    quota_type: PoolQuotaType = PoolQuotaType.HARD
    limit: float
    unit: str = "count"
    burst_limit: Optional[float] = None
    burst_duration_seconds: Optional[int] = None


class PoolCreateRequest(BaseModel):
    """Create pool request"""
    name: str
    node_names: List[str]
    quotas: Dict[str, ResourceQuotaRequest]
    allocation_policy: AllocationPolicy = AllocationPolicy.BEST_FIT
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None


class PoolResponse(BaseModel):
    """Pool response"""
    pool_id: str
    name: str
    description: Optional[str]
    allocation_policy: str
    node_names: List[str]
    enabled: bool
    active_allocations: int
    created_at: datetime


class PoolStatusResponse(BaseModel):
    """Pool status response"""
    pool_id: str
    name: str
    enabled: bool
    allocation_policy: str
    nodes: List[str]
    quotas: Dict[str, Dict[str, Any]]
    usage: Dict[str, float]
    available: Dict[str, float]
    active_allocations: int


class PoolAllocateRequest(BaseModel):
    """Allocate from pool request"""
    pool_id: str
    task_id: str
    resources: List[Dict[str, Any]]
    ttl_minutes: Optional[int] = None


class GPUMetricsResponse(BaseModel):
    """GPU metrics response"""
    gpu_id: str
    utilization_percent: float
    memory_used_mb: int
    memory_total_mb: int
    temperature: Optional[int]
    power_draw_w: Optional[float]
    fan_speed: Optional[str]
    pstate: Optional[str]
    clock_gpu_mhz: Optional[int]
    clock_mem_mhz: Optional[int]


# ============================================================================
# GPU Management Endpoints
# ============================================================================


@router.get("/resources", response_model=List[GPUResourceResponse])
async def list_gpu_resources(
    vendor: Optional[GPUVendor] = None,
    gpu_type: Optional[GPUType] = None,
    min_memory_gb: Optional[float] = None,
    unallocated_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List available GPU resources"""
    scheduler = get_gpu_scheduler(db)

    min_memory_mb = int(min_memory_gb * 1024) if min_memory_gb else None

    gpus = await scheduler.get_available_gpus(
        vendor=vendor,
        gpu_type=gpu_type,
        min_memory_mb=min_memory_mb,
        unallocated_only=unallocated_only,
    )

    return [
        GPUResourceResponse(
            gpu_id=gpu.gpu_id,
            gpu_type=gpu.gpu_type.value,
            vendor=gpu.vendor.value,
            total_memory_mb=gpu.total_memory_mb,
            used_memory_mb=gpu.used_memory_mb,
            free_memory_mb=gpu.free_memory_mb,
            utilization_percent=gpu.utilization_percent,
            temperature=gpu.temperature,
            power_usage_w=gpu.power_usage_w,
            is_allocated=gpu.is_allocated,
            node_name=gpu.node_name,
        )
        for gpu in gpus
    ]


@router.get("/summary", response_model=GPUSummaryResponse)
async def get_gpu_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cluster-wide GPU summary"""
    scheduler = get_gpu_scheduler(db)

    summary = await scheduler.get_cluster_gpu_summary()

    return GPUSummaryResponse(
        total_gpus=summary["total_gpus"],
        allocated_gpus=summary["allocated_gpus"],
        free_gpus=summary["free_gpus"],
        by_vendor=summary["by_vendor"],
        by_type=summary["by_type"],
        total_memory_mb=summary["total_memory_mb"],
        used_memory_mb=summary["used_memory_mb"],
        free_memory_mb=summary["free_memory_mb"],
    )


@router.post("/allocate", response_model=GPUAllocationResponse)
async def allocate_gpu(
    request: GPUAllocateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allocate GPUs"""
    scheduler = get_gpu_scheduler(db)

    # Convert request to GPUSpec
    memory = None
    if request.spec.memory:
        memory = GPUMemory(
            value=request.spec.memory.value,
            unit=request.spec.memory.unit,
        )

    spec = GPUSpec(
        gpu_type=request.spec.gpu_type,
        vendor=request.spec.vendor,
        count=request.spec.count,
        memory=memory,
    )

    task_id = request.task_id or f"task-{current_user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    allocation = await scheduler.allocate(
        spec=spec,
        allocated_to=task_id,
        ttl_minutes=request.ttl_minutes,
        preferred_gpu_ids=request.preferred_gpu_ids,
    )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No available GPUs matching specification"
        )

    return GPUAllocationResponse(
        allocation_id=allocation.allocation_id,
        gpu_ids=allocation.gpu_ids,
        gpu_type=allocation.spec.gpu_type.value,
        count=len(allocation.gpu_ids),
        allocated_to=allocation.allocated_to,
        allocated_at=allocation.allocated_at,
        expires_at=allocation.expires_at,
    )


@router.delete("/allocations/{allocation_id}")
async def deallocate_gpu(
    allocation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deallocate GPUs"""
    scheduler = get_gpu_scheduler(db)

    success = await scheduler.deallocate(allocation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )

    return {"success": True, "message": "GPU deallocated"}


@router.get("/allocations", response_model=List[GPUAllocationResponse])
async def list_gpu_allocations(
    task_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List GPU allocations"""
    scheduler = get_gpu_scheduler(db)

    allocations = await scheduler.list_allocations(allocated_to=task_id)

    return [
        GPUAllocationResponse(
            allocation_id=a.allocation_id,
            gpu_ids=a.gpu_ids,
            gpu_type=a.spec.gpu_type.value,
            count=len(a.gpu_ids),
            allocated_to=a.allocated_to,
            allocated_at=a.allocated_at,
            expires_at=a.expires_at,
        )
        for a in allocations
    ]


# ============================================================================
# GPU Metrics Endpoints
# ============================================================================


@router.get("/metrics/{gpu_id}", response_model=GPUMetricsResponse)
async def get_gpu_metrics(
    gpu_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current metrics for a GPU"""
    monitor = get_gpu_monitor(db)

    metrics = await monitor.get_current_metrics(gpu_id)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GPU not found or metrics unavailable"
        )

    return GPUMetricsResponse(
        gpu_id=gpu_id,
        utilization_percent=metrics.get("gpu_util", 0),
        memory_used_mb=metrics.get("mem_used", 0),
        memory_total_mb=metrics.get("mem_total", 0),
        temperature=metrics.get("temperature"),
        power_draw_w=metrics.get("power_draw"),
        fan_speed=metrics.get("fan_speed"),
        pstate=metrics.get("pstate"),
        clock_gpu_mhz=metrics.get("gpu_clock"),
        clock_mem_mhz=metrics.get("mem_clock"),
    )


@router.get("/metrics")
async def get_cluster_metrics(
    format: str = Query("json", regex="^(json|prometheus)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cluster-wide GPU metrics"""
    monitor = get_gpu_monitor(db)

    if format == "json":
        metrics = await monitor.get_cluster_metrics()
        return metrics
    else:
        # Prometheus format
        metrics = await monitor.export_metrics(format="prometheus")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=metrics,
            media_type="text/plain"
        )


# ============================================================================
# Resource Pool Endpoints
# ============================================================================


@router.post("/pools", response_model=PoolResponse)
async def create_pool(
    request: PoolCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a resource pool"""
    manager = get_resource_pool_manager(db)

    # Convert quotas
    quotas = {}
    for key, quota_req in request.quotas.items():
        quotas[ResourceType(key)] = ResourceQuota(
            resource_type=quota_req.resource_type,
            quota_type=quota_req.quota_type,
            limit=quota_req.limit,
            unit=quota_req.unit,
            burst_limit=quota_req.burst_limit,
            burst_duration_seconds=quota_req.burst_duration_seconds,
        )

    pool = await manager.create_pool(
        name=request.name,
        node_names=request.node_names,
        quotas=quotas,
        allocation_policy=request.allocation_policy,
        labels=request.labels,
        description=request.description,
    )

    return PoolResponse(
        pool_id=pool.pool_id,
        name=pool.name,
        description=pool.description,
        allocation_policy=pool.allocation_policy.value,
        node_names=pool.node_names,
        enabled=pool.enabled,
        active_allocations=0,
        created_at=pool.created_at,
    )


@router.get("/pools", response_model=List[PoolResponse])
async def list_pools(
    enabled_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all resource pools"""
    manager = get_resource_pool_manager(db)

    pools = await manager.list_pools(enabled_only=enabled_only)

    # Get active allocations count for each pool
    allocations = await manager.list_allocations()
    allocation_counts = {}
    for alloc in allocations:
        if alloc.pool_id not in allocation_counts:
            allocation_counts[alloc.pool_id] = 0
        allocation_counts[alloc.pool_id] += 1

    return [
        PoolResponse(
            pool_id=p.pool_id,
            name=p.name,
            description=p.description,
            allocation_policy=p.allocation_policy.value,
            node_names=p.node_names,
            enabled=p.enabled,
            active_allocations=allocation_counts.get(p.pool_id, 0),
            created_at=p.created_at,
        )
        for p in pools
    ]


@router.get("/pools/{pool_id}", response_model=PoolStatusResponse)
async def get_pool_status(
    pool_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get pool status"""
    manager = get_resource_pool_manager(db)

    status = await manager.get_pool_status(pool_id)

    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pool not found"
        )

    return PoolStatusResponse(**status)


@router.delete("/pools/{pool_id}")
async def delete_pool(
    pool_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a resource pool"""
    manager = get_resource_pool_manager(db)

    success = await manager.delete_pool(pool_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pool not found or has active allocations"
        )

    return {"success": True, "message": "Pool deleted"}


@router.post("/pools/allocate")
async def allocate_from_pool(
    request: PoolAllocateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allocate resources from a pool"""
    manager = get_resource_pool_manager(db)

    # Convert resource requests
    requests = []
    for r in request.resources:
        req = ResourceRequest(
            resource_type=ResourceType(r["resource_type"]),
            amount=r["amount"],
            unit=r.get("unit", "count"),
            gpu_type=GPUType(r["gpu_type"]) if r.get("gpu_type") else None,
            gpu_vendor=GPUVendor(r["gpu_vendor"]) if r.get("gpu_vendor") else None,
        )
        requests.append(req)

    allocation = await manager.allocate_from_pool(
        pool_id=request.pool_id,
        task_id=request.task_id,
        user_id=str(current_user.id),
        requests=requests,
        ttl_minutes=request.ttl_minutes,
    )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation failed - insufficient resources"
        )

    return {
        "allocation_id": allocation.allocation_id,
        "pool_id": allocation.pool_id,
        "task_id": allocation.task_id,
        "resources": {rt.value: {"amount": r.amount, "unit": r.unit}
                      for rt, r in allocation.resources.items()},
        "allocated_at": allocation.allocated_at,
        "expires_at": allocation.expires_at,
    }


@router.delete("/pools/allocations/{allocation_id}")
async def deallocate_from_pool(
    allocation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deallocate resources from a pool"""
    manager = get_resource_pool_manager(db)

    success = await manager.deallocate_from_pool(allocation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )

    return {"success": True, "message": "Resources deallocated"}


@router.get("/pools/allocations")
async def list_pool_allocations(
    pool_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List pool allocations"""
    manager = get_resource_pool_manager(db)

    allocations = await manager.list_allocations(
        pool_id=pool_id,
        user_id=str(current_user.id) if not pool_id else None,
    )

    return {
        "allocations": [
            {
                "allocation_id": a.allocation_id,
                "pool_id": a.pool_id,
                "task_id": a.task_id,
                "user_id": a.user_id,
                "resources": {rt.value: {"amount": r.amount, "unit": r.unit}
                              for rt, r in a.resources.items()},
                "allocated_at": a.allocated_at,
                "expires_at": a.expires_at,
            }
            for a in allocations
        ]
    }


@router.post("/maintenance/cleanup")
async def cleanup_expired_allocations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clean up expired allocations"""
    scheduler = get_gpu_scheduler(db)
    manager = get_resource_pool_manager(db)

    gpu_count = await scheduler.cleanup_expired_allocations()
    pool_count = await manager.cleanup_expired_allocations()

    return {
        "success": True,
        "gpu_allocations_cleaned": gpu_count,
        "pool_allocations_cleaned": pool_count,
    }


@router.get("/cluster/summary")
async def get_cluster_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cluster-wide resource summary"""
    manager = get_resource_pool_manager(db)

    summary = await manager.get_cluster_summary()

    return summary
