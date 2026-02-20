# Quality API endpoints

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DBSession
from app.schemas import (
    QualityScoreRequest,
    QualityScoreResponse,
    QualityIssuesResponse,
    QualityReportRequest,
    QualityReportResponse,
    QualityTrendRequest,
    QualityTrendResponse,
)
from app.services import DataQualityService

router = APIRouter(prefix="/quality", tags=["Quality"])


@router.post("/score", response_model=QualityScoreResponse)
async def calculate_quality_score(
    request: QualityScoreRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityScoreResponse:
    """Calculate quality score for a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.calculate_quality_score(
        request.source_id,
        request.table_name,
    )
    return QualityScoreResponse(**result)


@router.post("/issues", response_model=QualityIssuesResponse)
async def detect_quality_issues(
    request: QualityScoreRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityIssuesResponse:
    """Detect data quality issues in a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.detect_quality_issues(
        request.source_id,
        request.table_name,
    )
    return QualityIssuesResponse(**result)


@router.post("/report", response_model=QualityReportResponse)
async def generate_quality_report(
    request: QualityReportRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityReportResponse:
    """Generate comprehensive quality report for a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.generate_quality_report(
        request.source_id,
        request.table_name,
    )
    return QualityReportResponse(**result)


@router.post("/trend", response_model=QualityTrendResponse)
async def get_quality_trend(
    request: QualityTrendRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityTrendResponse:
    """Get quality trend over time."""
    quality_service = DataQualityService(db)
    # TODO: Map source_id + table_name to asset_id for historical data
    # For now, pass None to return trend summary without historical data
    result = await quality_service.track_quality_trend(
        asset_id=None,
        days=request.days,
    )
    return QualityTrendResponse(**result)
