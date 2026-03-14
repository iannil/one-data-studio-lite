"""
GPU Scheduler

Handles scheduling of GPU resources across the cluster.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import heapq
import logging

from .vgpu_allocator import (
    VGPUAllocator,
    GPUAllocationRequest,
    GPUAllocation,
    GPUType,
    GPUAllocationStrategy,
    get_vgpu_allocator,
)

logger = logging.getLogger(__name__)


class SchedulingPolicy(str, Enum):
    """GPU scheduling policies"""
    BEST_FIT = "best_fit"           # Allocate from GPU with least available memory that fits
    WORST_FIT = "worst_fit"         # Allocate from GPU with most available memory
    FIRST_FIT = "first_fit"         # Allocate from first available GPU
    SPREAD = "spread"               # Spread allocations across GPUs
    PACK = "pack"                   # Pack allocations on fewest GPUs
    BIN_PACKING = "bin_packing"     # Bin packing algorithm for efficiency


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def numeric_value(self) -> int:
        return {"low": 0, "normal": 1, "high": 2, "urgent": 3}[self.value]


@dataclass
class GPUTask:
    """A task requiring GPU resources"""
    task_id: str
    resource_name: str
    gpu_type: Optional[GPUType] = None
    vgpu_count: int = 1
    memory_mb: Optional[int] = None
    strategy: GPUAllocationStrategy = GPUAllocationStrategy.EXCLUSIVE
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration_minutes: Optional[int] = None
    submit_time: datetime = field(default_factory=datetime.now)
    scheduled_time: Optional[datetime] = None
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None

    # Retry info
    retry_count: int = 0
    max_retries: int = 3

    # Constraints
    allowed_gpu_ids: Optional[Set[str]] = None  # Specific GPUs to use
    forbidden_gpu_ids: Optional[Set[str]] = None  # GPUs to avoid
    requires_mig: bool = False
    min_cuda_version: Optional[str] = None

    @property
    def is_pending(self) -> bool:
        return self.scheduled_time is None

    @property
    def is_running(self) -> bool:
        return self.started_time is not None and self.completed_time is None

    @property
    def is_completed(self) -> bool:
        return self.completed_time is not None

    @property
    def wait_time_seconds(self) -> float:
        """Calculate wait time from submission to now or start"""
        end = self.started_time or datetime.now()
        return (end - self.submit_time).total_seconds()

    @property
    def run_time_seconds(self) -> float:
        """Calculate run time if running or completed"""
        if not self.started_time:
            return 0
        end = self.completed_time or datetime.now()
        return (end - self.started_time).total_seconds()

    def to_allocation_request(self) -> GPUAllocationRequest:
        """Convert to GPUAllocationRequest"""
        return GPUAllocationRequest(
            request_id=self.task_id,
            resource_name=self.resource_name,
            gpu_type=self.gpu_type,
            memory_mb=self.memory_mb,
            vgpu_count=self.vgpu_count,
            strategy=self.strategy,
            priority=self.priority.numeric_value,
        )


@dataclass
class SchedulingDecision:
    """Result of scheduling decision"""
    task_id: str
    scheduled: bool
    allocation_id: Optional[str] = None
    gpu_ids: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    estimated_start_time: Optional[datetime] = None
    queue_position: Optional[int] = None


@dataclass(order=True)
class QueuedTask:
    """Task in scheduling queue"""
    priority: int  # Lower number = higher priority (for heapq)
    submit_time: datetime
    task: GPUTask = field(compare=False)


class GPUScheduler:
    """
    GPU Scheduler

    Manages scheduling queue and allocation decisions for GPU resources.
    """

    def __init__(self, allocator: Optional[VGPUAllocator] = None):
        self.allocator = allocator or get_vgpu_allocator()
        self.pending_tasks: Dict[str, GPUTask] = {}
        self.running_tasks: Dict[str, GPUTask] = {}
        self.completed_tasks: Dict[str, GPUTask] = {}
        self.task_queue: List[QueuedTask] = []
        self.scheduling_policy = SchedulingPolicy.BEST_FIT
        self.enable_time_slicing = True  # Allow multiple time-sliced tasks on same GPU
        self.time_slice_minutes = 30  # Default time slice duration

    def submit_task(self, task: GPUTask) -> SchedulingDecision:
        """Submit a task for scheduling"""
        self.pending_tasks[task.task_id] = task

        # Add to priority queue
        priority_value = 100 - task.priority.numeric_value * 25  # Urgent=25, High=50, Normal=75, Low=100
        heapq.heappush(self.task_queue, QueuedTask(priority_value, task.submit_time, task))

        logger.info(f"Task {task.task_id} submitted with priority {task.priority}")

        # Try to schedule immediately
        return self._try_schedule_task(task)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        if task_id in self.pending_tasks:
            task = self.pending_tasks[task_id]

            # Remove from queue
            self.task_queue = [qt for qt in self.task_queue if qt.task.task_id != task_id]
            heapq.heapify(self.task_queue)

            del self.pending_tasks[task_id]
            logger.info(f"Task {task_id} cancelled")
            return True

        # Also check running tasks
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            # Deallocate GPU
            self.allocator.deallocate_by_resource(task_id)
            del self.running_tasks[task_id]
            self.completed_tasks[task_id] = task
            logger.info(f"Running task {task_id} cancelled and GPU deallocated")
            return True

        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        task = (
            self.pending_tasks.get(task_id)
            or self.running_tasks.get(task_id)
            or self.completed_tasks.get(task_id)
        )

        if not task:
            return None

        return {
            "task_id": task.task_id,
            "resource_name": task.resource_name,
            "vgpu_count": task.vgpu_count,
            "memory_mb": task.memory_mb,
            "priority": task.priority.value,
            "strategy": task.strategy.value,
            "status": "completed" if task.is_completed else "running" if task.is_running else "pending",
            "submit_time": task.submit_time.isoformat(),
            "scheduled_time": task.scheduled_time.isoformat() if task.scheduled_time else None,
            "started_time": task.started_time.isoformat() if task.started_time else None,
            "completed_time": task.completed_time.isoformat() if task.completed_time else None,
            "wait_time_seconds": task.wait_time_seconds,
            "run_time_seconds": task.run_time_seconds,
            "retry_count": task.retry_count,
        }

    def list_tasks(
        self,
        status: Optional[str] = None,
        resource_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filters"""
        all_tasks = {}

        if status == "pending" or status is None:
            all_tasks.update(self.pending_tasks)
        if status == "running" or status is None:
            all_tasks.update(self.running_tasks)
        if status == "completed" or status is None:
            all_tasks.update(self.completed_tasks)

        tasks = list(all_tasks.values())

        if resource_name:
            tasks = [t for t in tasks if t.resource_name == resource_name]

        return [self.get_task_status(t.task_id) for t in tasks if self.get_task_status(t.task_id)]

    def _try_schedule_task(self, task: GPUTask) -> SchedulingDecision:
        """Try to schedule a task immediately"""
        try:
            # Check constraints
            if task.allowed_gpu_ids:
                # Filter to allowed GPUs
                available_gpus = [
                    g
                    for g in self.allocator.list_gpus(task.gpu_type)
                    if g.gpu_id in task.allowed_gpu_ids and g.is_healthy
                ]
            elif task.forbidden_gpu_ids:
                # Filter out forbidden GPUs
                available_gpus = [
                    g
                    for g in self.allocator.list_gpus(task.gpu_type)
                    if g.gpu_id not in task.forbidden_gpu_ids and g.is_healthy
                ]
            else:
                available_gpus = [g for g in self.allocator.list_gpus(task.gpu_type) if g.is_healthy]

            if not available_gpus:
                return SchedulingDecision(
                    task_id=task.task_id,
                    scheduled=False,
                    reason="No suitable GPUs available (type or health constraints)",
                )

            # Try allocation
            allocation = self.allocator.allocate(task.to_allocation_request())

            # Task scheduled successfully
            task.scheduled_time = datetime.now()
            task.started_time = datetime.now()  # Auto-start for simplicity

            # Move to running
            del self.pending_tasks[task.task_id]
            self.running_tasks[task.task_id] = task

            logger.info(f"Task {task.task_id} scheduled on GPU(s): {allocation.gpu_id}")

            return SchedulingDecision(
                task_id=task.task_id,
                scheduled=True,
                allocation_id=allocation.allocation_id,
                gpu_ids=[allocation.gpu_id],
            )

        except ValueError as e:
            # Not enough resources
            queue_position = self._get_queue_position(task.task_id)

            # Estimate wait time based on queue
            estimated_wait = self._estimate_wait_time(task)
            estimated_start = datetime.now() + timedelta(seconds=estimated_wait) if estimated_wait else None

            return SchedulingDecision(
                task_id=task.task_id,
                scheduled=False,
                reason=str(e),
                estimated_start_time=estimated_start,
                queue_position=queue_position,
            )

    def _get_queue_position(self, task_id: str) -> int:
        """Get position of task in queue"""
        for i, qt in enumerate(self.task_queue):
            if qt.task.task_id == task_id:
                return i + 1
        return -1

    def _estimate_wait_time(self, task: GPUTask) -> Optional[float]:
        """Estimate wait time based on running tasks and queue"""
        # Simple estimate: sum of remaining times of higher priority tasks
        total_wait = 0.0

        for qt in self.task_queue:
            if qt.task.task_id == task.task_id:
                break
            if qt.task.estimated_duration_minutes:
                total_wait += qt.task.estimated_duration_minutes * 60

        # Add time for currently running tasks with same GPU requirements
        for running_task in self.running_tasks.values():
            if (
                running_task.gpu_type == task.gpu_type
                and running_task.estimated_duration_minutes
            ):
                elapsed = running_task.run_time_seconds
                total_duration = running_task.estimated_duration_minutes * 60
                remaining = max(0, total_duration - elapsed)
                total_wait += remaining

        return total_wait if total_wait > 0 else None

    def schedule_loop(self) -> List[SchedulingDecision]:
        """Run one iteration of the scheduling loop"""
        decisions = []

        # Process queue
        while self.task_queue:
            qt = self.task_queue[0]  # Peek at highest priority

            if qt.task.task_id not in self.pending_tasks:
                heapq.heappop(self.task_queue)  # Task no longer pending
                continue

            decision = self._try_schedule_task(qt.task)
            decisions.append(decision)

            if decision.scheduled:
                heapq.heappop(self.task_queue)  # Remove from queue
            else:
                # Can't schedule this task, stop processing
                break

        return decisions

    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """Mark a task as complete and release its resources"""
        if task_id not in self.running_tasks:
            return False

        task = self.running_tasks[task_id]
        task.completed_time = datetime.now()

        # Deallocate GPU
        allocated = self.allocator.deallocate_by_resource(task_id)

        # Move to completed
        del self.running_tasks[task_id]
        self.completed_tasks[task_id] = task

        logger.info(f"Task {task_id} completed (success={success}), deallocated {allocated} GPU(s)")

        # Try to schedule pending tasks
        self.schedule_loop()

        return True

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get scheduling queue statistics"""
        pending_count = len(self.pending_tasks)
        running_count = len(self.running_tasks)
        completed_count = len(self.completed_tasks)

        # Calculate average wait times
        avg_wait = 0.0
        if self.pending_tasks:
            avg_wait = sum(t.wait_time_seconds for t in self.pending_tasks.values()) / pending_count

        # Calculate average run times
        avg_run = 0.0
        if self.running_tasks:
            avg_run = sum(t.run_time_seconds for t in self.running_tasks.values()) / running_count

        # Priority breakdown
        pending_by_priority: Dict[str, int] = {}
        for task in self.pending_tasks.values():
            pending_by_priority[task.priority.value] = pending_by_priority.get(task.priority.value, 0) + 1

        return {
            "pending_tasks": pending_count,
            "running_tasks": running_count,
            "completed_tasks": completed_count,
            "avg_wait_time_seconds": avg_wait,
            "avg_run_time_seconds": avg_run,
            "pending_by_priority": pending_by_priority,
            "queue_depth": len(self.task_queue),
        }

    def set_scheduling_policy(self, policy: SchedulingPolicy) -> None:
        """Change the scheduling policy"""
        self.scheduling_policy = policy
        logger.info(f"Scheduling policy changed to {policy.value}")

    def cleanup_old_completed_tasks(self, older_than_hours: int = 24) -> int:
        """Remove completed tasks older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        to_remove = []

        for task_id, task in self.completed_tasks.items():
            if task.completed_time and task.completed_time < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.completed_tasks[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old completed tasks")

        return len(to_remove)


class GPUPoolManager:
    """
    GPU Pool Manager

    High-level management of GPU resources including scheduling and allocation.
    """

    def __init__(self):
        self.allocator = get_vgpu_allocator()
        self.scheduler = GPUScheduler(self.allocator)

    def request_gpu(
        self,
        resource_name: str,
        vgpu_count: int = 1,
        gpu_type: Optional[GPUType] = None,
        memory_mb: Optional[int] = None,
        strategy: GPUAllocationStrategy = GPUAllocationStrategy.EXCLUSIVE,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Request GPU allocation with automatic scheduling"""
        import uuid

        task = GPUTask(
            task_id=f"task-{uuid.uuid4()}",
            resource_name=resource_name,
            gpu_type=gpu_type,
            vgpu_count=vgpu_count,
            memory_mb=memory_mb,
            strategy=strategy,
            priority=priority,
            estimated_duration_minutes=estimated_duration_minutes,
        )

        decision = self.scheduler.submit_task(task)

        return {
            "task_id": task.task_id,
            "scheduled": decision.scheduled,
            "allocation_id": decision.allocation_id,
            "gpu_ids": decision.gpu_ids,
            "reason": decision.reason,
            "estimated_start_time": decision.estimated_start_time.isoformat() if decision.estimated_start_time else None,
            "queue_position": decision.queue_position,
        }

    def release_gpu(self, resource_name: str) -> bool:
        """Release GPU allocation for a resource"""
        return self.allocator.deallocate_by_resource(resource_name) > 0

    def get_pool_status(self) -> Dict[str, Any]:
        """Get overall GPU pool status"""
        return {
            "cluster_stats": self.allocator.get_cluster_gpu_stats(),
            "queue_stats": self.scheduler.get_queue_stats(),
            "gpus": [
                {
                    "gpu_id": g.gpu_id,
                    "name": g.name,
                    "type": g.gpu_type.value,
                    "total_memory_mb": g.total_memory_mb,
                    "used_memory_mb": g.memory_used_mb,
                    "utilization_percent": g.utilization_percent,
                    "temperature_celsius": g.temperature_celsius,
                    "healthy": g.is_healthy,
                    "vgpu_instances": len(g.vgpu_instances),
                    "active_vgpus": len([v for v in g.vgpu_instances if not v.is_available]),
                    "utilization_status": g.utilization_status,
                }
                for g in self.allocator.list_gpus()
            ],
            "allocations": [
                {
                    "allocation_id": a.allocation_id,
                    "resource_name": a.resource_name,
                    "gpu_id": a.gpu_id,
                    "vgpu_count": len(a.vgpu_ids),
                    "strategy": a.strategy.value,
                    "allocated_at": a.allocated_at.isoformat(),
                }
                for a in self.allocator.list_allocations()
            ],
        }

    def get_gpu_details(self, gpu_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific GPU"""
        gpu = self.allocator.get_gpu_status(gpu_id)
        if not gpu:
            return None

        vgpu_instances = []
        for vgpu in gpu.vgpu_instances:
            vgpu_instances.append({
                "vgpu_id": vgpu.vgpu_id,
                "memory_mb": vgpu.memory_mb,
                "allocated_to": vgpu.allocated_to,
                "allocated_at": vgpu.allocated_at.isoformat() if vgpu.allocated_at else None,
                "is_available": vgpu.is_available,
                "utilization_percent": vgpu.utilization_percent,
                "memory_used_mb": vgpu.memory_used_mb,
            })

        return {
            "gpu_id": gpu.gpu_id,
            "name": gpu.name,
            "type": gpu.gpu_type.value,
            "total_memory_mb": gpu.total_memory_mb,
            "used_memory_mb": gpu.memory_used_mb,
            "available_memory_mb": gpu.available_memory_mb,
            "cuda_cores": gpu.cuda_cores,
            "utilization_percent": gpu.utilization_percent,
            "temperature_celsius": gpu.temperature_celsius,
            "power_draw_watts": gpu.power_draw_watts,
            "healthy": gpu.is_healthy,
            "utilization_status": gpu.utilization_status,
            "driver_version": gpu.driver_version,
            "cuda_version": gpu.cuda_version,
            "max_vgpu_instances": gpu.max_vgpu_instances,
            "mig_enabled": gpu.mig_enabled,
            "vgpu_instances": vgpu_instances,
        }


# Global pool manager instance
_pool_manager: Optional[GPUPoolManager] = None


def get_gpu_pool_manager() -> GPUPoolManager:
    """Get the global GPU pool manager instance"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = GPUPoolManager()
    return _pool_manager
