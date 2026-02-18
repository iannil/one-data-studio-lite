from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.etl import ETLStepType, ExecutionStatus, PipelineStatus


class ETLStepBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    step_type: ETLStepType
    config: dict[str, Any]
    order: int
    is_enabled: bool = True
    description: str | None = None


class ETLStepCreate(ETLStepBase):
    pass


class ETLStepUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    order: int | None = None
    is_enabled: bool | None = None
    description: str | None = None


class ETLStepResponse(ETLStepBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID


class ETLPipelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_type: str
    source_config: dict[str, Any]
    target_type: str
    target_config: dict[str, Any]
    schedule_cron: str | None = None
    is_scheduled: bool = False
    tags: list[str] = []


class ETLPipelineCreate(ETLPipelineBase):
    steps: list[ETLStepCreate] = []


class ETLPipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_config: dict[str, Any] | None = None
    target_config: dict[str, Any] | None = None
    schedule_cron: str | None = None
    is_scheduled: bool | None = None
    status: PipelineStatus | None = None
    tags: list[str] | None = None


class ETLPipelineResponse(ETLPipelineBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: PipelineStatus
    version: int
    created_at: datetime
    created_by: UUID | None
    steps: list[ETLStepResponse] = []
    # Last execution info
    last_execution_status: ExecutionStatus | None = None
    last_run_at: datetime | None = None


class ETLExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_id: UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    rows_input: int
    rows_output: int
    rows_error: int
    error_message: str | None
    step_metrics: dict[str, Any] | None


class ETLRunRequest(BaseModel):
    preview_mode: bool = False
    preview_rows: int = 100


class ETLPreviewResponse(BaseModel):
    columns: list[str]
    data: list[dict[str, Any]]
    row_count: int


# AI-related
class AICleaningRule(BaseModel):
    step_type: ETLStepType
    config: dict[str, Any]
    reason: str
    confidence: float


class AISuggestRulesRequest(BaseModel):
    source_id: UUID
    table_name: str
    sample_size: int = 1000


class AISuggestRulesResponse(BaseModel):
    suggestions: list[AICleaningRule]
    data_quality_summary: dict[str, Any]


class AIPredictFillRequest(BaseModel):
    source_id: UUID
    table_name: str
    target_column: str
    feature_columns: list[str]


class AIPredictFillResponse(BaseModel):
    model_type: str
    accuracy: float | None
    filled_count: int
    preview: list[dict[str, Any]]
