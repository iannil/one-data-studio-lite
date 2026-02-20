"""Celery monitoring and management API endpoints.

This module provides REST endpoints for monitoring Celery workers,
tasks, and schedules.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import User

router = APIRouter()

USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"


class CeleryStatusResponse(BaseModel):
    """Response model for Celery status check."""

    enabled: bool
    workers_online: int
    tasks_active: int
    tasks_scheduled: int
    queues: dict[str, dict[str, Any]]
    beat_running: bool


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    status: str
    result: dict[str, Any] | None
    error: str | None
    started_at: str | None
    completed_at: str | None


class WorkerInfo(BaseModel):
    """Information about a Celery worker."""

    name: str
    pools: list[str]
    concurrency: int
    max_tasks_per_child: int | None
    active_tasks: int
    scheduled_tasks: int


@router.get("/status", response_model=CeleryStatusResponse)
async def get_celery_status(
    current_user: User = Depends(get_current_user),
) -> CeleryStatusResponse:
    """Get current Celery cluster status.

    Returns information about workers, tasks, and queues.
    """
    if not USE_CELERY:
        return CeleryStatusResponse(
            enabled=False,
            workers_online=0,
            tasks_active=0,
            tasks_scheduled=0,
            queues={},
            beat_running=False,
        )

    from app.celery_worker import celery_app

    inspect = celery_app.control.inspect()
    stats = inspect.stats() or {}
    active = inspect.active() or {}
    scheduled = inspect.scheduled() or {}
    reserved = inspect.reserved() or {}

    # Count workers
    workers_online = len(stats)

    # Count tasks
    tasks_active = sum(len(tasks) for tasks in active.values())
    tasks_scheduled = sum(len(tasks) for tasks in scheduled.values())
    tasks_reserved = sum(len(tasks) for tasks in reserved.values())

    # Get queue info
    queues = {}
    for worker_name, worker_stats in stats.items():
        for queue_name, queue_stats in worker_stats.get("rusage", {}).items():
            if queue_name not in queues:
                queues[queue_name] = {
                    "pending": 0,
                    "processing": 0,
                }
            queues[queue_name]["processing"] += queue_stats.get("processing", 0)

    # Check if beat is running (heuristic: check for beat-related tasks)
    beat_running = any(
        "celery.beat" in worker_name.lower()
        for worker_name in stats.keys()
    )

    return CeleryStatusResponse(
        enabled=True,
        workers_online=workers_online,
        tasks_active=tasks_active + tasks_reserved,
        tasks_scheduled=tasks_scheduled,
        queues=queues,
        beat_running=beat_running,
    )


@router.get("/workers", response_model=list[WorkerInfo])
async def get_workers(
    current_user: User = Depends(get_current_user),
) -> list[WorkerInfo]:
    """Get information about all Celery workers."""
    if not USE_CELERY:
        return []

    from app.celery_worker import celery_app

    inspect = celery_app.control.inspect()
    stats = inspect.stats() or {}
    active = inspect.active() or {}
    scheduled = inspect.scheduled() or {}
    reserved = inspect.reserved() or {}

    workers = []
    for worker_name, worker_stats in stats.items():
        # Extract pool info
        pool = worker_stats.get("pool", {})
        pools = [pool.get("type", "prefork")] if pool else ["prefork"]

        # Get concurrency
        concurrency = pool.get("max-concurrency", 0)

        # Get max tasks per child
        max_tasks = pool.get("max-tasks-per-child")

        # Count tasks
        active_tasks = len(active.get(worker_name, []))
        scheduled_tasks = len(scheduled.get(worker_name, [])) + len(reserved.get(worker_name, []))

        workers.append(
            WorkerInfo(
                name=worker_name,
                pools=pools,
                concurrency=concurrency,
                max_tasks_per_child=max_tasks,
                active_tasks=active_tasks,
                scheduled_tasks=scheduled_tasks,
            )
        )

    return workers


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get status of a specific Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status information
    """
    if not USE_CELERY:
        return {"error": "Celery is not enabled"}

    from app.celery_worker import celery_app

    result = celery_app.AsyncResult(task_id)

    response: dict[str, Any] = {
        "task_id": task_id,
        "status": result.state,
        "result": None,
        "error": None,
        "started_at": None,
        "completed_at": None,
    }

    if result.successful():
        response["result"] = result.result
        response["completed_at"] = result.date_done
    elif result.failed():
        response["error"] = str(result.info)
        response["completed_at"] = result.date_done
    elif result.state == "PROGRESS":
        response["result"] = result.info or {}
    elif result.state == "PENDING":
        response["result"] = None

    return response


@router.post("/task/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancel a running Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        Cancellation result
    """
    if not USE_CELERY:
        return {"error": "Celery is not enabled"}

    from app.celery_worker import celery_app

    celery_app.control.revoke(task_id, terminate=True)

    return {
        "task_id": task_id,
        "cancelled": True,
        "message": "Task cancellation requested",
    }


@router.post("/worker/shutdown")
async def shutdown_workers(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Shutdown all Celery workers.

    This action requires admin privileges.
    """
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only admins can shutdown workers")

    if not USE_CELERY:
        return {"error": "Celery is not enabled"}

    from app.celery_worker import celery_app

    # Send shutdown signal to all workers
    celery_app.control.broadcast("shutdown")

    return {
        "message": "Shutdown signal sent to all workers",
        "workers": "all",
    }


@router.post("/worker/pool/restart")
async def restart_worker_pools(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Restart worker pools.

    This action requires admin privileges.
    """
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only admins can restart workers")

    if not USE_CELERY:
        return {"error": "Celery is not enabled"}

    from app.celery_worker import celery_app

    # Send pool restart signal
    celery_app.control.broadcast("pool_restart")

    return {
        "message": "Pool restart signal sent to all workers",
        "workers": "all",
    }


@router.get("/queues")
async def get_queue_lengths(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current queue lengths.

    Returns the number of pending tasks in each queue.
    """
    if not USE_CELERY:
        return {"error": "Celery is not enabled"}

    from redis import Redis

    redis_client = Redis.from_url(
        settings.CELERY_BROKER_URL
        if hasattr(settings, "CELERY_BROKER_URL")
        else settings.REDIS_URL + "/1"
    )

    queues = {
        "collect": 0,
        "report": 0,
        "etl": 0,
        "system": 0,
    }

    # Get queue lengths from Redis
    for queue_name in queues.keys():
        queue_key = f"celery:{queue_name}"
        try:
            length = redis_client.llen(queue_key)
            queues[queue_name] = length
        except Exception:
            pass

    redis_client.close()

    return {
        "queues": queues,
        "total": sum(queues.values()),
    }


@router.get("/flower/url")
async def get_flower_url(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the Flower monitoring URL.

    Returns the configured Flower URL for direct access.
    """
    flower_url = os.getenv("FLOWER_URL", "http://localhost:5507")

    return {
        "url": flower_url,
        "enabled": USE_CELERY,
    }
