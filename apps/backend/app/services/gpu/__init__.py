"""
GPU Resource Management Service Package

Provides GPU pooling, virtual GPU allocation, and scheduling capabilities.
"""

from .vgpu_allocator import (
    GPUAllocationStrategy,
    GPUAllocationRequest,
    GPUAllocation,
    VirtualGPU,
    PhysicalGPU,
    GPUType,
    VGPUAllocator,
    get_vgpu_allocator,
)

from .gpu_scheduler import (
    SchedulingPolicy,
    TaskPriority,
    GPUTask,
    SchedulingDecision,
    QueuedTask,
    GPUScheduler,
    GPUPoolManager,
    get_gpu_pool_manager,
)

__all__ = [
    # VGPU Allocator
    "GPUAllocationStrategy",
    "GPUAllocationRequest",
    "GPUAllocation",
    "VirtualGPU",
    "PhysicalGPU",
    "GPUType",
    "VGPUAllocator",
    "get_vgpu_allocator",
    # GPU Scheduler
    "SchedulingPolicy",
    "TaskPriority",
    "GPUTask",
    "SchedulingDecision",
    "QueuedTask",
    "GPUScheduler",
    "GPUPoolManager",
    "get_gpu_pool_manager",
]
