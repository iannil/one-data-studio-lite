"""
Resource Pool Management Service

Provides multi-cluster resource pool management with isolation,
quotas, and allocation policies.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.services.gpu.gpu_scheduler import (
    GPUVendor,
    GPUType,
    GPUSpec,
    GPUAllocation,
    GPUScheduler,
    get_gpu_scheduler,
)

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types"""
    GPU = "gpu"
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    CUSTOM = "custom"


class PoolQuotaType(str, Enum):
    """Quota types"""
    HARD = "hard"  # Cannot exceed
    SOFT = "soft"  # Can exceed with warning
    BURST = "burst"  # Can exceed for limited time


class AllocationPolicy(str, Enum):
    """Resource allocation policies"""
    BEST_FIT = "best_fit"  # Use smallest sufficient resource
    WORST_FIT = "worst_fit"  # Use largest available
    FIRST_FIT = "first_fit"  # Use first available
    PACK = "pack"  # Pack as many tasks per node
    SPREAD = "spread"  # Spread tasks across nodes


@dataclass
class ResourceQuota:
    """Resource quota definition"""
    resource_type: ResourceType
    quota_type: PoolQuotaType
    limit: float
    unit: str
    burst_limit: Optional[float] = None
    burst_duration_seconds: Optional[int] = None


@dataclass
class ResourceRequest:
    """Resource allocation request"""
    resource_type: ResourceType
    amount: float
    unit: str
    gpu_type: Optional[GPUType] = None
    gpu_vendor: Optional[GPUVendor] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    affinity: Optional[List[str]] = None  # Preferred nodes/pools
    anti_affinity: Optional[List[str]] = None  # Avoid nodes/pools


@dataclass
class ResourcePool:
    """Resource pool definition"""
    pool_id: str
    name: str
    description: Optional[str] = None
    node_names: List[str] = field(default_factory=list)
    quotas: Dict[ResourceType, ResourceQuota] = field(default_factory=dict)
    allocation_policy: AllocationPolicy = AllocationPolicy.BEST_FIT
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PoolAllocation:
    """Pool allocation record"""
    allocation_id: str
    pool_id: str
    task_id: str
    user_id: str
    resources: Dict[ResourceType, ResourceRequest]
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: str = "active"


@dataclass
class NodeInfo:
    """Node information"""
    node_name: str
    pool_id: str
    available_resources: Dict[ResourceType, float] = field(default_factory=dict)
    total_resources: Dict[ResourceType, float] = field(default_factory=dict)
    allocated_resources: Dict[ResourceType, float] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    is_ready: bool = True
    is_schedulable: bool = True


class ResourcePoolManager:
    """
    Resource pool manager

    Manages resource pools, quotas, and allocation policies.
    """

    def __init__(self, db: Session):
        self.db = db
        self._pools: Dict[str, ResourcePool] = {}
        self._allocations: Dict[str, PoolAllocation] = {}
        self._nodes: Dict[str, NodeInfo] = {}
        self._scheduler: Optional[GPUScheduler] = None

    @property
    def scheduler(self) -> GPUScheduler:
        """Lazy load scheduler"""
        if self._scheduler is None:
            self._scheduler = get_gpu_scheduler(self.db)
        return self._scheduler

    async def create_pool(
        self,
        name: str,
        node_names: List[str],
        quotas: Dict[ResourceType, ResourceQuota],
        allocation_policy: AllocationPolicy = AllocationPolicy.BEST_FIT,
        labels: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> ResourcePool:
        """
        Create a new resource pool

        Args:
            name: Pool name
            node_names: Nodes in this pool
            quotas: Resource quotas
            allocation_policy: Allocation policy
            labels: Pool labels
            description: Pool description

        Returns:
            Created ResourcePool
        """
        pool_id = f"pool-{name.lower().replace('_', '-')}"

        pool = ResourcePool(
            pool_id=pool_id,
            name=name,
            description=description,
            node_names=node_names,
            quotas=quotas,
            allocation_policy=allocation_policy,
            labels=labels or {},
        )

        self._pools[pool_id] = pool

        # Register nodes
        for node_name in node_names:
            if node_name not in self._nodes:
                self._nodes[node_name] = NodeInfo(
                    node_name=node_name,
                    pool_id=pool_id,
                )

        return pool

    async def delete_pool(self, pool_id: str) -> bool:
        """Delete a resource pool"""
        if pool_id not in self._pools:
            return False

        # Check for active allocations
        active = [a for a in self._allocations.values() if a.pool_id == pool_id]
        if active:
            raise ValueError(f"Cannot delete pool with {len(active)} active allocations")

        # Remove pool
        del self._pools[pool_id]

        # Update nodes
        for node in self._nodes.values():
            if node.pool_id == pool_id:
                node.pool_id = ""

        return True

    async def get_pool(self, pool_id: str) -> Optional[ResourcePool]:
        """Get pool by ID"""
        return self._pools.get(pool_id)

    async def list_pools(
        self,
        enabled_only: bool = True,
    ) -> List[ResourcePool]:
        """List all pools"""
        pools = list(self._pools.values())
        if enabled_only:
            pools = [p for p in pools if p.enabled]
        return pools

    async def update_pool_quotas(
        self,
        pool_id: str,
        quotas: Dict[ResourceType, ResourceQuota],
    ) -> bool:
        """Update pool quotas"""
        pool = await self.get_pool(pool_id)
        if not pool:
            return False

        pool.quotas.update(quotas)
        return True

    async def allocate_from_pool(
        self,
        pool_id: str,
        task_id: str,
        user_id: str,
        requests: List[ResourceRequest],
        ttl_minutes: Optional[int] = None,
    ) -> Optional[PoolAllocation]:
        """
        Allocate resources from a pool

        Args:
            pool_id: Pool to allocate from
            task_id: Task ID
            user_id: User ID
            requests: Resource requests
            ttl_minutes: Time to live

        Returns:
            PoolAllocation or None if allocation failed
        """
        pool = await self.get_pool(pool_id)
        if not pool or not pool.enabled:
            return None

        # Check quotas
        for request in requests:
            quota = pool.quotas.get(request.resource_type)
            if quota and quota.quota_type == PoolQuotaType.HARD:
                current_usage = await self._get_pool_usage(pool_id, request.resource_type)
                if current_usage + request.amount > quota.limit:
                    logger.warning(
                        f"Quota exceeded for {request.resource_type} "
                        f"in pool {pool_id}: {current_usage + request.amount}/{quota.limit}"
                    )
                    return None

        # Allocate each resource
        allocated: Dict[ResourceType, ResourceRequest] = {}

        for request in requests:
            if request.resource_type == ResourceType.GPU:
                # Use GPU scheduler
                gpu_spec = GPUSpec(
                    gpu_type=request.gpu_type or GPUType.T4,
                    vendor=request.gpu_vendor or GPUVendor.NVIDIA,
                    count=int(request.amount),
                )

                gpu_allocation = await self.scheduler.allocate(
                    spec=gpu_spec,
                    allocated_to=task_id,
                    ttl_minutes=ttl_minutes,
                )

                if gpu_allocation:
                    allocated[ResourceType.GPU] = request
                else:
                    # Rollback
                    for alloc_type in allocated:
                        await self._deallocate_resource(alloc_type, task_id)
                    return None
            else:
                # For other resource types, track allocation
                allocated[request.resource_type] = request

        # Create allocation record
        allocation_id = f"pa-{datetime.now().strftime('%Y%m%d%H%M%S')}-{task_id[:8]}"

        expires_at = None
        if ttl_minutes:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        allocation = PoolAllocation(
            allocation_id=allocation_id,
            pool_id=pool_id,
            task_id=task_id,
            user_id=user_id,
            resources=allocated,
            expires_at=expires_at,
        )

        self._allocations[allocation_id] = allocation

        return allocation

    async def deallocate_from_pool(self, allocation_id: str) -> bool:
        """Deallocate resources from a pool"""
        allocation = self._allocations.get(allocation_id)
        if not allocation:
            return False

        # Deallocate each resource
        for resource_type, request in allocation.resources.items():
            await self._deallocate_resource(resource_type, allocation.task_id)

        del self._allocations[allocation_id]
        return True

    async def _deallocate_resource(self, resource_type: ResourceType, task_id: str):
        """Deallocate a specific resource"""
        if resource_type == ResourceType.GPU:
            # Find and deallocate GPU
            allocations = await self.scheduler.list_allocations(allocated_to=task_id)
            for alloc in allocations:
                await self.scheduler.deallocate(alloc.allocation_id)

    async def _get_pool_usage(
        self,
        pool_id: str,
        resource_type: ResourceType,
    ) -> float:
        """Get current usage of a resource type in a pool"""
        usage = 0.0

        for allocation in self._allocations.values():
            if allocation.pool_id != pool_id:
                continue

            request = allocation.resources.get(resource_type)
            if request:
                usage += request.amount

        return usage

    async def get_pool_status(self, pool_id: str) -> Dict[str, Any]:
        """Get pool status including usage"""
        pool = await self.get_pool(pool_id)
        if not pool:
            return {}

        status = {
            "pool_id": pool_id,
            "name": pool.name,
            "enabled": pool.enabled,
            "allocation_policy": pool.allocation_policy.value,
            "nodes": pool.node_names,
            "quotas": {},
            "usage": {},
            "available": {},
        }

        for resource_type, quota in pool.quotas.items():
            usage = await self._get_pool_usage(pool_id, resource_type)
            status["quotas"][resource_type.value] = {
                "limit": quota.limit,
                "unit": quota.unit,
                "type": quota.quota_type.value,
            }
            status["usage"][resource_type.value] = usage
            status["available"][resource_type.value] = quota.limit - usage

        # Active allocations
        active_allocations = [
            a for a in self._allocations.values()
            if a.pool_id == pool_id
        ]
        status["active_allocations"] = len(active_allocations)

        return status

    async def list_allocations(
        self,
        pool_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[PoolAllocation]:
        """List allocations"""
        allocations = list(self._allocations.values())

        if pool_id:
            allocations = [a for a in allocations if a.pool_id == pool_id]
        if user_id:
            allocations = [a for a in allocations if a.user_id == user_id]

        return allocations

    async def cleanup_expired_allocations(self) -> int:
        """Clean up expired allocations"""
        now = datetime.now()
        expired = []

        for allocation_id, allocation in self._allocations.items():
            if allocation.expires_at and allocation.expires_at < now:
                expired.append(allocation_id)

        for allocation_id in expired:
            await self.deallocate_from_pool(allocation_id)

        return len(expired)

    async def add_node_to_pool(
        self,
        pool_id: str,
        node_name: str,
        resources: Dict[ResourceType, Tuple[float, str]],  # (amount, unit)
    ) -> bool:
        """Add a node to a pool"""
        pool = await self.get_pool(pool_id)
        if not pool:
            return False

        if node_name not in self._nodes:
            self._nodes[node_name] = NodeInfo(
                node_name=node_name,
                pool_id=pool_id,
            )

        node = self._nodes[node_name]
        node.pool_id = pool_id

        for resource_type, (amount, unit) in resources.items():
            node.total_resources[resource_type] = amount
            node.available_resources[resource_type] = amount

        pool.node_names.append(node_name)

        return True

    async def remove_node_from_pool(
        self,
        pool_id: str,
        node_name: str,
    ) -> bool:
        """Remove a node from a pool"""
        pool = await self.get_pool(pool_id)
        if not pool:
            return False

        if node_name in pool.node_names:
            pool.node_names.remove(node_name)

        node = self._nodes.get(node_name)
        if node and node.pool_id == pool_id:
            node.pool_id = ""

        return True

    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Get cluster-wide resource summary"""
        summary = {
            "pools": {},
            "total_nodes": len(self._nodes),
            "total_pools": len(self._pools),
            "active_allocations": len(self._allocations),
            "by_resource_type": {},
        }

        # Pool summaries
        for pool_id in self._pools:
            summary["pools"][pool_id] = await self.get_pool_status(pool_id)

        # Resource type totals
        for node in self._nodes.values():
            for resource_type, amount in node.total_resources.items():
                if resource_type not in summary["by_resource_type"]:
                    summary["by_resource_type"][resource_type] = {
                        "total": 0,
                        "allocated": 0,
                        "available": 0,
                    }
                summary["by_resource_type"][resource_type]["total"] += amount
                summary["by_resource_type"][resource_type]["allocated"] += (
                    node.allocated_resources.get(resource_type, 0)
                )
                summary["by_resource_type"][resource_type]["available"] += (
                    node.available_resources.get(resource_type, 0)
                )

        return summary


# Singleton
_manager: Optional[ResourcePoolManager] = None


def get_resource_pool_manager(db: Session) -> ResourcePoolManager:
    """Get or create the resource pool manager instance"""
    return ResourcePoolManager(db)
