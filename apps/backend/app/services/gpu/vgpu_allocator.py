"""
Virtual GPU Allocator

Provides virtual GPU allocation and management capabilities.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import logging

logger = logging.getLogger(__name__)


class GPUAllocationStrategy(str, Enum):
    """GPU allocation strategies"""
    INTERLEAVED = "interleaved"  # Share GPU memory between tasks
    EXCLUSIVE = "exclusive"      # Exclusive GPU access
    MIG = "mig"                  # NVIDIA MIG (Multi-Instance GPU)
    MPS = "mps"                  # CUDA MPS (Multi-Process Service)


class GPUType(str, Enum):
    """GPU hardware types"""
    NVIDIA_A100 = "A100"
    NVIDIA_V100 = "V100"
    NVIDIA_T4 = "T4"
    NVIDIA_A10G = "A10G"
    NVIDIA_A30 = "A30"
    NVIDIA_H100 = "H100"
    GENERIC = "generic"


@dataclass
class VirtualGPU:
    """Virtual GPU instance"""
    vgpu_id: str
    parent_gpu_id: str
    memory_mb: int
    cpu_cores: float
    vgpu_index: int  # Index on parent GPU

    # Allocation info
    allocated_to: Optional[str] = None  # Resource name
    allocated_at: Optional[datetime] = None
    allocation_type: Optional[GPUAllocationStrategy] = None

    # Utilization
    utilization_percent: float = 0.0
    memory_used_mb: int = 0

    @property
    def is_available(self) -> bool:
        return self.allocated_to is None

    @property
    def memory_utilization(self) -> float:
        return (self.memory_used_mb / self.memory_mb * 100) if self.memory_mb > 0 else 0


@dataclass
class PhysicalGPU:
    """Physical GPU device"""
    gpu_id: str
    name: str
    gpu_type: GPUType
    total_memory_mb: int
    cuda_cores: int
    pcie_bandwidth: int  # MB/s
    driver_version: str
    cuda_version: str

    # VGPU configuration
    max_vgpu_instances: int = 8
    vgpu_instances: List[VirtualGPU] = field(default_factory=list)

    # Current state
    temperature_celsius: float = 0.0
    power_draw_watts: float = 0.0
    utilization_percent: float = 0.0
    memory_used_mb: int = 0

    # MIG support
    mig_enabled: bool = False
    mig_instances: int = 0

    @property
    def available_memory_mb(self) -> int:
        return self.total_memory_mb - self.memory_used_mb

    @property
    def available_vgpu_slots(self) -> int:
        return self.max_vgpu_instances - len([v for v in self.vgpu_instances if not v.is_available])

    @property
    def is_healthy(self) -> bool:
        return self.temperature_celsius < 90 and self.utilization_percent < 100

    @property
    def utilization_status(self) -> str:
        if self.utilization_percent < 50:
            return "low"
        elif self.utilization_percent < 80:
            return "medium"
        else:
            return "high"


@dataclass
class GPUAllocationRequest:
    """Request for GPU allocation"""
    request_id: str
    resource_name: str
    gpu_type: Optional[GPUType] = None
    memory_mb: Optional[int] = None
    vgpu_count: int = 1
    strategy: GPUAllocationStrategy = GPUAllocationStrategy.EXCLUSIVE
    required_cuda_cores: Optional[int] = None
    mig_profile: Optional[str] = None  # MIG profile if using MIG
    priority: int = 0  # Higher priority gets allocated first

    def __post_init__(self):
        if self.memory_mb is None and self.gpu_type:
            # Default memory based on GPU type
            self.memory_mb = self._default_memory_for_type(self.gpu_type)

    @staticmethod
    def _default_memory_for_type(gpu_type: GPUType) -> int:
        defaults = {
            GPUType.NVIDIA_A100: 40 * 1024,  # 40GB
            GPUType.NVIDIA_V100: 32 * 1024,  # 32GB
            GPUType.NVIDIA_T4: 16 * 1024,   # 16GB
            GPUType.NVIDIA_A10G: 24 * 1024,  # 24GB
            GPUType.NVIDIA_A30: 24 * 1024,   # 24GB
            GPUType.NVIDIA_H100: 80 * 1024,  # 80GB
        }
        return defaults.get(gpu_type, 16 * 1024)


@dataclass
class GPUAllocation:
    """GPU allocation result"""
    allocation_id: str
    request_id: str
    resource_name: str
    gpu_id: str
    vgpu_ids: List[str]
    allocated_at: datetime
    strategy: GPUAllocationStrategy
    memory_mb: int
    expires_at: Optional[datetime] = None


class VGPUAllocator:
    """
    Virtual GPU Allocator

    Manages virtual GPU instances on physical GPUs.
    """

    def __init__(self):
        self.physical_gpus: Dict[str, PhysicalGPU] = {}
        self.vgpu_instances: Dict[str, VirtualGPU] = {}
        self.allocations: Dict[str, GPUAllocation] = {}
        self.allocation_id_counter = 0

    def register_physical_gpu(
        self,
        gpu_id: str,
        name: str,
        gpu_type: GPUType,
        total_memory_mb: int,
        cuda_cores: int,
        driver_version: str = "unknown",
        cuda_version: str = "unknown",
        max_vgpu_instances: int = 8,
    ) -> PhysicalGPU:
        """Register a physical GPU"""
        gpu = PhysicalGPU(
            gpu_id=gpu_id,
            name=name,
            gpu_type=gpu_type,
            total_memory_mb=total_memory_mb,
            cuda_cores=cuda_cores,
            pcie_bandwidth=0,  # Will be detected
            driver_version=driver_version,
            cuda_version=cuda_version,
            max_vgpu_instances=max_vgpu_instances,
        )
        self.physical_gpus[gpu_id] = gpu
        logger.info(f"Registered physical GPU: {gpu_id} ({name})")
        return gpu

    def unregister_physical_gpu(self, gpu_id: str) -> None:
        """Unregister a physical GPU"""
        if gpu_id in self.physical_gpus:
            # Check if any VGPU instances are allocated
            gpu = self.physical_gpus[gpu_id]
            active_allocations = [v for v in gpu.vgpu_instances if not v.is_available]
            if active_allocations:
                raise ValueError(f"Cannot unregister GPU {gpu_id}: {len(active_allocations)} active allocations")

            # Remove VGPU instances
            for vgpu in gpu.vgpu_instances:
                self.vgpu_instances.pop(vgpu.vgpu_id, None)

            del self.physical_gpus[gpu_id]
            logger.info(f"Unregistered physical GPU: {gpu_id}")

    def create_vgpu_instances(
        self,
        gpu_id: str,
        count: int,
        memory_per_vgpu: int,
        cpu_cores_per_vgpu: float = 1.0,
    ) -> List[VirtualGPU]:
        """Create virtual GPU instances on a physical GPU"""
        if gpu_id not in self.physical_gpus:
            raise ValueError(f"GPU {gpu_id} not found")

        gpu = self.physical_gpus[gpu_id]

        # Check if we have space
        available_memory = gpu.available_memory_mb
        total_memory_needed = count * memory_per_vgpu

        if total_memory_needed > available_memory:
            raise ValueError(
                f"Insufficient memory: need {total_memory_needed}MB, have {available_memory}MB"
            )

        if len(gpu.vgpu_instances) + count > gpu.max_vgpu_instances:
            raise ValueError(
                f"Exceeds max VGPU instances: {len(gpu.vgpu_instances) + count} > {gpu.max_vgpu_instances}"
            )

        created_vgpus = []
        for i in range(count):
            vgpu_id = f"{gpu_id}-vgpu-{len(gpu.vgpu_instances) + i}"
            vgpu = VirtualGPU(
                vgpu_id=vgpu_id,
                parent_gpu_id=gpu_id,
                memory_mb=memory_per_vgpu,
                cpu_cores=cpu_cores_per_vgpu,
                vgpu_index=len(gpu.vgpu_instances) + i,
            )
            gpu.vgpu_instances.append(vgpu)
            self.vgpu_instances[vgpu_id] = vgpu
            created_vgpus.append(vgpu)

        logger.info(f"Created {count} VGPU instances on {gpu_id}")
        return created_vgpus

    def allocate(self, request: GPUAllocationRequest) -> GPUAllocation:
        """Allocate GPUs for a request"""
        suitable_gpus = self._find_suitable_gpus(request)

        if not suitable_gpus:
            raise ValueError(
                f"No suitable GPUs available for request {request.request_id}. "
                f"Required: {request.memory_mb}MB, GPU type: {request.gpu_type}"
            )

        # Allocate based on strategy
        if request.strategy == GPUAllocationStrategy.EXCLUSIVE:
            return self._allocate_exclusive(request, suitable_gpus)
        elif request.strategy == GPUAllocationStrategy.INTERLEAVED:
            return self._allocate_interleaved(request, suitable_gpus)
        elif request.strategy == GPUAllocationStrategy.MIG:
            return self._allocate_mig(request, suitable_gpus)
        else:
            return self._allocate_exclusive(request, suitable_gpus)

    def _find_suitable_gpus(self, request: GPUAllocationRequest) -> List[PhysicalGPU]:
        """Find GPUs that can satisfy the request"""
        suitable = []

        for gpu in self.physical_gpus.values():
            if not gpu.is_healthy:
                continue

            # Filter by GPU type if specified
            if request.gpu_type and gpu.gpu_type != request.gpu_type:
                continue

            # Check memory availability
            if request.strategy == GPUAllocationStrategy.EXCLUSIVE:
                # For exclusive, need full GPU available
                if len([v for v in gpu.vgpu_instances if not v.is_available]) > 0:
                    continue
            else:
                # For shared/interleaved, check memory
                if request.memory_mb and gpu.available_memory_mb < request.memory_mb:
                    continue

            # Check VGPU slot availability
            if request.vgpu_count > gpu.available_vgpu_slots:
                continue

            suitable.append(gpu)

        # Sort by utilization (prefer less utilized GPUs)
        suitable.sort(key=lambda g: g.utilization_percent)
        return suitable

    def _allocate_exclusive(
        self,
        request: GPUAllocationRequest,
        gpus: List[PhysicalGPU],
    ) -> GPUAllocation:
        """Allocate exclusive GPU access"""
        needed_gpus = (request.vgpu_count + 7) // 8  # One physical GPU per 8 VGPUs
        if len(gpus) < needed_gpus:
            needed_gpus = len(gpus)

        selected_gpus = gpus[:needed_gpus]
        vgpu_ids = []

        for gpu in selected_gpus:
            # Create VGPU instance for this allocation
            memory_per_vgpu = request.memory_mb or gpu.total_memory_mb

            # Find or create VGPU instance
            available_vgpu = next((v for v in gpu.vgpu_instances if v.is_available), None)

            if available_vgpu:
                available_vgpu.allocated_to = request.resource_name
                available_vgpu.allocated_at = datetime.now()
                available_vgpu.allocation_type = request.strategy
                vgpu_ids.append(available_vgpu.vgpu_id)
            else:
                # Create new VGPU
                new_vgpus = self.create_vgpu_instances(
                    gpu_id=gpu.gpu_id,
                    count=1,
                    memory_per_vgpu=memory_per_vgpu,
                )
                new_vgpus[0].allocated_to = request.resource_name
                new_vgpus[0].allocated_at = datetime.now()
                new_vgpus[0].allocation_type = request.strategy
                vgpu_ids.append(new_vgpus[0].vgpu_id)

        allocation = GPUAllocation(
            allocation_id=f"alloc-{self.allocation_id_counter}",
            request_id=request.request_id,
            resource_name=request.resource_name,
            gpu_id=selected_gpus[0].gpu_id,
            vgpu_ids=vgpu_ids,
            allocated_at=datetime.now(),
            strategy=request.strategy,
            memory_mb=request.memory_mb or (selected_gpus[0].total_memory_mb if selected_gpus else 0),
        )
        self.allocation_id_counter += 1
        self.allocations[allocation.allocation_id] = allocation

        logger.info(f"Allocated {len(vgpu_ids)} VGPU(s) for {request.resource_name}")
        return allocation

    def _allocate_interleaved(
        self,
        request: GPUAllocationRequest,
        gpus: List[PhysicalGPU],
    ) -> GPUAllocation:
        """Allocate interleaved (shared) GPU access"""
        vgpu_ids = []
        allocated_memory = 0

        for gpu in gpus:
            if len(vgpu_ids) >= request.vgpu_count:
                break

            # Find available VGPU slots
            available_vgpus = [v for v in gpu.vgpu_instances if v.is_available]

            for vgpu in available_vgpus:
                if len(vgpu_ids) >= request.vgpu_count:
                    break

                vgpu.allocated_to = request.resource_name
                vgpu.allocated_at = datetime.now()
                vgpu.allocation_type = request.strategy
                vgpu_ids.append(vgpu.vgpu_id)
                allocated_memory += vgpu.memory_mb

            # Create new VGPU if needed
            while len(vgpu_ids) < request.vgpu_count and len(gpu.vgpu_instances) < gpu.max_vgpu_instances:
                memory_per_vgpu = min(
                    request.memory_mb or (gpu.total_memory_mb // gpu.max_vgpu_instances),
                    gpu.available_memory_mb,
                )
                if memory_per_vgpu <= 0:
                    break

                new_vgpus = self.create_vgpu_instances(
                    gpu_id=gpu.gpu_id,
                    count=1,
                    memory_per_vgpu=memory_per_vgpu,
                )
                new_vgpus[0].allocated_to = request.resource_name
                new_vgpus[0].allocated_at = datetime.now()
                new_vgpus[0].allocation_type = request.strategy
                vgpu_ids.append(new_vgpus[0].vgpu_id)
                allocated_memory += memory_per_vgpu

        if len(vgpu_ids) < request.vgpu_count:
            # Rollback
            self.deallocate_by_resource(request.resource_name)
            raise ValueError(f"Could not allocate {request.vgpu_count} VGPU(s)")

        allocation = GPUAllocation(
            allocation_id=f"alloc-{self.allocation_id_counter}",
            request_id=request.request_id,
            resource_name=request.resource_name,
            gpu_id=gpus[0].gpu_id if gpus else "",
            vgpu_ids=vgpu_ids,
            allocated_at=datetime.now(),
            strategy=request.strategy,
            memory_mb=allocated_memory,
        )
        self.allocation_id_counter += 1
        self.allocations[allocation.allocation_id] = allocation

        logger.info(f"Allocated {len(vgpu_ids)} shared VGPU(s) for {request.resource_name}")
        return allocation

    def _allocate_mig(
        self,
        request: GPUAllocationRequest,
        gpus: List[PhysicalGPU],
    ) -> GPUAllocation:
        """Allocate using MIG (Multi-Instance GPU)"""
        # Find MIG-enabled GPU
        mig_gpu = next((g for g in gpus if g.mig_enabled), None)

        if not mig_gpu:
            # Try to enable MIG on first A100/H100
            a100_gpu = next(
                (g for g in gpus if g.gpu_type in [GPUType.NVIDIA_A100, GPUType.NVIDIA_H100]),
                None,
            )
            if a100_gpu:
                mig_gpu = a100_gpu
                mig_gpu.mig_enabled = True
                # MIG typically allows up to 7 instances
                mig_gpu.max_vgpu_instances = 7
            else:
                raise ValueError("No MIG-capable GPU available (A100/H100 required)")

        # Determine MIG profile based on request
        if request.mig_profile:
            # Parse MIG profile (e.g., "1g.5gb" = 1 GPU, 5GB memory)
            profile_parts = request.mig_profile.split(".")
            if len(profile_parts) == 2:
                gpus_count = int(profile_parts[0][:-1])  # Remove 'g'
                memory_gb = int(profile_parts[1][:-2]) if "gb" in profile_parts[1] else 0
                request.memory_mb = memory_gb * 1024

        # Create VGPU instances for MIG
        vgpu_ids = []
        memory_per_vgpu = request.memory_mb or (mig_gpu.total_memory_mb // mig_gpu.max_vgpu_instances)

        for i in range(request.vgpu_count):
            if i >= mig_gpu.available_vgpu_slots:
                break

            new_vgpus = self.create_vgpu_instances(
                gpu_id=mig_gpu.gpu_id,
                count=1,
                memory_per_vgpu=memory_per_vgpu,
            )
            new_vgpus[0].allocated_to = request.resource_name
            new_vgpus[0].allocated_at = datetime.now()
            new_vgpus[0].allocation_type = request.strategy
            vgpu_ids.append(new_vgpus[0].vgpu_id)

        allocation = GPUAllocation(
            allocation_id=f"alloc-{self.allocation_id_counter}",
            request_id=request.request_id,
            resource_name=request.resource_name,
            gpu_id=mig_gpu.gpu_id,
            vgpu_ids=vgpu_ids,
            allocated_at=datetime.now(),
            strategy=request.strategy,
            memory_mb=memory_per_vgpu * len(vgpu_ids),
        )
        self.allocation_id_counter += 1
        self.allocations[allocation.allocation_id] = allocation

        logger.info(f"Allocated {len(vgpu_ids)} MIG VGPU(s) for {request.resource_name}")
        return allocation

    def deallocate(self, allocation_id: str) -> bool:
        """Deallocate a GPU allocation"""
        if allocation_id not in self.allocations:
            return False

        allocation = self.allocations[allocation_id]

        # Free VGPU instances
        for vgpu_id in allocation.vgpu_ids:
            if vgpu_id in self.vgpu_instances:
                vgpu = self.vgpu_instances[vgpu_id]
                vgpu.allocated_to = None
                vgpu.allocated_at = None
                vgpu.allocation_type = None
                vgpu.memory_used_mb = 0

        del self.allocations[allocation_id]
        logger.info(f"Deallocated GPU allocation: {allocation_id}")
        return True

    def deallocate_by_resource(self, resource_name: str) -> int:
        """Deallocate all GPUs for a resource"""
        count = 0
        allocation_ids_to_remove = []

        for allocation_id, allocation in self.allocations.items():
            if allocation.resource_name == resource_name:
                for vgpu_id in allocation.vgpu_ids:
                    if vgpu_id in self.vgpu_instances:
                        vgpu = self.vgpu_instances[vgpu_id]
                        vgpu.allocated_to = None
                        vgpu.allocated_at = None
                        vgpu.allocation_type = None
                        vgpu.memory_used_mb = 0
                allocation_ids_to_remove.append(allocation_id)
                count += 1

        for allocation_id in allocation_ids_to_remove:
            del self.allocations[allocation_id]

        if count > 0:
            logger.info(f"Deallocated {count} allocation(s) for resource: {resource_name}")
        return count

    def get_allocation(self, allocation_id: str) -> Optional[GPUAllocation]:
        """Get allocation by ID"""
        return self.allocations.get(allocation_id)

    def list_allocations(self, resource_name: Optional[str] = None) -> List[GPUAllocation]:
        """List allocations, optionally filtered by resource"""
        allocations = list(self.allocations.values())
        if resource_name:
            allocations = [a for a in allocations if a.resource_name == resource_name]
        return allocations

    def get_gpu_status(self, gpu_id: str) -> Optional[PhysicalGPU]:
        """Get status of a physical GPU"""
        return self.physical_gpus.get(gpu_id)

    def list_gpus(self, gpu_type: Optional[GPUType] = None) -> List[PhysicalGPU]:
        """List physical GPUs, optionally filtered by type"""
        gpus = list(self.physical_gpus.values())
        if gpu_type:
            gpus = [g for g in gpus if g.gpu_type == gpu_type]
        return gpus

    def get_cluster_gpu_stats(self) -> Dict[str, Any]:
        """Get cluster-wide GPU statistics"""
        total_gpus = len(self.physical_gpus)
        total_memory = sum(g.total_memory_mb for g in self.physical_gpus.values())
        used_memory = sum(g.memory_used_mb for g in self.physical_gpus.values())

        healthy_gpus = sum(1 for g in self.physical_gpus.values() if g.is_healthy)
        total_vgpu_instances = sum(len(g.vgpu_instances) for g in self.physical_gpus.values())
        active_allocations = len(self.allocations)

        gpu_type_counts: Dict[GPUType, int] = {}
        for gpu in self.physical_gpus.values():
            gpu_type_counts[gpu.gpu_type] = gpu_type_counts.get(gpu.gpu_type, 0) + 1

        return {
            "total_gpus": total_gpus,
            "healthy_gpus": healthy_gpus,
            "unhealthy_gpus": total_gpus - healthy_gpus,
            "total_memory_mb": total_memory,
            "used_memory_mb": used_memory,
            "available_memory_mb": total_memory - used_memory,
            "memory_utilization_percent": (used_memory / total_memory * 100) if total_memory > 0 else 0,
            "total_vgpu_instances": total_vgpu_instances,
            "active_allocations": active_allocations,
            "gpu_type_counts": {t.value: c for t, c in gpu_type_counts.items()},
        }

    def update_gpu_metrics(
        self,
        gpu_id: str,
        utilization_percent: float,
        memory_used_mb: int,
        temperature_celsius: float,
        power_draw_watts: float,
    ) -> None:
        """Update GPU metrics (called by monitoring)"""
        if gpu_id in self.physical_gpus:
            gpu = self.physical_gpus[gpu_id]
            gpu.utilization_percent = utilization_percent
            gpu.memory_used_mb = memory_used_mb
            gpu.temperature_celsius = temperature_celsius
            gpu.power_draw_watts = power_draw_watts


# Global allocator instance
_vgpu_allocator: Optional[VGPUAllocator] = None


def get_vgpu_allocator() -> VGPUAllocator:
    """Get the global VGPU allocator instance"""
    global _vgpu_allocator
    if _vgpu_allocator is None:
        _vgpu_allocator = VGPUAllocator()
        # Initialize with mock GPUs for development
        _initialize_mock_gpus(_vgpu_allocator)
    return _vgpu_allocator


def _initialize_mock_gpus(allocator: VGPUAllocator) -> None:
    """Initialize mock GPUs for development/testing"""
    # A100 40GB
    allocator.register_physical_gpu(
        gpu_id="gpu-0",
        name="NVIDIA A100-SXM4-40GB",
        gpu_type=GPUType.NVIDIA_A100,
        total_memory_mb=40 * 1024,
        cuda_cores=6912,
        driver_version="525.60.13",
        cuda_version="12.0",
        max_vgpu_instances=7,
    )

    # A100 40GB
    allocator.register_physical_gpu(
        gpu_id="gpu-1",
        name="NVIDIA A100-SXM4-40GB",
        gpu_type=GPUType.NVIDIA_A100,
        total_memory_mb=40 * 1024,
        cuda_cores=6912,
        driver_version="525.60.13",
        cuda_version="12.0",
        max_vgpu_instances=7,
    )

    # V100 32GB
    allocator.register_physical_gpu(
        gpu_id="gpu-2",
        name="NVIDIA Tesla V100-SXM2-32GB",
        gpu_type=GPUType.NVIDIA_V100,
        total_memory_mb=32 * 1024,
        cuda_cores=5120,
        driver_version="525.60.13",
        cuda_version="12.0",
        max_vgpu_instances=8,
    )

    # T4 16GB
    allocator.register_physical_gpu(
        gpu_id="gpu-3",
        name="NVIDIA Tesla T4",
        gpu_type=GPUType.NVIDIA_T4,
        total_memory_mb=16 * 1024,
        cuda_cores=2560,
        driver_version="525.60.13",
        cuda_version="12.0",
        max_vgpu_instances=8,
    )

    # Create some initial VGPU instances
    allocator.create_vgpu_instances("gpu-0", count=4, memory_per_vgpu=10 * 1024)
    allocator.create_vgpu_instances("gpu-1", count=4, memory_per_vgpu=10 * 1024)
    allocator.create_vgpu_instances("gpu-2", count=4, memory_per_vgpu=8 * 1024)
    allocator.create_vgpu_instances("gpu-3", count=2, memory_per_vgpu=8 * 1024)
