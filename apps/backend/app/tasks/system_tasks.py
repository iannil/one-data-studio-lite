"""Celery tasks for system maintenance operations.

This module contains system maintenance tasks like cleanup,
health checks, and monitoring.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from app.celery_worker import celery_app
from app.core.database import AsyncSessionLocal
from app.models import AuditLog, ETLExecution, CollectExecution
from sqlalchemy import delete


@celery_app.task(name="system.cleanup_old_results")
def cleanup_old_results(days: int = 7) -> dict[str, Any]:
    """Clean up old Celery task results from the database.

    Args:
        days: Delete results older than this many days.

    Returns:
        Cleanup summary.
    """
    import asyncio

    async def _cleanup() -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with AsyncSessionLocal() as db:
            # Clean up old audit logs (optional - for compliance you may want to keep these)
            audit_result = await db.execute(
                delete(AuditLog).where(AuditLog.timestamp < cutoff)
            )
            audit_deleted = audit_result.rowcount

            # Clean up old ETL executions that are not the latest
            etl_result = await db.execute(
                delete(ETLExecution).where(
                    ETLExecution.created_at < cutoff,
                    ETLExecution.status.in_(["success", "failed", "cancelled"]),
                )
            )
            etl_deleted = etl_result.rowcount

            # Clean up old collect executions
            collect_result = await db.execute(
                delete(CollectExecution).where(
                    CollectExecution.created_at < cutoff,
                    CollectExecution.status.in_(["success", "failed"]),
                )
            )
            collect_deleted = collect_result.rowcount

            await db.commit()

            return {
                "status": "success",
                "cutoff_date": cutoff.isoformat(),
                "audit_logs_deleted": audit_deleted,
                "etl_executions_deleted": etl_deleted,
                "collect_executions_deleted": collect_deleted,
                "total_deleted": audit_deleted + etl_deleted + collect_deleted,
            }

    return asyncio.run(_cleanup())


@celery_app.task(name="system.health_check_sources")
def health_check_sources() -> dict[str, Any]:
    """Health check for all data sources.

    Returns:
        Health check summary for all sources.
    """
    from app.tasks.collect_tasks import health_check_sources
    return health_check_sources()


@celery_app.task(name="system.disk_usage_report")
def disk_usage_report() -> dict[str, Any]:
    """Generate a disk usage report for system monitoring.

    Returns:
        Disk usage statistics.
    """
    import shutil
    import os

    def get_disk_usage(path: str) -> dict[str, Any]:
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round(usage.used / usage.total * 100, 2),
        }

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disk_usage": {},
    }

    # Check common paths
    paths_to_check = [
        "/",
        "/var",
        "/tmp",
        os.environ.get("HOME", "/root"),
    ]

    for path in paths_to_check:
        if os.path.exists(path):
            try:
                report["disk_usage"][path] = get_disk_usage(path)
            except Exception:
                pass

    return report


@celery_app.task(name="system.task_monitor")
def task_monitor() -> dict[str, Any]:
    """Monitor active Celery tasks and report statistics.

    Returns:
        Task monitoring statistics.
    """
    from celery import current_app

    inspect = current_app.control.inspect()
    stats = inspect.stats()
    active = inspect.active()
    scheduled = inspect.scheduled()
    reserved = inspect.reserved()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workers": stats if stats else {},
        "active_tasks": active if active else {},
        "scheduled_tasks": scheduled if scheduled else {},
        "reserved_tasks": reserved if reserved else {},
    }
