"""Celery Beat scheduler with persistent storage in Redis.

This module provides a custom scheduler that reads the beat schedule from Redis,
allowing dynamic schedule updates without restarting the Beat process.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from celery.beat import Scheduler, ScheduleEntry
from celery.schedules import schedule
from redis import Redis

from app.core.config import settings


class RedisBeatScheduler(Scheduler):
    """Celery Beat scheduler that stores schedule in Redis.

    This allows dynamic updates to the beat schedule without restarting
    the Celery Beat process.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._redis: Redis | None = None
        self._schedule_key = "celery:beat_schedule"
        self._last_sync: datetime | None = None

    @property
    def redis(self) -> Redis:
        """Lazy load Redis client."""
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.CELERY_BROKER_URL if hasattr(settings, 'CELERY_BROKER_URL')
                else settings.REDIS_URL + '/1',
                decode_responses=True
            )
        return self._redis

    def setup_schedule(self) -> None:
        """Load schedule from Redis and merge with static schedule."""
        super().setup_schedule()
        self._load_from_redis()

    def _load_from_redis(self) -> None:
        """Load dynamic schedule entries from Redis."""
        try:
            data = self.redis.get(self._schedule_key)
            if data:
                dynamic_schedule = json.loads(data)
                for name, entry_def in dynamic_schedule.items():
                    if name not in self.data:
                        self._add_entry(name, entry_def)
                self._last_sync = datetime.now()
                self.logger.info(f"Loaded {len(dynamic_schedule)} entries from Redis")
        except Exception as e:
            self.logger.error(f"Failed to load schedule from Redis: {e}")

    def _add_entry(self, name: str, entry_def: dict[str, Any]) -> None:
        """Add a schedule entry from definition."""
        try:
            task = entry_def.get("task", "")
            schedule_def = entry_def.get("schedule", {})
            args = entry_def.get("args", [])
            kwargs = entry_def.get("kwargs", {})
            options = entry_def.get("options", {})

            # Parse schedule
            if isinstance(schedule_def, dict):
                # Crontab schedule
                from celery.schedules import crontab
                s = crontab(**schedule_def)
            else:
                # Already a schedule object or string
                s = schedule_def

            entry = ScheduleEntry(
                name=name,
                task=task,
                schedule=s,
                args=args,
                kwargs=kwargs,
                options=options,
            )
            self.data[name] = entry
        except Exception as e:
            self.logger.error(f"Failed to add entry {name}: {e}")

    def sync(self) -> None:
        """Sync schedule from Redis periodically."""
        super().sync()
        # Reload from Redis every 60 seconds
        if self._last_sync is None or (datetime.now() - self._last_sync) > timedelta(seconds=60):
            self._load_from_redis()

    def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            self._redis.close()
        super().close()
