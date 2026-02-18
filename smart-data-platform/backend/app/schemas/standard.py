"""Pydantic schemas for data standard management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StandardRules(BaseModel):
    """Base rules schema for data standards."""
    pattern: str | None = None
    format: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    allowed_values: list[str] | None = None
    range: dict[str, float] | None = None
    encoding: str | None = None
    completeness: float | None = None
    uniqueness: bool | None = None
    not_null: bool | None = None
    precision: int | None = None


class StandardCreate(BaseModel):
    """Schema for creating a new data standard."""
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str | None = None
    standard_type: str = Field(..., pattern=r"^(field_format|encoding_rule|naming_convention|value_domain|data_quality)$")
    rules: dict[str, Any] = Field(default_factory=dict)
    applicable_domains: list[str] = Field(default_factory=list)
    applicable_data_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    department: str | None = None


class StandardUpdate(BaseModel):
    """Schema for updating a data standard."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    rules: dict[str, Any] | None = None
    applicable_domains: list[str] | None = None
    applicable_data_types: list[str] | None = None
    tags: list[str] | None = None
    department: str | None = None


class StandardResponse(BaseModel):
    """Schema for data standard response."""
    id: uuid.UUID
    name: str
    code: str
    description: str | None
    standard_type: str
    status: str
    rules: dict[str, Any]
    applicable_domains: list[str]
    applicable_data_types: list[str]
    tags: list[str]
    owner_id: uuid.UUID | None
    department: str | None
    ai_suggested: bool
    ai_confidence: float | None
    version: int
    previous_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    approved_by: uuid.UUID | None

    class Config:
        from_attributes = True


class StandardSuggestionRequest(BaseModel):
    """Schema for requesting AI standard suggestions."""
    source_id: uuid.UUID
    table_name: str


class StandardSuggestionColumn(BaseModel):
    """Schema for suggested standard on a column."""
    type: str
    name: str
    code: str
    description: str | None
    rules: dict[str, Any]
    confidence: float


class ColumnSuggestion(BaseModel):
    """Schema for column-level suggestions."""
    column_name: str
    suggested_standards: list[StandardSuggestionColumn]
    detected_type: str | None
    notes: str | None


class StandardSuggestionResponse(BaseModel):
    """Schema for AI standard suggestion response."""
    source_id: str
    table_name: str
    columns_analyzed: int
    suggestions: dict[str, Any]


class ComplianceCheckRequest(BaseModel):
    """Schema for requesting compliance check."""
    standard_id: uuid.UUID
    source_id: uuid.UUID | None = None
    table_name: str | None = None
    column_name: str | None = None


class ComplianceCheckResponse(BaseModel):
    """Schema for compliance check response."""
    id: uuid.UUID
    standard_id: uuid.UUID
    source_id: uuid.UUID | None
    table_name: str | None
    column_name: str | None
    is_compliant: bool
    compliance_score: float
    total_records: int
    compliant_records: int
    violation_records: int
    violations: dict[str, Any]
    checked_at: datetime
    check_duration_ms: int | None

    class Config:
        from_attributes = True


class ApplyStandardRequest(BaseModel):
    """Schema for applying a standard to a target."""
    standard_id: uuid.UUID
    target_type: str = Field(..., pattern=r"^(table|column|asset)$")
    source_id: uuid.UUID | None = None
    table_name: str | None = None
    column_name: str | None = None
    asset_id: uuid.UUID | None = None
    is_mandatory: bool = False


class StandardApplicationResponse(BaseModel):
    """Schema for standard application response."""
    id: uuid.UUID
    standard_id: uuid.UUID
    target_type: str
    source_id: uuid.UUID | None
    table_name: str | None
    column_name: str | None
    asset_id: uuid.UUID | None
    is_mandatory: bool
    is_active: bool
    applied_at: datetime
    applied_by: uuid.UUID | None

    class Config:
        from_attributes = True


class CreateVersionRequest(BaseModel):
    """Schema for creating a new standard version."""
    updated_rules: dict[str, Any]


class StandardListResponse(BaseModel):
    """Schema for listing standards."""
    items: list[StandardResponse]
    total: int


class ComplianceHistoryResponse(BaseModel):
    """Schema for compliance history."""
    items: list[ComplianceCheckResponse]
    total: int
