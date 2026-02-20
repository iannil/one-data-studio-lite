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


# Data Quality Schemas

class QualityScoreRequest(BaseModel):
    source_id: UUID
    table_name: str


class QualityScoreResponse(BaseModel):
    overall_score: float
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    consistency_score: float
    timeliness_score: float
    row_count: int
    column_count: int
    assessment: str


class QualityIssuesResponse(BaseModel):
    issues: dict[str, list[dict[str, Any]]]
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int


class QualityReportRequest(BaseModel):
    source_id: UUID
    table_name: str


class QualityReportResponse(BaseModel):
    table_name: str
    generated_at: str
    summary: dict[str, Any]
    issues: dict[str, list[dict[str, Any]]]
    trend: dict[str, Any]
    recommendations: list[dict[str, Any]]


class QualityTrendRequest(BaseModel):
    source_id: UUID
    table_name: str
    days: int = 30


class QualityTrendResponse(BaseModel):
    table_name: str
    period_days: int
    trend: list[dict[str, Any]]
    average_score: float
    trend_direction: str
