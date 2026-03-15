"""
GPU Monitoring Service

Provides real-time GPU metrics collection and historical monitoring.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.gpu.gpu_scheduler import (
    GPUVendor,
    GPUType,
    GPUResource,
    GPUScheduler,
    get_gpu_scheduler,
)

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """GPU metric types"""
    UTILIZATION = "utilization"
    MEMORY = "memory"
    TEMPERATURE = "temperature"
    POWER = "power"
    CLOCK = "clock"
    PCIE = "pcie"


@dataclass
class GPUMetric:
    """Single GPU metric point"""
    gpu_id: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GPUStatistics:
    """GPU statistics over a time window"""
    gpu_id: str
    gpu_type: GPUType
    vendor: GPUVendor
    window_start: datetime
    window_end: datetime

    # Utilization
    avg_utilization: float
    max_utilization: float
    min_utilization: float

    # Memory
    avg_memory_used_mb: float
    max_memory_used_mb: int
    min_memory_used_mb: int
    avg_memory_utilization: float

    # Temperature
    avg_temperature: float
    max_temperature: int

    # Power
    avg_power_w: float
    max_power_w: float
    total_energy_kwh: float

    # Sample count
    sample_count: int


@dataclass
class GPUHealthStatus:
    """GPU health status"""
    gpu_id: str
    healthy: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class GPUMetricsSnapshot:
    """Snapshot of all GPU metrics at a point in time"""
    timestamp: datetime
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class GPUMonitor:
    """
    GPU monitoring service

    Collects and aggregates GPU metrics.
    """

    def __init__(self, db: Session, collection_interval_seconds: int = 10):
        self.db = db
        self.collection_interval = collection_interval_seconds
        self._scheduler: Optional[GPUScheduler] = None
        self._metrics_history: Dict[str, List[GPUMetric]] = {}
        self._max_history_size = 1000
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

    @property
    def scheduler(self) -> GPUScheduler:
        """Lazy load scheduler"""
        if self._scheduler is None:
            self._scheduler = get_gpu_scheduler(self.db)
        return self._scheduler

    async def collect_metrics(self) -> GPUMetricsSnapshot:
        """
        Collect current metrics from all GPUs

        Returns:
            GPUMetricsSnapshot with current metrics
        """
        snapshot = GPUMetricsSnapshot(timestamp=datetime.now())

        for vendor in [GPUVendor.NVIDIA, GPUVendor.HUAWEI, GPUVendor.CAMBRICON]:
            backend = self.scheduler._backends.get(vendor)
            if not backend:
                continue

            try:
                gpus = await backend.enumerate_gpus()
                for gpu in gpus:
                    metrics = await backend.get_gpu_metrics(gpu.gpu_id)
                    if metrics:
                        snapshot.metrics[gpu.gpu_id] = {
                            "gpu_type": gpu.gpu_type.value,
                            "vendor": gpu.vendor.value,
                            "metrics": metrics,
                        }

                        # Store in history
                        self._store_metric(gpu.gpu_id, metrics)

            except Exception as e:
                logger.error(f"Error collecting metrics for {vendor}: {e}")

        return snapshot

    def _store_metric(self, gpu_id: str, metrics: Dict[str, Any]):
        """Store metric in history"""
        if gpu_id not in self._metrics_history:
            self._metrics_history[gpu_id] = []

        timestamp = datetime.now()

        # Extract and store individual metrics
        for key, value in metrics.items():
            if value is None:
                continue

            metric_type = self._infer_metric_type(key)
            if metric_type:
                metric = GPUMetric(
                    gpu_id=gpu_id,
                    metric_type=metric_type,
                    value=float(value) if isinstance(value, (int, float)) else 0,
                    unit=self._get_metric_unit(key),
                    timestamp=timestamp,
                )
                self._metrics_history[gpu_id].append(metric)

        # Trim history
        if len(self._metrics_history[gpu_id]) > self._max_history_size:
            self._metrics_history[gpu_id] = self._metrics_history[gpu_id][-self._max_history_size:]

    def _infer_metric_type(self, key: str) -> Optional[MetricType]:
        """Infer metric type from key name"""
        key_lower = key.lower()
        if "util" in key_lower:
            return MetricType.UTILIZATION
        elif "mem" in key_lower and "used" in key_lower:
            return MetricType.MEMORY
        elif "temp" in key_lower or "temperature" in key_lower:
            return MetricType.TEMPERATURE
        elif "power" in key_lower:
            return MetricType.POWER
        elif "clock" in key_lower:
            return MetricType.CLOCK
        elif "pcie" in key_lower:
            return MetricType.PCIE
        return None

    def _get_metric_unit(self, key: str) -> str:
        """Get unit for metric"""
        key_lower = key.lower()
        if "util" in key_lower:
            return "%"
        elif "mem" in key_lower:
            return "MB"
        elif "temp" in key_lower or "temperature" in key_lower:
            return "C"
        elif "power" in key_lower:
            return "W"
        elif "clock" in key_lower:
            return "MHz"
        return ""

    async def get_current_metrics(self, gpu_id: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for a specific GPU"""
        snapshot = await self.collect_metrics()
        return snapshot.metrics.get(gpu_id, {}).get("metrics")

    async def get_gpu_statistics(
        self,
        gpu_id: str,
        window_minutes: int = 60,
    ) -> Optional[GPUStatistics]:
        """
        Get statistics for a GPU over a time window

        Args:
            gpu_id: GPU ID
            window_minutes: Time window in minutes

        Returns:
            GPUStatistics or None
        """
        window_start = datetime.now() - timedelta(minutes=window_minutes)
        window_end = datetime.now()

        history = self._metrics_history.get(gpu_id, [])
        if not history:
            return None

        # Filter by time window
        window_metrics = [
            m for m in history
            if window_start <= m.timestamp <= window_end
        ]

        if not window_metrics:
            return None

        # Get GPU info
        snapshot = await self.collect_metrics()
        gpu_info = snapshot.metrics.get(gpu_id, {})
        gpu_type = GPUType(gpu_info.get("gpu_type", "T4"))
        vendor = GPUVendor(gpu_info.get("vendor", "nvidia"))

        # Calculate statistics
        util_metrics = [m for m in window_metrics if m.metric_type == MetricType.UTILIZATION]
        mem_metrics = [m for m in window_metrics if m.metric_type == MetricType.MEMORY]
        temp_metrics = [m for m in window_metrics if m.metric_type == MetricType.TEMPERATURE]
        power_metrics = [m for m in window_metrics if m.metric_type == MetricType.POWER]

        avg_util = sum(m.value for m in util_metrics) / len(util_metrics) if util_metrics else 0
        max_util = max((m.value for m in util_metrics), default=0)
        min_util = min((m.value for m in util_metrics), default=0)

        avg_mem = sum(m.value for m in mem_metrics) / len(mem_metrics) if mem_metrics else 0
        max_mem = int(max((m.value for m in mem_metrics), default=0))
        min_mem = int(min((m.value for m in mem_metrics), default=0))

        # Get total memory from current metrics
        current = await self.get_current_metrics(gpu_id)
        total_mem = current.get("mem_total", 0) if current else 0
        avg_mem_util = (avg_mem / total_mem * 100) if total_mem > 0 else 0

        avg_temp = sum(m.value for m in temp_metrics) / len(temp_metrics) if temp_metrics else 0
        max_temp = int(max((m.value for m in temp_metrics), default=0))

        avg_power = sum(m.value for m in power_metrics) / len(power_metrics) if power_metrics else 0
        max_power = max((m.value for m in power_metrics), default=0)

        # Calculate energy (kWh)
        total_energy = (avg_power * len(power_metrics) * self.collection_interval) / (1000 * 3600)

        return GPUStatistics(
            gpu_id=gpu_id,
            gpu_type=gpu_type,
            vendor=vendor,
            window_start=window_start,
            window_end=window_end,
            avg_utilization=avg_util,
            max_utilization=max_util,
            min_utilization=min_util,
            avg_memory_used_mb=avg_mem,
            max_memory_used_mb=max_mem,
            min_memory_used_mb=min_mem,
            avg_memory_utilization=avg_mem_util,
            avg_temperature=avg_temp,
            max_temperature=max_temp,
            avg_power_w=avg_power,
            max_power_w=max_power,
            total_energy_kwh=total_energy,
            sample_count=len(window_metrics),
        )

    async def check_gpu_health(self, gpu_id: str) -> GPUHealthStatus:
        """
        Check GPU health status

        Args:
            gpu_id: GPU ID to check

        Returns:
            GPUHealthStatus
        """
        status = GPUHealthStatus(gpu_id=gpu_id, healthy=True)

        metrics = await self.get_current_metrics(gpu_id)
        if not metrics:
            status.issues.append("Unable to retrieve metrics")
            status.healthy = False
            return status

        # Check temperature
        temp = metrics.get("temperature")
        if temp and temp > 90:
            status.issues.append(f"High temperature: {temp}°C")
            status.healthy = False
        elif temp and temp > 80:
            status.warnings.append(f"Elevated temperature: {temp}°C")

        # Check utilization
        util = metrics.get("gpu_util")
        if util is not None and util > 95:
            status.warnings.append(f"Very high utilization: {util}%")

        # Check memory errors
        ecc_errors = metrics.get("ecc_errors")
        if ecc_errors and ecc_errors > 0:
            status.issues.append(f"ECC errors detected: {ecc_errors}")
            status.healthy = False

        # Check power
        power = metrics.get("power_draw")
        max_power = metrics.get("power_limit")
        if power and max_power and power > max_power * 0.9:
            status.warnings.append(f"Power near limit: {power}W / {max_power}W")

        # Check for persistence mode
        persistence = metrics.get("persistence_mode")
        if persistence == "Disabled":
            status.warnings.append("Persistence mode disabled")

        return status

    async def start_monitoring(self):
        """Start continuous monitoring"""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self):
        """Monitoring loop"""
        while self._is_monitoring:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)

    def get_metrics_history(
        self,
        gpu_id: str,
        metric_type: Optional[MetricType] = None,
        limit: int = 100,
    ) -> List[GPUMetric]:
        """Get metrics history for a GPU"""
        history = self._metrics_history.get(gpu_id, [])

        if metric_type:
            history = [m for m in history if m.metric_type == metric_type]

        return history[-limit:]

    async def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get cluster-wide GPU metrics"""
        snapshot = await self.collect_metrics()

        total_gpus = len(snapshot.metrics)
        total_util = 0
        total_mem = 0
        total_mem_used = 0
        high_temp_count = 0

        for gpu_id, data in snapshot.metrics.items():
            metrics = data.get("metrics", {})
            total_util += metrics.get("gpu_util", 0)
            total_mem += metrics.get("mem_total", 0)
            total_mem_used += metrics.get("mem_used", 0)
            if metrics.get("temperature", 0) > 80:
                high_temp_count += 1

        return {
            "timestamp": snapshot.timestamp,
            "total_gpus": total_gpus,
            "average_utilization": total_util / total_gpus if total_gpus > 0 else 0,
            "total_memory_gb": total_mem / 1024,
            "used_memory_gb": total_mem_used / 1024,
            "memory_utilization_percent": (total_mem_used / total_mem * 100) if total_mem > 0 else 0,
            "high_temperature_count": high_temp_count,
            "gpu_details": snapshot.metrics,
        }

    async def export_metrics(
        self,
        format: str = "json",
        gpu_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Export metrics in specified format

        Args:
            format: Export format (json, prometheus)
            gpu_ids: Optional list of GPU IDs to export

        Returns:
            Formatted metrics string
        """
        snapshot = await self.collect_metrics()

        if format == "prometheus":
            return self._to_prometheus_format(snapshot, gpu_ids)

        return self._to_json_format(snapshot, gpu_ids)

    def _to_json_format(
        self,
        snapshot: GPUMetricsSnapshot,
        gpu_ids: Optional[List[str]] = None,
    ) -> str:
        """Convert to JSON format"""
        import json

        data = {
            "timestamp": snapshot.timestamp.isoformat(),
            "gpus": {},
        }

        for gpu_id, metrics in snapshot.metrics.items():
            if gpu_ids and gpu_id not in gpu_ids:
                continue
            data["gpus"][gpu_id] = metrics

        return json.dumps(data, indent=2)

    def _to_prometheus_format(
        self,
        snapshot: GPUMetricsSnapshot,
        gpu_ids: Optional[List[str]] = None,
    ) -> str:
        """Convert to Prometheus format"""
        lines = []

        for gpu_id, data in snapshot.metrics.items():
            if gpu_ids and gpu_id not in gpu_ids:
                continue

            metrics = data.get("metrics", {})
            labels = f'gpu_id="{gpu_id}",gpu_type="{data.get("gpu_type", "")}",vendor="{data.get("vendor", "")}"'

            for key, value in metrics.items():
                if value is None or not isinstance(value, (int, float)):
                    continue
                lines.append(f'gpu_{key}{{{labels}}} {value}')

        return "\n".join(lines)


# Singleton
_monitor: Optional[GPUMonitor] = None


def get_gpu_monitor(db: Session, collection_interval: int = 10) -> GPUMonitor:
    """Get or create the GPU monitor instance"""
    return GPUMonitor(db, collection_interval)
