"""
Multi-Cluster Management Service

Manages multiple Kubernetes clusters for workload distribution.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


class ClusterStatus(str, Enum):
    """Cluster status"""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNREACHABLE = "unreachable"
    DELETING = "deleting"


class ClusterType(str, Enum):
    """Cluster types"""

    MANAGED = "managed"  # Fully managed by platform
    ATTACHED = "attached"  # Customer-provided, attached to platform
    HYBRID = "hybrid"  # Mix of managed and attached nodes


class NodeRole(str, Enum):
    """Node roles"""

    MASTER = "master"
    WORKER = "worker"
    INFERENCE = "inference"  # Dedicated for inference workloads
    TRAINING = "training"  # Dedicated for training workloads


class GPUType(str, Enum):
    """GPU types available in clusters"""

    NVIDIA_T4 = "nvidia-tesla-t4"
    NVIDIA_V100 = "nvidia-tesla-v100"
    NVIDIA_A100 = "nvidia-tesla-a100"
    NVIDIA_H100 = "nvidia-tesla-h100"
    NVIDIA_A10G = "nvidia-tesla-a10g"
    NVIDIA_L40 = "nvidia-tesla-l40"


@dataclass
class NodeInfo:
    """Information about a cluster node"""

    name: str
    role: NodeRole
    cpu_capacity: int  # CPU cores
    memory_capacity_gb: int
    gpu_capacity: int = 0
    gpu_type: Optional[GPUType] = None
    cpu_allocated: int = 0
    memory_allocated_gb: int = 0
    gpu_allocated: int = 0
    pod_capacity: int = 110  # Default max pods
    pods_running: int = 0
    condition: str = "Ready"  # Ready, NotReady, etc.
    version: str = "v1.28.0"


@dataclass
class ClusterMetrics:
    """Real-time cluster metrics"""

    cluster_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Resource utilization
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    gpu_usage_percent: float = 0.0

    # Pod counts
    pods_running: int = 0
    pods_pending: int = 0
    pods_failed: int = 0

    # Node counts
    nodes_ready: int = 0
    nodes_not_ready: int = 0

    # Storage
    storage_used_gb: float = 0.0
    storage_capacity_gb: float = 0.0


@dataclass
class Cluster:
    """A Kubernetes cluster managed by the platform"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Type and status
    cluster_type: ClusterType = ClusterType.MANAGED
    status: ClusterStatus = ClusterStatus.PROVISIONING

    # Connection info
    api_endpoint: str = ""
    region: str = ""
    zone: str = ""

    # Version
    kubernetes_version: str = "v1.28.0"

    # Resource capacity
    node_count: int = 0
    cpu_capacity: int = 0
    memory_capacity_gb: int = 0
    gpu_capacity: int = 0
    storage_capacity_gb: int = 0

    # Networking
    pod_cidr: str = "10.244.0.0/16"
    service_cidr: str = "10.96.0.0/12"
    network_plugin: str = "calico"

    # Authentication
    kubeconfig: Optional[str] = None  # Encrypted
    service_account_token: Optional[str] = None

    # Labels and annotations
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Tags for scheduling
    tags: List[str] = field(default_factory=list)  # e.g., ["gpu", "high-memory", "inference"]

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None

    def calculate_utilization(self) -> Tuple[float, float, float]:
        """Calculate current resource utilization"""
        # Would query metrics from cluster
        cpu_usage = 45.0  # Example
        memory_usage = 60.0
        gpu_usage = 30.0 if self.gpu_capacity > 0 else 0.0
        return cpu_usage, memory_usage, gpu_usage

    def is_healthy(self) -> bool:
        """Check if cluster is healthy"""
        if self.status not in [ClusterStatus.ACTIVE, ClusterStatus.DEGRADED]:
            return False

        # Check last health check
        if self.last_health_check:
            if datetime.utcnow() - self.last_health_check > timedelta(minutes=5):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        cpu, memory, gpu = self.calculate_utilization()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.cluster_type.value,
            "status": self.status.value,
            "region": self.region,
            "zone": self.zone,
            "kubernetes_version": self.kubernetes_version,
            "node_count": self.node_count,
            "cpu_capacity": self.cpu_capacity,
            "memory_capacity_gb": self.memory_capacity_gb,
            "gpu_capacity": self.gpu_capacity,
            "storage_capacity_gb": self.storage_capacity_gb,
            "utilization": {
                "cpu_percent": cpu,
                "memory_percent": memory,
                "gpu_percent": gpu,
            },
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ClusterNodePool:
    """Node pool for group of similar nodes"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cluster_id: str = ""
    name: str = ""

    # Node specifications
    instance_type: str = ""  # e.g., c5.2xlarge, n1-standard-4
    node_count: int = 0
    min_nodes: int = 0
    max_nodes: int = 10

    # Resources per node
    cpu_per_node: int = 4
    memory_per_node_gb: int = 16
    gpu_per_node: int = 0
    gpu_type: Optional[GPUType] = None

    # Auto-scaling
    auto_scaling: bool = False

    # Labels
    labels: Dict[str, str] = field(default_factory=dict)
    taints: List[Dict[str, str]] = field(default_factory=list)

    # Status
    phase: str = "Provisioning"  # Provisioning, Running, Scaling, Deleting


@dataclass
class ScheduledJob:
    """A job scheduled on a cluster"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    cluster_id: str = ""
    namespace: str = "default"

    # Job type
    job_type: str = "training"  # training, inference, etl, etc.

    # Resource requirements
    cpu_request: int = 1
    memory_request_gb: int = 4
    gpu_request: int = 0

    # Status
    phase: str = "Pending"  # Pending, Running, Succeeded, Failed
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None


class ClusterSelector:
    """Criteria for selecting a cluster"""

    def __init__(
        self,
        min_cpu: int = 0,
        min_memory_gb: int = 0,
        min_gpu: int = 0,
        gpu_type: Optional[GPUType] = None,
        preferred_regions: Optional[List[str]] = None,
        required_tags: Optional[List[str]] = None,
        forbidden_tags: Optional[List[str]] = None,
        max_cpu_utilization: float = 80.0,
    ):
        self.min_cpu = min_cpu
        self.min_memory_gb = min_memory_gb
        self.min_gpu = min_gpu
        self.gpu_type = gpu_type
        self.preferred_regions = preferred_regions or []
        self.required_tags = required_tags or []
        self.forbidden_tags = forbidden_tags or []
        self.max_cpu_utilization = max_cpu_utilization

    def matches(self, cluster: Cluster) -> bool:
        """Check if cluster matches selector criteria"""
        # Check resource capacity
        if cluster.cpu_capacity < self.min_cpu:
            return False
        if cluster.memory_capacity_gb < self.min_memory_gb:
            return False
        if cluster.gpu_capacity < self.min_gpu:
            return False

        # Check GPU type if required
        if self.min_gpu > 0 and self.gpu_type:
            # Would need to check actual GPU types in cluster
            pass

        # Check required tags
        for tag in self.required_tags:
            if tag not in cluster.tags:
                return False

        # Check forbidden tags
        for tag in self.forbidden_tags:
            if tag in cluster.tags:
                return False

        # Check utilization
        cpu_usage, _, _ = cluster.calculate_utilization()
        if cpu_usage > self.max_cpu_utilization:
            return False

        return True


class ClusterService:
    """
    Service for managing multiple clusters.
    """

    def __init__(self):
        # In production, store in database
        self.clusters: Dict[str, Cluster] = {}
        self.node_pools: Dict[str, List[ClusterNodePool]] = {}
        self.metrics: Dict[str, ClusterMetrics] = {}
        self.scheduled_jobs: Dict[str, List[ScheduledJob]] = {}

    def register_cluster(
        self,
        name: str,
        cluster_type: ClusterType,
        api_endpoint: str,
        region: str,
        kubeconfig: Optional[str] = None,
        **kwargs,
    ) -> Cluster:
        """
        Register a new cluster.

        Args:
            name: Cluster name
            cluster_type: Type of cluster
            api_endpoint: Kubernetes API endpoint
            region: Cluster region
            kubeconfig: Kubeconfig for authentication
            **kwargs: Additional cluster properties

        Returns:
            Created cluster
        """
        cluster = Cluster(
            name=name,
            cluster_type=cluster_type,
            api_endpoint=api_endpoint,
            region=region,
            kubeconfig=kubeconfig,
            **kwargs,
        )

        self.clusters[cluster.id] = cluster
        self.node_pools[cluster.id] = []

        # Start health check
        cluster.last_health_check = datetime.utcnow()

        return cluster

    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        """Get cluster by ID"""
        return self.clusters.get(cluster_id)

    def list_clusters(
        self,
        status: Optional[ClusterStatus] = None,
        region: Optional[str] = None,
    ) -> List[Cluster]:
        """List clusters with optional filters"""
        clusters = list(self.clusters.values())

        if status:
            clusters = [c for c in clusters if c.status == status]

        if region:
            clusters = [c for c in clusters if c.region == region]

        return clusters

    def update_cluster(
        self, cluster_id: str, **kwargs
    ) -> Optional[Cluster]:
        """Update cluster properties"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return None

        for key, value in kwargs.items():
            if hasattr(cluster, key):
                setattr(cluster, key, value)

        cluster.updated_at = datetime.utcnow()
        return cluster

    def delete_cluster(self, cluster_id: str) -> bool:
        """Delete a cluster"""
        if cluster_id not in self.clusters:
            return False

        cluster = self.clusters[cluster_id]
        cluster.status = ClusterStatus.DELETING

        # In production, would deprovision resources
        del self.clusters[cluster_id]
        if cluster_id in self.node_pools:
            del self.node_pools[cluster_id]

        return True

    # Node Pool Management
    def create_node_pool(
        self,
        cluster_id: str,
        name: str,
        instance_type: str,
        node_count: int,
        cpu_per_node: int,
        memory_per_node_gb: int,
        gpu_per_node: int = 0,
        gpu_type: Optional[GPUType] = None,
        **kwargs,
    ) -> Optional[ClusterNodePool]:
        """Create a node pool in a cluster"""
        if cluster_id not in self.clusters:
            return None

        pool = ClusterNodePool(
            cluster_id=cluster_id,
            name=name,
            instance_type=instance_type,
            node_count=node_count,
            cpu_per_node=cpu_per_node,
            memory_per_node_gb=memory_per_node_gb,
            gpu_per_node=gpu_per_node,
            gpu_type=gpu_type,
            **kwargs,
        )

        self.node_pools[cluster_id].append(pool)

        # Update cluster capacity
        cluster = self.clusters[cluster_id]
        cluster.node_count += node_count
        cluster.cpu_capacity += cpu_per_node * node_count
        cluster.memory_capacity_gb += memory_per_node_gb * node_count
        cluster.gpu_capacity += gpu_per_node * node_count

        return pool

    def get_node_pools(self, cluster_id: str) -> List[ClusterNodePool]:
        """Get node pools for a cluster"""
        return self.node_pools.get(cluster_id, [])

    def scale_node_pool(
        self, pool_id: str, new_count: int
    ) -> Optional[ClusterNodePool]:
        """Scale a node pool"""
        for cluster_id, pools in self.node_pools.items():
            for pool in pools:
                if pool.id == pool_id:
                    old_count = pool.node_count
                    pool.node_count = new_count

                    # Update cluster capacity
                    cluster = self.clusters.get(cluster_id)
                    if cluster:
                        delta = new_count - old_count
                        cluster.node_count += delta
                        cluster.cpu_capacity += pool.cpu_per_node * delta
                        cluster.memory_capacity_gb += pool.memory_per_node_gb * delta
                        cluster.gpu_capacity += pool.gpu_per_node * delta

                    return pool
        return None

    # Scheduling
    def select_cluster(
        self, selector: ClusterSelector
    ) -> Optional[Cluster]:
        """
        Select the best cluster matching the selector.

        Args:
            selector: Cluster selection criteria

        Returns:
            Best matching cluster or None
        """
        matching_clusters = [
            c for c in self.clusters.values()
            if c.status == ClusterStatus.ACTIVE and selector.matches(c)
        ]

        if not matching_clusters:
            return None

        # Sort by utilization (prefer less utilized)
        matching_clusters.sort(
            key=lambda c: c.calculate_utilization()[0]
        )

        # Prefer preferred regions
        if selector.preferred_regions:
            for cluster in matching_clusters:
                if cluster.region in selector.preferred_regions:
                    return cluster

        return matching_clusters[0]

    def schedule_job(
        self,
        job_name: str,
        selector: ClusterSelector,
        cpu_request: int,
        memory_request_gb: int,
        gpu_request: int = 0,
        job_type: str = "training",
    ) -> Optional[ScheduledJob]:
        """
        Schedule a job on the best available cluster.

        Args:
            job_name: Name of the job
            selector: Cluster selection criteria
            cpu_request: CPU cores requested
            memory_request_gb: Memory requested
            gpu_request: GPUs requested
            job_type: Type of job

        Returns:
            Scheduled job or None if no suitable cluster
        """
        cluster = self.select_cluster(selector)

        if not cluster:
            return None

        job = ScheduledJob(
            name=job_name,
            cluster_id=cluster.id,
            cpu_request=cpu_request,
            memory_request_gb=memory_request_gb,
            gpu_request=gpu_request,
            job_type=job_type,
            phase="Pending",
        )

        if cluster.id not in self.scheduled_jobs:
            self.scheduled_jobs[cluster.id] = []

        self.scheduled_jobs[cluster.id].append(job)

        return job

    def get_cluster_jobs(self, cluster_id: str) -> List[ScheduledJob]:
        """Get jobs scheduled on a cluster"""
        return self.scheduled_jobs.get(cluster_id, [])

    # Health and Metrics
    def update_cluster_health(self, cluster_id: str, healthy: bool) -> bool:
        """Update cluster health status"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return False

        cluster.last_health_check = datetime.utcnow()

        if healthy:
            if cluster.status == ClusterStatus.UNREACHABLE:
                cluster.status = ClusterStatus.ACTIVE
        else:
            cluster.status = ClusterStatus.UNREACHABLE

        return True

    def collect_metrics(self, cluster_id: str) -> Optional[ClusterMetrics]:
        """Collect metrics from a cluster"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return None

        # In production, would query metrics server / Prometheus
        cpu, memory, gpu = cluster.calculate_utilization()

        metrics = ClusterMetrics(
            cluster_id=cluster_id,
            cpu_usage_percent=cpu,
            memory_usage_percent=memory,
            gpu_usage_percent=gpu,
            nodes_ready=cluster.node_count,
            storage_capacity_gb=cluster.storage_capacity_gb,
        )

        self.metrics[cluster_id] = metrics
        return metrics

    def get_cluster_metrics(self, cluster_id: str) -> Optional[ClusterMetrics]:
        """Get latest metrics for a cluster"""
        return self.metrics.get(cluster_id)

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get metrics aggregated across all clusters"""
        total_cpu = 0
        total_memory = 0
        total_gpu = 0
        total_nodes = 0
        active_clusters = 0

        for cluster in self.clusters.values():
            if cluster.status == ClusterStatus.ACTIVE:
                active_clusters += 1
                total_cpu += cluster.cpu_capacity
                total_memory += cluster.memory_capacity_gb
                total_gpu += cluster.gpu_capacity
                total_nodes += cluster.node_count

        return {
            "total_clusters": len(self.clusters),
            "active_clusters": active_clusters,
            "total_nodes": total_nodes,
            "total_cpu_capacity": total_cpu,
            "total_memory_capacity_gb": total_memory,
            "total_gpu_capacity": total_gpu,
        }

    # Cluster Operations
    def drain_node(self, cluster_id: str, node_name: str) -> bool:
        """Drain a node for maintenance"""
        # In production, would execute kubectl drain
        return True

    def cordon_node(self, cluster_id: str, node_name: str) -> bool:
        """Cordon a node (mark unschedulable)"""
        # In production, would execute kubectl cordon
        return True

    def uncordon_node(self, cluster_id: str, node_name: str) -> bool:
        """Uncordon a node (mark schedulable)"""
        # In production, would execute kubectl uncordon
        return True

    def get_cluster_logs(
        self,
        cluster_id: str,
        namespace: str,
        pod_name: str,
        tail_lines: int = 100,
    ) -> str:
        """Get logs from a pod"""
        # In production, would execute kubectl logs
        return "Simulated logs output..."


# Global service instance
cluster_service = ClusterService()
