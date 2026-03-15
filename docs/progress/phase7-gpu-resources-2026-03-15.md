# Phase 7: GPU与资源调度 - Progress Report

**Date:** 2026-03-15
**Status:** Completed

## Overview

Phase 7 focuses on GPU resource scheduling, resource pool management, and cluster monitoring. It provides multi-vendor GPU support (NVIDIA, Huawei NPU, Cambricon MLU), vGPU capabilities, quota management, and comprehensive monitoring.

## Completed Components

### 1. GPU Scheduler Service (`app/services/gpu/gpu_scheduler.py`)

#### Supported GPU Vendors

**GPUVendor Enum:**
- NVIDIA - Full support with nvidia-smi
- HUAWEI - Placeholder for Ascend NPUs (npu-smi)
- CAMBRICON - Placeholder for MLUs (mlu-smi)
- ILUVATAR, MOORE_THREADS - Defined for future support

**GPUType Enum:**
- NVIDIA: A100, H100, V100, T4, RTX 3090/4090, L4, L40
- Huawei: Ascend-910, Ascend-910B, Ascend-310
- Cambricon: MLU370, MLU590
- Iluvatar: BI150
- Moore Threads: S4000

#### Core Classes

**GPUMemory:**
```python
@dataclass
class GPUMemory:
    value: float
    unit: MemoryUnit  # MB or GB
    # Conversion methods: to_mb(), to_gb()
```

**GPUSpec:**
```python
@dataclass
class GPUSpec:
    gpu_type: GPUType
    vendor: GPUVendor
    count: int
    memory: Optional[GPUMemory]
    min_compute_capability: Optional[float]
    supports_mig: Optional[bool]
    pcie_bandwidth: Optional[int]
```

**GPUResource:**
```python
@dataclass
class GPUResource:
    gpu_id: str
    gpu_type: GPUType
    vendor: GPUVendor
    uuid: Optional[str]
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_percent: float
    temperature: Optional[int]
    power_usage_w: Optional[float]
    is_allocated: bool
    node_name: str
```

**GPUAllocation:**
```python
@dataclass
class GPUAllocation:
    allocation_id: str
    gpu_ids: List[str]
    spec: GPUSpec
    allocated_to: str
    allocated_at: datetime
    expires_at: Optional[datetime]
```

#### GPU Backend Architecture

**GPUBackend (Abstract Base Class):**
```python
class GPUBackend(ABC):
    @abstractmethod
    async def enumerate_gpus() -> List[GPUResource]
    
    @abstractmethod
    async def get_gpu_metrics(gpu_id: str) -> Dict[str, Any]
    
    @abstractmethod
    async def allocate_gpu(gpu_id, allocation_id, spec) -> bool
    
    @abstractmethod
    async def deallocate_gpu(allocation_id) -> bool
```

**NVIDIABackend:**
- nvidia-smi integration for GPU enumeration
- 5-second caching for performance
- Detailed metrics via nvidia-smi query
- Support for MIG (Multi-Instance GPU) devices

**HuaweiNPUBackend:**
- Placeholder for npu-smi integration
- Ready for Ascend-910/910B/310 series

**CambriconMLUBackend:**
- Placeholder for mlu-smi integration
- Ready for MLU370/MLU590 series

#### GPUScheduler

**Key Methods:**
- `get_available_gpus()` - Find GPUs matching criteria
- `allocate()` - Allocate GPUs with TTL support
- `deallocate()` - Release GPU allocation
- `list_allocations()` - List all allocations
- `cleanup_expired_allocations()` - Auto-cleanup
- `get_cluster_gpu_summary()` - Cluster-wide stats

### 2. GPU Monitoring Service (`app/services/gpu/gpu_monitoring.py`)

#### Metric Types

**MetricType Enum:**
- UTILIZATION - GPU utilization %
- MEMORY - Memory usage
- TEMPERATURE - Core temperature
- POWER - Power consumption
- CLOCK - Clock speeds
- PCIE - PCIe link info

#### Monitoring Classes

**GPUMetric:**
```python
@dataclass
class GPUMetric:
    gpu_id: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

**GPUStatistics:**
```python
@dataclass
class GPUStatistics:
    gpu_id: str
    window_start: datetime
    window_end: datetime
    avg_utilization: float
    max_utilization: float
    avg_memory_used_mb: float
    avg_temperature: float
    max_temperature: int
    avg_power_w: float
    total_energy_kwh: float
```

**GPUHealthStatus:**
```python
@dataclass
class GPUHealthStatus:
    gpu_id: str
    healthy: bool
    issues: List[str]
    warnings: List[str]
    last_check: datetime
```

#### GPUMonitor Features

**Collection:**
- 10-second collection interval (configurable)
- Automatic metric type inference
- In-memory history with max size limit
- Prometheus export format support

**Health Checks:**
- High temperature detection (>90°C = error, >80°C = warning)
- High utilization warning (>95%)
- ECC error detection
- Power limit proximity check
- Persistence mode check

**Statistics:**
- Time window analysis (default 60 minutes)
- Min/max/average calculations
- Energy consumption tracking

### 3. Resource Pool Manager (`app/services/gpu/resource_pool.py`)

#### Resource Types

**ResourceType Enum:**
- GPU, CPU, MEMORY, STORAGE, CUSTOM

#### Pool Configuration

**PoolQuotaType:**
- HARD - Cannot exceed
- SOFT - Can exceed with warning
- BURST - Can exceed for limited time

**AllocationPolicy:**
- BEST_FIT - Use smallest sufficient resource
- WORST_FIT - Use largest available
- FIRST_FIT - Use first available
- PACK - Pack tasks per node
- SPREAD - Spread across nodes

#### Core Classes

**ResourceQuota:**
```python
@dataclass
class ResourceQuota:
    resource_type: ResourceType
    quota_type: PoolQuotaType
    limit: float
    unit: str
    burst_limit: Optional[float]
    burst_duration_seconds: Optional[int]
```

**ResourceRequest:**
```python
@dataclass
class ResourceRequest:
    resource_type: ResourceType
    amount: float
    unit: str
    gpu_type: Optional[GPUType]
    gpu_vendor: Optional[GPUVendor]
    constraints: Dict[str, Any]
    affinity: Optional[List[str]]
    anti_affinity: Optional[List[str]]
```

**ResourcePool:**
```python
@dataclass
class ResourcePool:
    pool_id: str
    name: str
    node_names: List[str]
    quotas: Dict[ResourceType, ResourceQuota]
    allocation_policy: AllocationPolicy
    enabled: bool
    labels: Dict[str, str]
```

**PoolAllocation:**
```python
@dataclass
class PoolAllocation:
    allocation_id: str
    pool_id: str
    task_id: str
    user_id: str
    resources: Dict[ResourceType, ResourceRequest]
    allocated_at: datetime
    expires_at: Optional[datetime]
```

**NodeInfo:**
```python
@dataclass
class NodeInfo:
    node_name: str
    pool_id: str
    available_resources: Dict[ResourceType, float]
    total_resources: Dict[ResourceType, float]
    allocated_resources: Dict[ResourceType, float]
    is_ready: bool
    is_schedulable: bool
```

#### ResourcePoolManager Methods

- `create_pool()` - Create new pool
- `delete_pool()` - Delete pool (with safety check)
- `allocate_from_pool()` - Allocate with quota enforcement
- `deallocate_from_pool()` - Release resources
- `get_pool_status()` - Get usage vs quotas
- `add_node_to_pool()` - Add node to pool
- `remove_node_from_pool()` - Remove node from pool
- `cleanup_expired_allocations()` - Auto-cleanup
- `get_cluster_summary()` - Cluster-wide stats

### 4. Database Models (`app/models/gpu.py`)

**GPURecord:**
- GPU inventory tracking
- MIG device support
- Health status
- Labels for flexible organization

**GPUAllocationRecord:**
- Allocation history
- TTL tracking
- Multi-GPU support

**ResourcePoolRecord:**
- Pool configuration
- Node membership

**ResourceQuotaRecord:**
- Per-pool quotas
- Burst configuration

**PoolAllocationRecord:**
- Pool allocation history
- Resource details stored as JSON

**GPUMetricsRecord:**
- Historical metrics for analysis
- Time-series indexed
- Additional metrics as JSON

### 5. GPU API Endpoints (`app/api/v1/gpu.py`)

#### GPU Resource Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gpu/resources` | GET | List available GPUs |
| `/gpu/summary` | GET | Cluster GPU summary |
| `/gpu/allocate` | POST | Allocate GPUs |
| `/gpu/allocations/{id}` | DELETE | Deallocate GPUs |
| `/gpu/allocations` | GET | List allocations |

#### GPU Metrics Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gpu/metrics/{gpu_id}` | GET | Get GPU metrics |
| `/gpu/metrics` | GET | Cluster metrics (JSON/Prometheus) |

#### Resource Pool Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gpu/pools` | POST | Create pool |
| `/gpu/pools` | GET | List pools |
| `/gpu/pools/{pool_id}` | GET | Get pool status |
| `/gpu/pools/{pool_id}` | DELETE | Delete pool |
| `/gpu/pools/allocate` | POST | Allocate from pool |
| `/gpu/pools/allocations/{id}` | DELETE | Deallocate from pool |
| `/gpu/pools/allocations` | GET | List pool allocations |
| `/gpu/cluster/summary` | GET | Cluster resource summary |
| `/gpu/maintenance/cleanup` | POST | Cleanup expired allocations |

## API Examples

### Allocate GPUs

```python
POST /gpu/allocate
{
  "spec": {
    "gpu_type": "A100",
    "vendor": "nvidia",
    "count": 2,
    "memory": {"value": 40, "unit": "GB"}
  },
  "task_id": "training-job-123",
  "ttl_minutes": 120
}
```

### Create Resource Pool

```python
POST /gpu/pools
{
  "name": "training-pool",
  "node_names": ["gpu-node-1", "gpu-node-2"],
  "quotas": {
    "gpu": {
      "resource_type": "gpu",
      "quota_type": "hard",
      "limit": 16,
      "unit": "count"
    }
  },
  "allocation_policy": "spread",
  "description": "GPU pool for training jobs"
}
```

### Get Pool Status

```python
GET /gpu/pools/{pool_id}

Response:
{
  "pool_id": "pool-training",
  "name": "training-pool",
  "enabled": true,
  "nodes": ["gpu-node-1", "gpu-node-2"],
  "quotas": {
    "gpu": {"limit": 16, "unit": "count", "type": "hard"}
  },
  "usage": {"gpu": 8},
  "available": {"gpu": 8},
  "active_allocations": 4
}
```

## Architecture Decisions

1. **Multi-Vendor Support**: Abstract backend pattern allows adding new GPU vendors
2. **nvidia-smi Integration**: Using nvidia-smi for NVIDIA GPU enumeration and metrics
3. **Quota Enforcement**: Hard, soft, and burst quotas for flexible resource control
4. **Allocation Policies**: Best-fit, worst-fit, first-fit, pack, spread for different use cases
5. **In-Memory Monitoring**: Fast metric collection with optional persistence
6. **Prometheus Export**: Native support for Prometheus metrics format

## Dependencies

### System Requirements
- nvidia-smi (for NVIDIA GPUs)
- npu-smi (for Huawei NPUs, optional)
- mlu-smi (for Cambricon MLUs, optional)

### Backend
- asyncio: Async operations
- subprocess: CLI tool integration
- sqlalchemy: Database ORM

## Files Created

```
apps/backend/app/services/gpu/
├── __init__.py           # Service exports
├── gpu_scheduler.py      # GPU scheduling with multi-vendor support
├── gpu_monitoring.py     # GPU metrics and health monitoring
└── resource_pool.py      # Resource pool management

apps/backend/app/models/
└── gpu.py                # GPU-related database models

apps/backend/app/api/v1/
└── gpu.py                # GPU and pool API endpoints
```

## Next Steps

Phase 8: 算法市场与AIHub
- 算法市场UI
- 算法订阅与部署
- 模型应用市场
- Pipeline SDK

## Notes

- Huawei NPU and Cambricon MLU backends are stubs pending driver/API availability
- vGPU support requires MIG-enabled GPUs or vGPU license
- For production, metrics should be persisted to time-series database
- Consider GPU affinity for multi-GPU training jobs
- NUMA awareness for optimal performance

## Remaining Work for Phase 7

All short-term tasks completed!
