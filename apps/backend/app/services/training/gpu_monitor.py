"""
GPU Monitoring Service for Training Jobs

Provides real-time GPU utilization monitoring for training jobs,
including temperature, memory usage, and compute utilization.
"""

import logging
import asyncio
import subprocess
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, replace
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class GPUMetrics:
    """GPU metrics snapshot"""
    gpu_id: int
    name: str
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_celsius: float
    power_draw_watts: float
    processes: List[Dict[str, Any]]

    @property
    def memory_used_percent(self) -> float:
        return (self.memory_used_mb / self.memory_total_mb * 100) if self.memory_total_mb > 0 else 0

    @property
    def is_healthy(self) -> bool:
        """Check if GPU is healthy (temperature < 90°C)"""
        return self.temperature_celsius < 90

    @property
    def utilization_status(self) -> str:
        """Get utilization status category"""
        if self.utilization_percent > 80:
            return "high"
        elif self.utilization_percent > 40:
            return "medium"
        else:
            return "low"


class GPUMonitor:
    """
    GPU Monitor using nvidia-smi

    Collects GPU metrics from nvidia-smi command.
    """

    def __init__(self, poll_interval_seconds: float = 5.0):
        self.poll_interval = poll_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def get_gpu_metrics(self) -> List[GPUMetrics]:
        """
        Get current GPU metrics using nvidia-smi

        Returns:
            List of GPU metrics
        """
        try:
            # Use nvidia-smi to query GPU metrics in CSV format
            cmd = [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,"
                "temperature.gpu,power.draw,processes.name,processes.pid,processes.used_memory",
                "--format=csv,noheader,nounits"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                logger.warning(f"nvidia-smi returned code {process.returncode}")
                return []

            return self._parse_nvidia_smi_output(stdout.decode())

        except FileNotFoundError:
            logger.warning("nvidia-smi not found, returning mock data")
            return self._get_mock_gpu_metrics()
        except Exception as e:
            logger.error(f"Failed to get GPU metrics: {e}")
            return []

    def _parse_nvidia_smi_output(self, output: str) -> List[GPUMetrics]:
        """Parse nvidia-smi CSV output"""
        metrics = []
        lines = output.strip().split('\n')

        for line in lines:
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 7:
                continue

            try:
                gpu_metrics = GPUMetrics(
                    gpu_id=int(parts[0]),
                    name=parts[1],
                    utilization_percent=float(parts[2]),
                    memory_used_mb=float(parts[3]),
                    memory_total_mb=float(parts[4]),
                    temperature_celsius=float(parts[5]),
                    power_draw_watts=float(parts[6]),
                    processes=self._parse_processes(parts[7:] if len(parts) > 7 else []),
                )
                metrics.append(gpu_metrics)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse GPU metrics line: {line}, error: {e}")

        return metrics

    def _parse_processes(self, process_parts: List[str]) -> List[Dict[str, Any]]:
        """Parse process information from nvidia-smi output"""
        processes = []
        # Process format: "process_name:pid:used_memory"
        process_str = ','.join(process_parts)

        if process_str == "":
            return []

        # Split by multiple processes (separated by ";;;")
        for proc in process_str.split(';;;'):
            proc_parts = proc.split(':')
            if len(proc_parts) >= 3:
                processes.append({
                    "name": proc_parts[0],
                    "pid": proc_parts[1],
                    "memory_mb": float(proc_parts[2]) if proc_parts[2] else 0,
                })

        return processes

    def _get_mock_gpu_metrics(self) -> List[GPUMetrics]:
        """Return mock GPU metrics for testing"""
        return [
            GPUMetrics(
                gpu_id=0,
                name="NVIDIA GeForce RTX 3090",
                utilization_percent=75.5,
                memory_used_mb=18956,
                memory_total_mb=24576,
                temperature_celsius=72.0,
                power_draw_watts=280.0,
                processes=[],
            ),
            GPUMetrics(
                gpu_id=1,
                name="NVIDIA GeForce RTX 3090",
                utilization_percent=82.3,
                memory_used_mb=20480,
                memory_total_mb=24576,
                temperature_celsius=75.0,
                power_draw_watts=295.0,
                processes=[],
            ),
        ]

    async def start_monitoring(
        self,
        callback: callable[[List[GPUMetrics]], None],
    ) -> None:
        """
        Start continuous GPU monitoring

        Args:
            callback: Function to call with each metrics update
        """
        self._running = True

        async def _monitor_loop():
            while self._running:
                try:
                    metrics = await self.get_gpu_metrics()
                    await callback(metrics)
                except Exception as e:
                    logger.error(f"Error in GPU monitoring loop: {e}")

                await asyncio.sleep(self.poll_interval)

        self._task = asyncio.create_task(_monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop continuous GPU monitoring"""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class TrainingGPUMonitor:
    """
    GPU Monitor for Training Jobs

    Tracks GPU utilization specifically for training jobs,
    providing historical metrics and alerts.
    """

    def __init__(self, job_id: str, gpu_monitor: GPUMonitor):
        self.job_id = job_id
        self.gpu_monitor = gpu_monitor
        self._metrics_history: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
        self._start_time: Optional[datetime] = None

    async def start_monitoring(self, duration_minutes: Optional[float] = None) -> None:
        """
        Start monitoring GPU for the training job

        Args:
            duration_minutes: How long to monitor (None = until stopped)
        """
        self._start_time = datetime.utcnow()

        async def metrics_callback(metrics: List[GPUMetrics]):
            timestamp = datetime.utcnow()

            for metric in metrics:
                # Store in history
                self._metrics_history.append({
                    "timestamp": timestamp.isoformat(),
                    "job_id": self.job_id,
                    **{
                        "gpu_id": metric.gpu_id,
                        "name": metric.name,
                        "utilization_percent": metric.utilization_percent,
                        "memory_used_mb": metric.memory_used_mb,
                        "memory_total_mb": metric.memory_total_mb,
                        "temperature_celsius": metric.temperature_celsius,
                        "power_draw_watts": metric.power_draw_watts,
                        "memory_used_percent": metric.memory_used_percent,
                        "is_healthy": metric.is_healthy,
                        "utilization_status": metric.utilization_status,
                    }
                })
                )

                # Check for alerts
                await self._check_alerts(metric, timestamp)

        # Start monitoring
        if duration_minutes:
            # Run for specified duration then stop
            await self.gpu_monitor.start_monitoring(metrics_callback)
            await asyncio.sleep(duration_minutes * 60)
            await self.stop_monitoring()
        else:
            # Run until stopped
            await self.gpu_monitor.start_monitoring(metrics_callback)

    async def stop_monitoring(self) -> None:
        """Stop monitoring GPU for the training job"""
        await self.gpu_monitor.stop_monitoring()

    async def _check_alerts(self, metric: GPUMetrics, timestamp: datetime) -> None:
        """Check for alert conditions and generate alerts"""
        alerts = []

        # Temperature alert
        if metric.temperature_celsius > 85:
            alerts.append({
                "timestamp": timestamp.isoformat(),
                "job_id": self.job_id,
                "gpu_id": metric.gpu_id,
                "type": "high_temperature",
                "severity": "warning" if metric.temperature_celsius < 90 else "critical",
                "message": f"GPU {metric.gpu_id} temperature: {metric.temperature_celsius}°C",
                "value": metric.temperature_celsius,
            })

        # Memory alert
        if metric.memory_used_percent > 95:
            alerts.append({
                "timestamp": timestamp.isoformat(),
                "job_id": self.job_id,
                "gpu_id": metric.gpu_id,
                "type": "high_memory",
                "severity": "warning",
                "message": f"GPU {metric.gpu_id} memory usage: {metric.memory_used_percent:.1f}%",
                "value": metric.memory_used_percent,
            })

        # Low utilization alert
        if metric.utilization_percent < 10 and metric.memory_used_mb > 1000:
            alerts.append({
                "timestamp": timestamp.isoformat(),
                "job_id": self.job_id,
                "gpu_id": metric.gpu_id,
                "type": "low_utilization",
                "severity": "info",
                "message": f"GPU {metric.gpu_id} underutilized: {metric.utilization_percent:.1f}%",
                "value": metric.utilization_percent,
            })

        self._alerts.extend(alerts)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        if not self._metrics_history:
            return {}

        # Calculate statistics
        utilizations = [m["utilization_percent"] for m in self._metrics_history]
        temperatures = [m["temperature_celsius"] for m in self._metrics_history]
        memory_usage = [m["memory_used_percent"] for m in self._metrics_history]

        duration = None
        if self._start_time:
            duration = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "job_id": self.job_id,
            "duration_seconds": duration,
            "samples_count": len(self._metrics_history),
            "avg_utilization_percent": sum(utilizations) / len(utilizations) if utilizations else 0,
            "max_utilization_percent": max(utilizations) if utilizations else 0,
            "min_utilization_percent": min(utilizations) if utilizations else 0,
            "avg_temperature_celsius": sum(temperatures) / len(temperatures) if temperatures else 0,
            "max_temperature_celsius": max(temperatures) if temperatures else 0,
            "avg_memory_usage_percent": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
            "peak_memory_usage_percent": max(memory_usage) if memory_usage else 0,
            "alerts_count": len(self._alerts),
        }

    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metrics history"""
        if limit:
            return self._metrics_history[-limit:]
        return self._metrics_history

    def get_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by severity"""
        alerts = self._alerts

        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        return alerts

    def get_gpu_efficiency(self) -> Dict[str, float]:
        """
        Calculate GPU efficiency metrics

        Returns:
            Dictionary with efficiency metrics
        """
        if not self._metrics_history:
            return {}

        # Group by GPU
        gpu_metrics = defaultdict(lambda: {
            "utilization": [],
            "memory": [],
            "temperature": [],
        })

        for metric in self._metrics_history:
            gpu_id = metric["gpu_id"]
            gpu_metrics[gpu_id]["utilization"].append(metric["utilization_percent"])
            gpu_metrics[gpu_id]["memory"].append(metric["memory_used_percent"])
            gpu_metrics[gpu_id]["temperature"].append(metric["temperature_celsius"])

        efficiency = {}
        for gpu_id, metrics in gpu_metrics.items():
            if metrics["utilization"]:
                efficiency[f"gpu_{gpu_id}_avg_utilization"] = sum(metrics["utilization"]) / len(metrics["utilization"])
            if metrics["memory"]:
                efficiency[f"gpu_{gpu_id}_avg_memory"] = sum(metrics["memory"]) / len(metrics["memory"])
            if metrics["temperature"]:
                efficiency[f"gpu_{gpu_id}_avg_temp"] = sum(metrics["temperature"]) / len(metrics["temperature"])

        return efficiency


class MultiJobGPUMonitor:
    """
    Monitor GPU utilization across multiple training jobs
    """

    def __init__(self):
        self.job_monitors: Dict[str, TrainingGPUMonitor] = {}
        self.gpu_monitor = GPUMonitor(poll_interval_seconds=10.0)

    async def start_job_monitoring(
        self,
        job_id: str,
        duration_minutes: Optional[float] = None,
    ) -> None:
        """Start monitoring a training job"""
        if job_id not in self.job_monitors:
            self.job_monitors[job_id] = TrainingGPUMonitor(job_id, self.gpu_monitor)

        await self.job_monitors[job_id].start_monitoring(duration_minutes)

    async def stop_job_monitoring(self, job_id: str) -> None:
        """Stop monitoring a training job"""
        if job_id in self.job_monitors:
            await self.job_monitors[job_id].stop_monitoring()

    def get_job_metrics_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics summary for a job"""
        if job_id in self.job_monitors:
            return self.job_monitors[job_id].get_metrics_summary()
        return None

    def get_all_jobs_summary(self) -> Dict[str, Any]:
        """Get summary of all monitored jobs"""
        return {
            job_id: monitor.get_metrics_summary()
            for job_id, monitor in self.job_monitors.items()
        }


# Singleton instance
_gpu_monitor: Optional[GPUMonitor] = None
_multi_job_monitor: Optional[MultiJobGPUMonitor] = None


def get_gpu_monitor() -> GPUMonitor:
    """Get the GPU monitor singleton"""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMonitor()
    return _gpu_monitor


def get_multi_job_gpu_monitor() -> MultiJobGPUMonitor:
    """Get the multi-job GPU monitor singleton"""
    global _multi_job_monitor
    if _multi_job_monitor is None:
        _multi_job_monitor = MultiJobGPUMonitor()
    return _multi_job_monitor
