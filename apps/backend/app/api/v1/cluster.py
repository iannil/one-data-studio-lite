"""
Cluster Management API Endpoints

APIs for managing multiple Kubernetes clusters.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.cluster.manager import (
    cluster_service,
    Cluster,
    ClusterStatus,
    ClusterType,
    ClusterSelector,
    GPUType,
    ClusterNodePool,
    ScheduledJob,
)


router = APIRouter()


# Request/Response Schemas
class ClusterCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)
    type: str = Field("managed", description="Cluster type: managed, attached, hybrid")
    api_endpoint: str = Field(..., description="Kubernetes API endpoint")
    region: str = Field(..., description="Cluster region")
    zone: str = Field("", description="Availability zone")
    kubeconfig: Optional[str] = Field(None, description="Kubeconfig (encrypted)")
    tags: List[str] = Field(default_factory=list)


class ClusterUpdateRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ClusterResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    status: str
    region: str
    zone: str
    kubernetes_version: str
    node_count: int
    cpu_capacity: int
    memory_capacity_gb: int
    gpu_capacity: int
    storage_capacity_gb: int
    utilization: Dict[str, float]
    tags: List[str]
    created_at: str


class NodePoolCreateRequest(BaseModel):
    cluster_id: str
    name: str
    instance_type: str
    node_count: int = Field(..., ge=1, le=100)
    cpu_per_node: int = Field(..., ge=1)
    memory_per_node_gb: int = Field(..., ge=1)
    gpu_per_node: int = Field(0, ge=0)
    gpu_type: Optional[str] = None
    auto_scaling: bool = False
    min_nodes: int = Field(1, ge=0)
    max_nodes: int = Field(10, ge=1)


class NodePoolResponse(BaseModel):
    id: str
    cluster_id: str
    name: str
    instance_type: str
    node_count: int
    min_nodes: int
    max_nodes: int
    cpu_per_node: int
    memory_per_node_gb: int
    gpu_per_node: int
    gpu_type: Optional[str]
    auto_scaling: bool
    phase: str


class JobScheduleRequest(BaseModel):
    name: str
    cpu_request: int = Field(..., ge=1)
    memory_request_gb: int = Field(..., ge=1)
    gpu_request: int = Field(0, ge=0)
    gpu_type: Optional[str] = None
    job_type: str = Field("training")
    preferred_regions: Optional[List[str]] = None
    required_tags: Optional[List[str]] = None


class JobResponse(BaseModel):
    id: str
    name: str
    cluster_id: str
    job_type: str
    cpu_request: int
    memory_request_gb: int
    gpu_request: int
    phase: str
    start_time: Optional[str]
    completion_time: Optional[str]


# Cluster Endpoints
@router.post("/clusters", response_model=ClusterResponse)
async def create_cluster(
    request: ClusterCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new cluster"""
    cluster = cluster_service.register_cluster(
        name=request.name,
        cluster_type=ClusterType(request.type),
        api_endpoint=request.api_endpoint,
        region=request.region,
        description=request.description,
        zone=request.zone,
        kubeconfig=request.kubeconfig,
        tags=request.tags,
    )

    return ClusterResponse(**cluster.to_dict())


@router.get("/clusters", response_model=List[ClusterResponse])
async def list_clusters(
    status: Optional[str] = Query(None, description="Filter by status"),
    region: Optional[str] = Query(None, description="Filter by region"),
    current_user: User = Depends(get_current_user),
):
    """List all clusters"""
    cluster_status = ClusterStatus(status) if status else None
    clusters = cluster_service.list_clusters(status=cluster_status, region=region)

    return [ClusterResponse(**c.to_dict()) for c in clusters]


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get cluster details"""
    cluster = cluster_service.get_cluster(cluster_id)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return ClusterResponse(**cluster.to_dict())


@router.put("/clusters/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: str,
    request: ClusterUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Update cluster"""
    update_data = {}
    if request.description is not None:
        update_data["description"] = request.description
    if request.tags is not None:
        update_data["tags"] = request.tags

    cluster = cluster_service.update_cluster(cluster_id, **update_data)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return ClusterResponse(**cluster.to_dict())


@router.delete("/clusters/{cluster_id}")
async def delete_cluster(
    cluster_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a cluster"""
    success = cluster_service.delete_cluster(cluster_id)

    if not success:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return {"message": "Cluster deleted"}


@router.post("/clusters/{cluster_id}/health")
async def update_cluster_health(
    cluster_id: str,
    healthy: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Update cluster health status"""
    success = cluster_service.update_cluster_health(cluster_id, healthy)

    if not success:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return {"message": "Health status updated"}


# Node Pool Endpoints
@router.post("/node-pools", response_model=NodePoolResponse)
async def create_node_pool(
    request: NodePoolCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a node pool"""
    gpu_type = GPUType(request.gpu_type) if request.gpu_type else None

    pool = cluster_service.create_node_pool(
        cluster_id=request.cluster_id,
        name=request.name,
        instance_type=request.instance_type,
        node_count=request.node_count,
        cpu_per_node=request.cpu_per_node,
        memory_per_node_gb=request.memory_per_node_gb,
        gpu_per_node=request.gpu_per_node,
        gpu_type=gpu_type,
        auto_scaling=request.auto_scaling,
        min_nodes=request.min_nodes,
        max_nodes=request.max_nodes,
    )

    if not pool:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return NodePoolResponse(
        id=pool.id,
        cluster_id=pool.cluster_id,
        name=pool.name,
        instance_type=pool.instance_type,
        node_count=pool.node_count,
        min_nodes=pool.min_nodes,
        max_nodes=pool.max_nodes,
        cpu_per_node=pool.cpu_per_node,
        memory_per_node_gb=pool.memory_per_node_gb,
        gpu_per_node=pool.gpu_per_node,
        gpu_type=pool.gpu_type.value if pool.gpu_type else None,
        auto_scaling=pool.auto_scaling,
        phase=pool.phase,
    )


@router.get("/clusters/{cluster_id}/node-pools", response_model=List[NodePoolResponse])
async def list_node_pools(
    cluster_id: str,
    current_user: User = Depends(get_current_user),
):
    """List node pools for a cluster"""
    pools = cluster_service.get_node_pools(cluster_id)

    return [
        NodePoolResponse(
            id=pool.id,
            cluster_id=pool.cluster_id,
            name=pool.name,
            instance_type=pool.instance_type,
            node_count=pool.node_count,
            min_nodes=pool.min_nodes,
            max_nodes=pool.max_nodes,
            cpu_per_node=pool.cpu_per_node,
            memory_per_node_gb=pool.memory_per_node_gb,
            gpu_per_node=pool.gpu_per_node,
            gpu_type=pool.gpu_type.value if pool.gpu_type else None,
            auto_scaling=pool.auto_scaling,
            phase=pool.phase,
        )
        for pool in pools
    ]


@router.put("/node-pools/{pool_id}/scale")
async def scale_node_pool(
    pool_id: str,
    node_count: int = Query(..., ge=0, le=100),
    current_user: User = Depends(get_current_user),
):
    """Scale a node pool"""
    pool = cluster_service.scale_node_pool(pool_id, node_count)

    if not pool:
        raise HTTPException(status_code=404, detail="Node pool not found")

    return {
        "message": "Node pool scaled",
        "node_count": pool.node_count,
    }


# Job Scheduling Endpoints
@router.post("/jobs/schedule", response_model=JobResponse)
async def schedule_job(
    request: JobScheduleRequest,
    current_user: User = Depends(get_current_user),
):
    """Schedule a job on the best available cluster"""
    gpu_type = GPUType(request.gpu_type) if request.gpu_type else None

    selector = ClusterSelector(
        min_cpu=request.cpu_request,
        min_memory_gb=request.memory_request_gb,
        min_gpu=request.gpu_request,
        gpu_type=gpu_type,
        preferred_regions=request.preferred_regions,
        required_tags=request.required_tags,
    )

    job = cluster_service.schedule_job(
        job_name=request.name,
        selector=selector,
        cpu_request=request.cpu_request,
        memory_request_gb=request.memory_request_gb,
        gpu_request=request.gpu_request,
        job_type=request.job_type,
    )

    if not job:
        raise HTTPException(
            status_code=503,
            detail="No suitable cluster available for the job requirements"
        )

    return JobResponse(
        id=job.id,
        name=job.name,
        cluster_id=job.cluster_id,
        job_type=job.job_type,
        cpu_request=job.cpu_request,
        memory_request_gb=job.memory_request_gb,
        gpu_request=job.gpu_request,
        phase=job.phase,
        start_time=job.start_time.isoformat() if job.start_time else None,
        completion_time=job.completion_time.isoformat() if job.completion_time else None,
    )


@router.get("/clusters/{cluster_id}/jobs", response_model=List[JobResponse])
async def list_cluster_jobs(
    cluster_id: str,
    current_user: User = Depends(get_current_user),
):
    """List jobs scheduled on a cluster"""
    jobs = cluster_service.get_cluster_jobs(cluster_id)

    return [
        JobResponse(
            id=job.id,
            name=job.name,
            cluster_id=job.cluster_id,
            job_type=job.job_type,
            cpu_request=job.cpu_request,
            memory_request_gb=job.memory_request_gb,
            gpu_request=job.gpu_request,
            phase=job.phase,
            start_time=job.start_time.isoformat() if job.start_time else None,
            completion_time=job.completion_time.isoformat() if job.completion_time else None,
        )
        for job in jobs
    ]


# Metrics Endpoints
@router.get("/clusters/{cluster_id}/metrics")
async def get_cluster_metrics(
    cluster_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get metrics for a cluster"""
    metrics = cluster_service.collect_metrics(cluster_id)

    if not metrics:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return {
        "cluster_id": metrics.cluster_id,
        "timestamp": metrics.timestamp.isoformat(),
        "cpu_usage_percent": metrics.cpu_usage_percent,
        "memory_usage_percent": metrics.memory_usage_percent,
        "gpu_usage_percent": metrics.gpu_usage_percent,
        "pods_running": metrics.pods_running,
        "pods_pending": metrics.pods_pending,
        "nodes_ready": metrics.nodes_ready,
        "storage_used_gb": metrics.storage_used_gb,
        "storage_capacity_gb": metrics.storage_capacity_gb,
    }


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    current_user: User = Depends(get_current_user),
):
    """Get metrics aggregated across all clusters"""
    metrics = cluster_service.get_aggregated_metrics()
    return metrics


# Node Operations
@router.post("/clusters/{cluster_id}/nodes/{node_name}/drain")
async def drain_node(
    cluster_id: str,
    node_name: str,
    current_user: User = Depends(get_current_user),
):
    """Drain a node for maintenance"""
    success = cluster_service.drain_node(cluster_id, node_name)

    if not success:
        raise HTTPException(status_code=404, detail="Cluster or node not found")

    return {"message": f"Node {node_name} drained"}


@router.post("/clusters/{cluster_id}/nodes/{node_name}/cordon")
async def cordon_node(
    cluster_id: str,
    node_name: str,
    current_user: User = Depends(get_current_user),
):
    """Cordon a node (mark unschedulable)"""
    success = cluster_service.cordon_node(cluster_id, node_name)

    if not success:
        raise HTTPException(status_code=404, detail="Cluster or node not found")

    return {"message": f"Node {node_name} cordoned"}


@router.post("/clusters/{cluster_id}/nodes/{node_name}/uncordon")
async def uncordon_node(
    cluster_id: str,
    node_name: str,
    current_user: User = Depends(get_current_user),
):
    """Uncordon a node (mark schedulable)"""
    success = cluster_service.uncordon_node(cluster_id, node_name)

    if not success:
        raise HTTPException(status_code=404, detail="Cluster or node not found")

    return {"message": f"Node {node_name} uncordoned"}


@router.get("/clusters/{cluster_id}/logs")
async def get_cluster_logs(
    cluster_id: str,
    namespace: str = Query("default"),
    pod_name: str = Query(...),
    tail_lines: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """Get logs from a pod"""
    logs = cluster_service.get_cluster_logs(cluster_id, namespace, pod_name, tail_lines)

    return {
        "cluster_id": cluster_id,
        "namespace": namespace,
        "pod_name": pod_name,
        "logs": logs,
    }
