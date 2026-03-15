"""
GPU Scheduler Service

Provides GPU resource scheduling with vGPU support and
multi-vendor compatibility (NVIDIA, Huawei NPU, Cambricon MLU).
"""

import asyncio
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GPUVendor(str, Enum):
    """GPU vendor types - including domestic (Chinese) chip vendors"""
    # International
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"

    # Domestic (Chinese) GPU/NPU vendors
    HUAWEI = "huawei"           # Huawei Ascend (NPU)
    CAMBRICON = "cambricon"     # Cambricon (MLU)
    ILUVATAR = "iluvatar"       # Iluvatar CoreX (BI)
    MOORE_THREADS = "moore_threads"  # Moore Threads (Musa)
    ENFLAME = "enflame"         # Enflame (Suanhou/DTU)
    HYGON = "hygon"             # Hygon (DCU)
    BIREN = "biren"             # Biren (BR)
    METAX = "metax"             # MetaX (CIX)
    VASTAI = "vastai"           # Vastai (Erda)
    INNOSILICON = "innosilicon" # InnoSilicon (Fenghua)


class GPUType(str, Enum):
    """Specific GPU models"""
    # NVIDIA
    A100 = "A100"
    A100_80G = "A100-80GB"
    H100 = "H100"
    H100_80G = "H100-80GB"
    H200 = "H200"
    V100 = "V100"
    T4 = "T4"
    RTX_3090 = "RTX-3090"
    RTX_4090 = "RTX-4090"
    L4 = "L4"
    L40 = "L40"
    L40S = "L40S"

    # AMD
    MI200 = "MI200"
    MI250 = "MI250"
    MI300 = "MI300"
    MI300X = "MI300X"
    RX7900 = "RX7900"

    # Intel
    MAX1100 = "MAX1100"
    MAX1550 = "MAX1550"
    GMMA = "GMMA"

    # Huawei Ascend (NPU)
    ASCEND_910 = "Ascend-910"
    ASCEND_910A = "Ascend-910A"
    ASCEND_910B = "Ascend-910B"
    ASCEND_910C = "Ascend-910C"
    ASCEND_310 = "Ascend-310"
    ASCEND_310B = "Ascend-310B"
    ASCEND_310P = "Ascend-310P"
    ASCEND_920 = "Ascend-920"
    ASCEND_A2 = "Ascend-A2"
    ASCEND_S310 = "Ascend-S310"

    # Cambricon (MLU)
    MLU100 = "MLU100"
    MLU270 = "MLU270"
    MLU290 = "MLU290"
    MLU370 = "MLU370"
    MLU370_X4 = "MLU370-X4"
    MLU370_X8 = "MLU370-X8"
    MLU370_S4 = "MLU370-S4"
    MLU370_S8 = "MLU370-S8"
    MLU590 = "MLU590"
    MLU580 = "MLU580"
    MLU590_T = "MLU590-T"
    C100 = "C100"
    C200 = "C200"
    C500 = "C500"

    # Iluvatar CoreX
    BI100 = "BI100"
    BI150 = "BI150"
    BI164 = "BI164"
    BI300 = "BI300"
    BI350 = "BI350"
    TIANGAI = "Tiangai"

    # Moore Threads (Musa)
    S3000 = "S3000"
    S4000 = "S4000"
    S5000 = "S5000"
    S7000 = "S7000"
    S8000 = "S8000"
    MTT_S80 = "MTT-S80"
    CHUNXIAO = "Chunxiao"

    # Enflame (Suanhou/DTU)
    DTU1 = "DTU1"
    DTU2 = "DTU2"
    DTU3 = "DTU3"
    DTU4 = "DTU4"
    G10 = "G10"
    G11 = "G11"
    G12 = "G12"
    Q100 = "Q100"
    S40 = "S40"

    # Hygon (DCU)
    DCU1 = "DCU1"
    DCU2 = "DCU2"
    Z100 = "Z100"
    HYGON_C100 = "HYGON_C100"  # Hygon C100

    # Biren (BR)
    BR100 = "BR100"
    BR104 = "BR104"
    BR104L = "BR104L"
    BR140 = "BR140"
    BR210 = "BR210"

    # MetaX (CIX)
    CIX = "CIX"
    CIX_E1 = "CIX-E1"

    # Vastai (Erda)
    ERDA1 = "Erda1"
    ERDA2 = "Erda2"
    VASTAI_V1 = "Vastai-V1"

    # InnoSilicon (Fenghua)
    FENGHUA1 = "Fenghua1"
    FENGHUA2 = "Fenghua2"


class MemoryUnit(str, Enum):
    """Memory units"""
    MB = "MB"
    GB = "GB"


@dataclass
class GPUMemory:
    """GPU memory specification"""
    value: float
    unit: MemoryUnit = MemoryUnit.GB

    def to_mb(self) -> int:
        """Convert to MB"""
        if self.unit == MemoryUnit.GB:
            return int(self.value * 1024)
        return int(self.value)

    def to_gb(self) -> float:
        """Convert to GB"""
        if self.unit == MemoryUnit.MB:
            return self.value / 1024
        return self.value


@dataclass
class GPUSpec:
    """GPU resource specification"""
    gpu_type: GPUType
    vendor: GPUVendor = GPUVendor.NVIDIA
    count: int = 1
    memory: Optional[GPUMemory] = None
    min_compute_capability: Optional[float] = None
    supports_mig: Optional[bool] = None
    pcie_bandwidth: Optional[int] = None


@dataclass
class vGPUSpec:
    """Virtual GPU specification"""
    parent_gpu_id: str
    memory: GPUMemory
    cuda_cores: Optional[int] = None
    share_ratio: Optional[int] = None
    min_compute: Optional[float] = None


@dataclass
class GPUAllocation:
    """GPU allocation record"""
    allocation_id: str
    gpu_ids: List[str]
    spec: GPUSpec
    allocated_to: str
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    vgpu_configs: List[vGPUSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GPUResource:
    """Available GPU resource"""
    gpu_id: str
    gpu_type: GPUType
    vendor: GPUVendor
    uuid: Optional[str] = None
    bus_id: Optional[str] = None
    total_memory_mb: int = 0
    used_memory_mb: int = 0
    free_memory_mb: int = 0
    utilization_percent: float = 0
    temperature: Optional[int] = None
    power_usage_w: Optional[float] = None
    max_power_w: Optional[float] = None
    compute_capability: Optional[str] = None
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None
    is_mig_enabled: bool = False
    mig_devices: List[str] = field(default_factory=list)
    is_allocated: bool = False
    allocation_id: Optional[str] = None
    node_name: str = "localhost"
    numa_node: Optional[int] = None


class GPUBackend(ABC):
    """Abstract base class for GPU backends"""

    vendor: GPUVendor

    @abstractmethod
    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate all available GPUs"""
        pass

    @abstractmethod
    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        """Get current GPU metrics"""
        pass

    @abstractmethod
    async def allocate_gpu(
        self,
        gpu_id: str,
        allocation_id: str,
        spec: GPUSpec,
    ) -> bool:
        """Allocate a GPU"""
        pass

    @abstractmethod
    async def deallocate_gpu(self, allocation_id: str) -> bool:
        """Deallocate a GPU"""
        pass


class NVIDIABackend(GPUBackend):
    """NVIDIA GPU backend implementation"""

    vendor = GPUVendor.NVIDIA

    def __init__(self):
        self._allocations: Dict[str, GPUAllocation] = {}
        self._gpu_cache: Optional[List[GPUResource]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=5)

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate NVIDIA GPUs using nvidia-smi"""
        # Return cached result if fresh
        if (self._gpu_cache and self._cache_time and
                datetime.now() - self._cache_time < self._cache_ttl):
            return self._gpu_cache

        gpus = []

        try:
            # Get GPU count
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning(f"nvidia-smi failed: {result.stderr}")
                return []

            count = int(result.stdout.strip())

            # Get detailed info
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,power.limit,driver_version,cuda_version",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 12:
                        gpu = GPUResource(
                            gpu_id=f"gpu-{parts[0]}",
                            gpu_type=self._parse_gpu_name(parts[1]),
                            vendor=GPUVendor.NVIDIA,
                            uuid=parts[2],
                            total_memory_mb=int(parts[3]),
                            used_memory_mb=int(parts[4]),
                            free_memory_mb=int(parts[5]),
                            utilization_percent=float(parts[6]),
                            temperature=int(parts[7]) if parts[7] else None,
                            power_usage_w=float(parts[8]) if parts[8] else None,
                            max_power_w=float(parts[9]) if parts[9] else None,
                            driver_version=parts[10],
                            cuda_version=parts[11],
                        )
                        gpus.append(gpu)

        except FileNotFoundError:
            logger.warning("nvidia-smi not found")
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi timed out")
        except Exception as e:
            logger.error(f"Error enumerating GPUs: {e}")

        self._gpu_cache = gpus
        self._cache_time = datetime.now()
        return gpus

    def _parse_gpu_name(self, name: str) -> GPUType:
        """Parse GPU name to GPUType"""
        name_upper = name.upper()
        for gpu_type in GPUType:
            if gpu_type.value.upper() in name_upper:
                return gpu_type
        return GPUType.T4  # Default

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        """Get detailed GPU metrics"""
        index = gpu_id.replace("gpu-", "")

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={index}",
                    "--query-gpu=timestamp,name,driver_version,cuda_version,pcie.link.gen.current,pcie.link.width.current,fan.speed,pstate,temperature.gpu,power.draw,clocks.gr,clocks.mem,utilization.gpu,utilization.memory,memory.used,memory.total",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                return {
                    "timestamp": parts[0] if len(parts) > 0 else None,
                    "name": parts[1] if len(parts) > 1 else None,
                    "driver_version": parts[2] if len(parts) > 2 else None,
                    "cuda_version": parts[3] if len(parts) > 3 else None,
                    "pcie_gen": parts[4] if len(parts) > 4 else None,
                    "pcie_width": parts[5] if len(parts) > 5 else None,
                    "fan_speed": parts[6] if len(parts) > 6 else None,
                    "pstate": parts[7] if len(parts) > 7 else None,
                    "temperature": int(parts[8]) if len(parts) > 8 and parts[8] else None,
                    "power_draw": float(parts[9]) if len(parts) > 9 and parts[9] else None,
                    "gpu_clock": int(parts[10]) if len(parts) > 10 and parts[10] else None,
                    "mem_clock": int(parts[11]) if len(parts) > 11 and parts[11] else None,
                    "gpu_util": float(parts[12]) if len(parts) > 12 and parts[12] else None,
                    "mem_util": float(parts[13]) if len(parts) > 13 and parts[13] else None,
                    "mem_used": int(parts[14]) if len(parts) > 14 and parts[14] else None,
                    "mem_total": int(parts[15]) if len(parts) > 15 and parts[15] else None,
                }

        except Exception as e:
            logger.error(f"Error getting GPU metrics: {e}")

        return {}

    async def allocate_gpu(
        self,
        gpu_id: str,
        allocation_id: str,
        spec: GPUSpec,
    ) -> bool:
        """Allocate a GPU (record-keeping)"""
        gpus = await self.enumerate_gpus()
        for gpu in gpus:
            if gpu.gpu_id == gpu_id:
                gpu.is_allocated = True
                gpu.allocation_id = allocation_id
                return True
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        """Deallocate a GPU"""
        gpus = await self.enumerate_gpus()
        for gpu in gpus:
            if gpu.allocation_id == allocation_id:
                gpu.is_allocated = False
                gpu.allocation_id = None
                return True
        return False


class HuaweiNPUBackend(GPUBackend):
    """Huawei NPU backend (Ascend) - Placeholder"""

    vendor = GPUVendor.HUAWEI

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Huawei NPUs using npu-smi"""
        gpus = []
        try:
            result = subprocess.run(
                ["npu-smi", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse npu-smi output
                pass
        except FileNotFoundError:
            logger.debug("npu-smi not found")
        except Exception as e:
            logger.error(f"Error enumerating NPUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class CambriconMLUBackend(GPUBackend):
    """Cambricon MLU backend - Placeholder"""

    vendor = GPUVendor.CAMBRICON

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Cambricon MLU devices using cnmon"""
        gpus = []
        try:
            result = subprocess.run(
                ["cnmon", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse cnmon output for MLU devices
                pass
        except FileNotFoundError:
            logger.debug("cnmon not found")
        except Exception as e:
            logger.error(f"Error enumerating MLUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class EnflameDTUBackend(GPUBackend):
    """Enflame DTU (Suanhou) backend"""

    vendor = GPUVendor.ENFLAME

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Enflame DTU devices"""
        gpus = []
        try:
            result = subprocess.run(
                ["dtu-smi", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse dtu-smi output
                pass
        except FileNotFoundError:
            logger.debug("dtu-smi not found")
        except Exception as e:
            logger.error(f"Error enumerating DTUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class HygonDCUBackend(GPUBackend):
    """Hygon DCU backend"""

    vendor = GPUVendor.HYGON

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Hygon DCU devices using rocm-smi"""
        gpus = []
        try:
            # Hygon DCU uses ROCm tools
            result = subprocess.run(
                ["rocm-smi", "--showallinfo"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse rocm-smi output for DCU devices
                pass
        except FileNotFoundError:
            logger.debug("rocm-smi not found")
        except Exception as e:
            logger.error(f"Error enumerating DCUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class IluvatarBackend(GPUBackend):
    """Iluvatar CoreX backend"""

    vendor = GPUVendor.ILUVATAR

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Iluvatar CoreX devices"""
        gpus = []
        try:
            result = subprocess.run(
                ["bi-smi", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse bi-smi output
                pass
        except FileNotFoundError:
            logger.debug("bi-smi not found")
        except Exception as e:
            logger.error(f"Error enumerating Iluvatar GPUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class MooreThreadsBackend(GPUBackend):
    """Moore Threads (Musa) backend"""

    vendor = GPUVendor.MOORE_THREADS

    async def enumerate_gpus(self) -> List[GPUResource]:
        """Enumerate Moore Threads devices using musa-smi"""
        gpus = []
        try:
            result = subprocess.run(
                ["musa-smi", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse musa-smi output
                pass
        except FileNotFoundError:
            logger.debug("musa-smi not found")
        except Exception as e:
            logger.error(f"Error enumerating Moore Threads GPUs: {e}")
        return gpus

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class BirenBackend(GPUBackend):
    """Biren (BR) backend - Placeholder"""

    vendor = GPUVendor.BIREN

    async def enumerate_gpus(self) -> List[GPUResource]:
        return []

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class MetaxBackend(GPUBackend):
    """MetaX (CIX) backend - Placeholder"""

    vendor = GPUVendor.METAX

    async def enumerate_gpus(self) -> List[GPUResource]:
        return []

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class VastaiBackend(GPUBackend):
    """Vastai (Erda) backend - Placeholder"""

    vendor = GPUVendor.VASTAI

    async def enumerate_gpus(self) -> List[GPUResource]:
        return []

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class InnoSiliconBackend(GPUBackend):
    """InnoSilicon (Fenghua) backend - Placeholder"""

    vendor = GPUVendor.INNOSILICON

    async def enumerate_gpus(self) -> List[GPUResource]:
        return []

    async def get_gpu_metrics(self, gpu_id: str) -> Dict[str, Any]:
        return {}

    async def allocate_gpu(self, gpu_id: str, allocation_id: str, spec: GPUSpec) -> bool:
        return False

    async def deallocate_gpu(self, allocation_id: str) -> bool:
        return False


class GPUScheduler:
    """GPU scheduler service"""

    def __init__(self, db: Session):
        self.db = db
        self._backends: Dict[GPUVendor, GPUBackend] = {
            # International
            GPUVendor.NVIDIA: NVIDIABackend(),
            # Domestic (Chinese) GPU/NPU vendors
            GPUVendor.HUAWEI: HuaweiNPUBackend(),
            GPUVendor.CAMBRICON: CambriconMLUBackend(),
            GPUVendor.ILUVATAR: IluvatarBackend(),
            GPUVendor.MOORE_THREADS: MooreThreadsBackend(),
            GPUVendor.ENFLAME: EnflameDTUBackend(),
            GPUVendor.HYGON: HygonDCUBackend(),
            GPUVendor.BIREN: BirenBackend(),
            GPUVendor.METAX: MetaxBackend(),
            GPUVendor.VASTAI: VastaiBackend(),
            GPUVendor.INNOSILICON: InnoSiliconBackend(),
        }
        self._allocations: Dict[str, GPUAllocation] = {}

    async def get_available_gpus(
        self,
        vendor: Optional[GPUVendor] = None,
        gpu_type: Optional[GPUType] = None,
        min_memory_mb: Optional[int] = None,
        unallocated_only: bool = True,
    ) -> List[GPUResource]:
        """Get available GPUs matching criteria"""
        available = []

        for v, backend in self._backends.items():
            if vendor and v != vendor:
                continue

            try:
                gpus = await backend.enumerate_gpus()
                for gpu in gpus:
                    if gpu_type and gpu.gpu_type != gpu_type:
                        continue
                    if min_memory_mb and gpu.free_memory_mb < min_memory_mb:
                        continue
                    if unallocated_only and gpu.is_allocated:
                        continue
                    available.append(gpu)
            except Exception as e:
                logger.error(f"Error enumerating GPUs for {v}: {e}")

        return available

    async def allocate(
        self,
        spec: GPUSpec,
        allocated_to: str,
        ttl_minutes: Optional[int] = None,
        preferred_gpu_ids: Optional[List[str]] = None,
    ) -> Optional[GPUAllocation]:
        """Allocate GPUs matching specification"""
        available = await self.get_available_gpus(
            vendor=spec.vendor,
            gpu_type=spec.gpu_type,
            min_memory_mb=spec.memory.to_mb() if spec.memory else None,
        )

        if preferred_gpu_ids:
            preferred = [g for g in available if g.gpu_id in preferred_gpu_ids]
            if len(preferred) >= spec.count:
                available = preferred
            else:
                return None

        if len(available) < spec.count:
            return None

        selected_gpus = available[:spec.count]
        allocation_id = f"alloc-{datetime.now().strftime('%Y%m%d%H%M%S')}-{spec.gpu_type.value}"
        gpu_ids = []

        backend = self._backends.get(spec.vendor)
        if not backend:
            return None

        for gpu in selected_gpus:
            success = await backend.allocate_gpu(gpu.gpu_id, allocation_id, spec)
            if not success:
                for allocated_id in gpu_ids:
                    await backend.deallocate_gpu(allocated_id)
                return None
            gpu_ids.append(gpu.gpu_id)

        expires_at = None
        if ttl_minutes:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        allocation = GPUAllocation(
            allocation_id=allocation_id,
            gpu_ids=gpu_ids,
            spec=spec,
            allocated_to=allocated_to,
            allocated_at=datetime.now(),
            expires_at=expires_at,
        )

        self._allocations[allocation_id] = allocation
        return allocation

    async def deallocate(self, allocation_id: str) -> bool:
        """Deallocate GPUs"""
        allocation = self._allocations.get(allocation_id)
        if not allocation:
            return False

        backend = self._backends.get(allocation.spec.vendor)
        if not backend:
            return False

        success = await backend.deallocate_gpu(allocation_id)

        if success:
            del self._allocations[allocation_id]

        return success

    async def get_allocation(self, allocation_id: str) -> Optional[GPUAllocation]:
        """Get allocation by ID"""
        return self._allocations.get(allocation_id)

    async def list_allocations(self, allocated_to: Optional[str] = None) -> List[GPUAllocation]:
        """List all allocations"""
        allocations = list(self._allocations.values())
        if allocated_to:
            allocations = [a for a in allocations if a.allocated_to == allocated_to]
        return allocations

    async def cleanup_expired_allocations(self) -> int:
        """Clean up expired allocations"""
        now = datetime.now()
        expired = [a_id for a_id, a in self._allocations.items()
                   if a.expires_at and a.expires_at < now]

        for allocation_id in expired:
            await self.deallocate(allocation_id)

        return len(expired)

    async def get_cluster_gpu_summary(self) -> Dict[str, Any]:
        """Get cluster-wide GPU summary"""
        summary = {
            "total_gpus": 0,
            "allocated_gpus": 0,
            "free_gpus": 0,
            "by_vendor": {},
            "by_type": {},
            "total_memory_mb": 0,
            "used_memory_mb": 0,
            "free_memory_mb": 0,
        }

        all_gpus = []
        for vendor, backend in self._backends.items():
            try:
                gpus = await backend.enumerate_gpus()
                all_gpus.extend(gpus)
            except Exception:
                pass

        summary["total_gpus"] = len(all_gpus)

        for gpu in all_gpus:
            if gpu.is_allocated:
                summary["allocated_gpus"] += 1
            else:
                summary["free_gpus"] += 1

            vendor_name = gpu.vendor.value
            if vendor_name not in summary["by_vendor"]:
                summary["by_vendor"][vendor_name] = {"total": 0, "allocated": 0}
            summary["by_vendor"][vendor_name]["total"] += 1
            if gpu.is_allocated:
                summary["by_vendor"][vendor_name]["allocated"] += 1

            type_name = gpu.gpu_type.value
            if type_name not in summary["by_type"]:
                summary["by_type"][type_name] = {"total": 0, "allocated": 0}
            summary["by_type"][type_name]["total"] += 1
            if gpu.is_allocated:
                summary["by_type"][type_name]["allocated"] += 1

            summary["total_memory_mb"] += gpu.total_memory_mb
            summary["used_memory_mb"] += gpu.used_memory_mb
            summary["free_memory_mb"] += gpu.free_memory_mb

        return summary


def get_gpu_scheduler(db: Session) -> GPUScheduler:
    """Get or create the GPU scheduler instance"""
    return GPUScheduler(db)
