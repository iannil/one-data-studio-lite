from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from app.core.config import settings


def create_scheduler() -> AsyncIOScheduler:
    jobstores = {
        "default": RedisJobStore(
            host=settings.REDIS_URL.split("://")[1].split(":")[0],
            port=int(settings.REDIS_URL.split(":")[-1].split("/")[0]),
            db=int(settings.REDIS_URL.split("/")[-1]),
        )
    }

    executors = {
        "default": ThreadPoolExecutor(20),
        "processpool": ProcessPoolExecutor(5),
    }

    job_defaults = {
        "coalesce": False,
        "max_instances": 3,
    }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",
    )

    return scheduler


scheduler = create_scheduler()
