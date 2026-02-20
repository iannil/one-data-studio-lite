"""Celery worker configuration for Smart Data Platform.

This module sets up the Celery application for distributed task processing,
replacing APScheduler for better scalability and reliability.

Usage:
    # Start worker
    celery -A app.celery_worker worker --loglevel=info

    # Start beat with custom scheduler (for dynamic schedules)
    celery -A app.celery_worker beat --loglevel=info \
        --scheduler=app.core.celery_beat_scheduler:RedisBeatScheduler

    # Start beat with standard scheduler
    celery -A app.celery_worker beat --loglevel=info
"""
from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "smart_data_platform",
    broker=settings.CELERY_BROKER_URL if hasattr(settings, 'CELERY_BROKER_URL') else settings.REDIS_URL + '/1',
    backend=settings.CELERY_RESULT_BACKEND if hasattr(settings, 'CELERY_RESULT_BACKEND') else settings.REDIS_URL + '/2',
    include=[
        "app.tasks.collect_tasks",
        "app.tasks.report_tasks",
        "app.tasks.etl_tasks",
        "app.tasks.system_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.tasks.collect_tasks.*": {"queue": "collect"},
        "app.tasks.report_tasks.*": {"queue": "report"},
        "app.tasks.etl_tasks.*": {"queue": "etl"},
        "app.tasks.system_tasks.*": {"queue": "system"},
    },
    # Task result expiry (24 hours)
    result_expires=86400,
    # Retry settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Rate limits
    task_annotations={
        "app.tasks.collect_tasks.execute_collect_task": {
            "rate_limit": "10/m",
        },
        "app.tasks.report_tasks.generate_scheduled_report": {
            "rate_limit": "20/m",
        },
    },
)

# Celery Beat schedule for periodic tasks
# Note: Dynamic schedules are stored in Redis and loaded by RedisBeatScheduler
celery_app.conf.beat_schedule = {
    # Daily cleanup of old task results (at 2 AM UTC)
    "cleanup-old-results": {
        "task": "app.tasks.system_tasks.cleanup_old_results",
        "schedule": crontab(hour=2, minute=0),
    },
    # Hourly health check for data sources
    "health-check-sources": {
        "task": "app.tasks.system_tasks.health_check_sources",
        "schedule": crontab(minute=0),  # Every hour
    },
}

# Optional: Configure worker settings for production
if os.getenv("ENVIRONMENT") == "production":
    celery_app.conf.update(
        worker_max_tasks_per_child=100,
        worker_concurrency=4,
    )

# Export for beat scheduler
__all__ = ["celery_app"]
