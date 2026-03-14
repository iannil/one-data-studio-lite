"""
WebSocket Manager for Real-time Training Metrics

Provides WebSocket connections for streaming training metrics,
logs, and status updates to connected clients.
"""

import logging
import asyncio
import json
from typing import Dict, Set, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types"""
    # Training events
    TRAINING_STARTED = "training_started"
    TRAINING_STOPPED = "training_stopped"
    TRAINING_FAILED = "training_failed"
    TRAINING_COMPLETED = "training_completed"

    # Metric events
    METRICS_UPDATE = "metrics_update"
    METRICS_BATCH = "metrics_batch"

    # Log events
    LOG_ENTRY = "log_entry"
    LOG_BATCH = "log_batch"

    # Status events
    STATUS_UPDATE = "status_update"
    PROGRESS_UPDATE = "progress_update"

    # GPU events
    GPU_UPDATE = "gpu_update"

    # Checkpoint events
    CHECKPOINT_SAVED = "checkpoint_saved"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str
    job_id: str

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "job_id": self.job_id,
        })


class ConnectionManager:
    """
    Manages WebSocket connections for training job updates

    Maintains active connections and broadcasts messages
    to relevant subscribers.
    """

    def __init__(self):
        # Active connections: job_id -> set of websocket connections
        self.active_connections: Dict[str, Set[Any]] = {}

        # Connection metadata: connection -> job_ids
        self.connection_jobs: Dict[Any, Set[str]] = {}

    async def connect(self, websocket: Any, job_id: str) -> None:
        """Connect a websocket to a training job"""
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()

        self.active_connections[job_id].add(websocket)

        if websocket not in self.connection_jobs:
            self.connection_jobs[websocket] = set()
        self.connection_jobs[websocket].add(job_id)

        logger.info(f"WebSocket connected for job {job_id}")

    def disconnect(self, websocket: Any) -> None:
        """Disconnect a websocket from all jobs"""
        if websocket in self.connection_jobs:
            for job_id in self.connection_jobs[websocket]:
                if job_id in self.active_connections:
                    self.active_connections[job_id].discard(websocket)
                    if not self.active_connections[job_id]:
                        del self.active_connections[job_id]

            del self.connection_jobs[websocket]

        logger.info("WebSocket disconnected")

    async def broadcast_to_job(
        self,
        job_id: str,
        message: WebSocketMessage,
    ) -> None:
        """Broadcast a message to all connections for a job"""
        if job_id not in self.active_connections:
            return

        # Convert message to JSON once
        message_json = message.to_json()
        disconnected = set()

        for connection in self.active_connections[job_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_metrics(
        self,
        job_id: str,
        metrics: Dict[str, Any],
        step: Optional[int] = None,
    ) -> None:
        """Broadcast metrics update for a training job"""
        message = WebSocketMessage(
            event_type=EventType.METRICS_UPDATE,
            data={
                "metrics": metrics,
                "step": step,
                "timestamp": datetime.utcnow().isoformat(),
            },
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.broadcast_to_job(job_id, message)

    async def broadcast_log(
        self,
        job_id: str,
        log_message: str,
        level: str = "INFO",
        source: Optional[str] = None,
    ) -> None:
        """Broadcast log entry for a training job"""
        message = WebSocketMessage(
            event_type=EventType.LOG_ENTRY,
            data={
                "message": log_message,
                "level": level,
                "source": source,
                "timestamp": datetime.utcnow().isoformat(),
            },
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.broadcast_to_job(job_id, message)

    async def broadcast_status(
        self,
        job_id: str,
        status: str,
        message: Optional[str] = None,
    ) -> None:
        """Broadcast status update for a training job"""
        ws_message = WebSocketMessage(
            event_type=EventType.STATUS_UPDATE,
            data={
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.broadcast_to_job(job_id, ws_message)

    async def broadcast_progress(
        self,
        job_id: str,
        current_step: int,
        total_steps: Optional[int],
        epoch: Optional[int] = None,
        total_epochs: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Broadcast progress update for a training job"""
        data = {
            "current_step": current_step,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if total_steps:
            data["total_steps"] = total_steps
            data["progress_percent"] = (current_step / total_steps) * 100

        if epoch is not None:
            data["epoch"] = epoch
        if total_epochs:
            data["total_epochs"] = total_epochs

        if metrics:
            data["metrics"] = metrics

        ws_message = WebSocketMessage(
            event_type=EventType.PROGRESS_UPDATE,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.broadcast_to_job(job_id, ws_message)

    async def broadcast_gpu(
        self,
        job_id: str,
        gpu_stats: List[Dict[str, Any]],
    ) -> None:
        """Broadcast GPU utilization update"""
        message = WebSocketMessage(
            event_type=EventType.GPU_UPDATE,
            data={
                "gpus": gpu_stats,
                "timestamp": datetime.utcnow().isoformat(),
            },
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.broadcast_to_job(job_id, message)

    def get_connection_count(self, job_id: str) -> int:
        """Get number of active connections for a job"""
        return len(self.active_connections.get(job_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_jobs)


# Singleton instance
_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> ConnectionManager:
    """Get the WebSocket manager singleton"""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


class MetricsBroadcaster:
    """
    Broadcasts training metrics to connected WebSocket clients

    Can be used by training runners to push real-time updates.
    """

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self._buffer: Dict[str, List[Dict[str, Any]]] = {}

    async def log_metric(
        self,
        job_id: str,
        key: str,
        value: float,
        step: int,
        timestamp: Optional[float] = None,
    ) -> None:
        """Log a single metric"""
        # Add to buffer
        if job_id not in self._buffer:
            self._buffer[job_id] = []

        self._buffer[job_id].append({
            "key": key,
            "value": value,
            "step": step,
            "timestamp": timestamp or datetime.utcnow().timestamp(),
        })

        # Broadcast immediately
        await self.manager.broadcast_metrics(job_id, {key: value}, step)

    async def log_metrics(
        self,
        job_id: str,
        metrics: Dict[str, float],
        step: int,
    ) -> None:
        """Log multiple metrics at once"""
        for key, value in metrics.items():
            await self.log_metric(job_id, key, value, step)

    async def flush_batch(self, job_id: str, batch_size: int = 100) -> None:
        """Flush buffered metrics as a batch"""
        if job_id not in self._buffer or not self._buffer[job_id]:
            return

        batch = self._buffer[job_id][-batch_size:]
        if not batch:
            return

        message = WebSocketMessage(
            event_type=EventType.METRICS_BATCH,
            data={
                "metrics": batch,
                "count": len(batch),
            },
            timestamp=datetime.utcnow().isoformat(),
            job_id=job_id,
        )
        await self.manager.broadcast_to_job(job_id, message)

    def clear_buffer(self, job_id: str) -> None:
        """Clear metrics buffer for a job"""
        if job_id in self._buffer:
            del self._buffer[job_id]


def get_metrics_broadcaster() -> MetricsBroadcaster:
    """Get the metrics broadcaster singleton"""
    return MetricsBroadcaster(get_ws_manager())
