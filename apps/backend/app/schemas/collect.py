from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.collect import CollectTaskStatus


class CollectTaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_id: UUID
    source_table: str | None = None
    source_query: str | None = None
    target_table: str
    schedule_cron: str | None = None
    is_incremental: bool = False
    incremental_field: str | None = None
    column_mapping: dict[str, Any] | None = None


class CollectTaskCreate(CollectTaskBase):
    pass


class CollectTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_table: str | None = None
    source_query: str | None = None
    target_table: str | None = None
    schedule_cron: str | None = None
    is_active: bool | None = None
    is_incremental: bool | None = None
    incremental_field: str | None = None
    column_mapping: dict[str, Any] | None = None


class CollectTaskResponse(CollectTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    status: CollectTaskStatus
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_sync_value: str | None
    last_error: str | None
    created_at: datetime
    created_by: UUID | None


class CollectExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    status: CollectTaskStatus
    started_at: datetime
    completed_at: datetime | None
    rows_processed: int
    rows_inserted: int
    rows_updated: int
    error_message: str | None


class CollectRunRequest(BaseModel):
    force_full_sync: bool = False
