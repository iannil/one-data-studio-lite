"""
GPU Scheduling Service Package

Provides GPU resource management including:
- GPU allocation and deallocation
- vGPU (virtual GPU) support
- Multiple GPU type support (NVIDIA, Huawei NPU, Cambricon MLU)
- GPU monitoring and metrics
- Resource pool integration
"""

from app.services.gpu.gpu_scheduler import (
    GPUBackend,
    NVIDIABackend,
    HuaweiNPUBackend,
    CambriconMLUBackend,
    GPUSpec,
    GPUAllocation,
    GPUResource,
    vGPUSpec,
    GPUScheduler,
    get_gpu_scheduler,
)

from app.services.gpu.gpu_monitoring import (
    GPUMetric,
    GPUStatistics,
    GPUMonitor,
    get_gpu_monitor,
)

__all__ = [
    # GPU Scheduler
    "GPUBackend",
    "NVIDIABackend",
    "HuaweiNPUBackend",
    "CambriconMLUBackend",
    "GPUSpec",
    "GPUAllocation",
    "GPUResource",
    "vGPUSpec",
    "GPUScheduler",
    "get_gpu_scheduler",
    # GPU Monitoring
    "GPUMetric",
    "GPUStatistics",
    "GPUMonitor",
    "get_gpu_monitor",
]
