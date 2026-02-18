from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NLQueryRequest(BaseModel):
    query: str
    context_tables: list[str] | None = None
    limit: int = 100


class NLQueryResponse(BaseModel):
    sql: str
    data: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    visualization_suggestion: dict[str, Any] | None = None
    explanation: str | None = None


class AIFieldAnalysisRequest(BaseModel):
    source_id: UUID
    table_name: str


class AIFieldAnalysisResponse(BaseModel):
    table_id: UUID
    columns_analyzed: int
    results: list[dict[str, Any]]


class AIDataQualityRequest(BaseModel):
    source_id: UUID
    table_name: str
    sample_size: int = 10000


class AIDataQualityResponse(BaseModel):
    overall_score: float
    issues: list[dict[str, Any]]
    recommendations: list[str]
    column_statistics: dict[str, Any]


class PredictionRequest(BaseModel):
    model_type: str  # timeseries, classification, clustering
    source_table: str
    target_column: str | None = None
    feature_columns: list[str] = []
    config: dict[str, Any] = {}


class PredictionResponse(BaseModel):
    prediction_id: UUID
    model_type: str
    results: list[dict[str, Any]]
    metrics: dict[str, Any] | None = None
    visualization: dict[str, Any] | None = None
