from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class OCRProcessRequest(BaseModel):
    """Request for processing a single document."""

    extract_structured: bool = Field(
        default=True,
        description="Whether to extract structured data using AI",
    )


class OCRProcessResponse(BaseModel):
    """Response from OCR processing."""

    file_name: str
    file_type: str
    raw_text: str
    structured_data: Optional[dict[str, Any]] = None
    status: str = "success"
    error: Optional[str] = None


class OCRBatchResponse(BaseModel):
    """Response from batch OCR processing."""

    results: list[OCRProcessResponse]
    total: int
    successful: int
    failed: int


class SupportedTypesResponse(BaseModel):
    """Response listing supported file types."""

    supported_types: list[str]
    descriptions: dict[str, str]
