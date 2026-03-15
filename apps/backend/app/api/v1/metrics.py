"""
Metric and Dimension Management API Endpoints

Provides REST API for defining and calculating business metrics.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.metric.metric_service import (
    get_metric_manager,
    get_dimension_manager,
    MetricType,
    AggregationType,
    MetricStatus,
    Dimension,
    Metric,
    MetricValue,
    MetricCalculationResult,
    MetricLineage,
    MetricExplainer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


# ============================================================================
# Request/Response Models
# ============================================================================


class DimensionCreateRequest(BaseModel):
    """Request to create a dimension"""
    name: str
    table_name: str
    column_name: str
    data_type: str
    description: Optional[str] = None
    is_hierarchy: bool = False
    parent_dimension_id: Optional[str] = None
    level: int = 0
    tags: List[str] = []


class DimensionResponse(BaseModel):
    """Dimension response"""
    id: str
    name: str
    table_name: str
    column_name: str
    data_type: str
    description: Optional[str]
    is_hierarchy: bool
    parent_dimension_id: Optional[str]
    level: int
    created_at: str


class MetricCreateRequest(BaseModel):
    """Request to create a metric"""
    name: str
    display_name: str
    metric_type: MetricType
    table_name: str
    column_name: Optional[str] = None
    description: Optional[str] = None
    filter_condition: Optional[str] = None
    expression: Optional[str] = None
    dimensions: List[str] = []
    is_time_series: bool = False
    time_column: Optional[str] = None
    tags: List[str] = []


class MetricResponse(BaseModel):
    """Metric response"""
    id: str
    name: str
    display_name: str
    metric_type: str
    table_name: str
    column_name: Optional[str]
    description: Optional[str]
    dimensions: List[str]
    is_time_series: bool
    time_column: Optional[str]
    status: str
    created_at: str


class MetricCalculateRequest(BaseModel):
    """Request to calculate a metric"""
    metric_id: str
    dimensions: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    aggregation: Optional[AggregationType] = None


class MetricCalculateResponse(BaseModel):
    """Metric calculation response"""
    metric_id: str
    metric_name: str
    values: List[Dict[str, Any]]
    total: Optional[float]
    execution_time_ms: float
    row_count: int
    error: Optional[str]


class MetricLineageResponse(BaseModel):
    """Metric lineage response"""
    metric_id: str
    upstream_tables: List[str]
    upstream_metrics: List[str]
    downstream_metrics: List[str]
    downstream_tables: List[str]


# ============================================================================
# Dimension Endpoints
# ============================================================================


@router.post("/dimensions", response_model=DimensionResponse)
async def create_dimension(
    data: DimensionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new dimension"""
    manager = get_dimension_manager(db)

    dimension = manager.create_dimension(
        name=data.name,
        table_name=data.table_name,
        column_name=data.column_name,
        data_type=data.data_type,
        description=data.description,
        is_hierarchy=data.is_hierarchy,
        parent_dimension_id=data.parent_dimension_id,
        level=data.level,
        user_id=str(current_user.id),
        tags=data.tags,
    )

    return DimensionResponse(
        id=dimension.id,
        name=dimension.name,
        table_name=dimension.table_name,
        column_name=dimension.column_name,
        data_type=dimension.data_type,
        description=dimension.description,
        is_hierarchy=dimension.is_hierarchy,
        parent_dimension_id=dimension.parent_dimension_id,
        level=dimension.level,
        created_at=dimension.created_at.isoformat(),
    )


@router.get("/dimensions", response_model=List[DimensionResponse])
async def list_dimensions(
    table_name: Optional[str] = None,
    is_hierarchy: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all dimensions"""
    manager = get_dimension_manager(db)

    dimensions = manager.list_dimensions(
        table_name=table_name,
        is_hierarchy=is_hierarchy,
        limit=limit,
    )

    return [
        DimensionResponse(
            id=d.id,
            name=d.name,
            table_name=d.table_name,
            column_name=d.column_name,
            data_type=d.data_type,
            description=d.description,
            is_hierarchy=d.is_hierarchy,
            parent_dimension_id=d.parent_dimension_id,
            level=d.level,
            created_at=d.created_at.isoformat(),
        )
        for d in dimensions
    ]


@router.get("/dimensions/{dimension_id}/values")
async def get_dimension_values(
    dimension_id: str,
    limit: int = Query(1000, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get distinct values for a dimension"""
    manager = get_dimension_manager(db)

    values = manager.get_dimension_values(
        dimension_id=dimension_id,
        limit=limit,
    )

    return {
        "dimension_id": dimension_id,
        "values": values,
    }


@router.get("/dimensions/{dimension_id}/hierarchy")
async def get_dimension_hierarchy(
    dimension_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get hierarchy for a dimension"""
    manager = get_dimension_manager(db)

    hierarchy = manager.get_dimension_hierarchy(dimension_id)

    return {
        "dimension_id": dimension_id,
        "hierarchy": hierarchy,
    }


# ============================================================================
# Metric Endpoints
# ============================================================================


@router.post("/metrics", response_model=MetricResponse)
async def create_metric(
    data: MetricCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new metric"""
    manager = get_metric_manager(db)

    metric = manager.create_metric(
        name=data.name,
        display_name=data.display_name,
        metric_type=data.metric_type,
        table_name=data.table_name,
        column_name=data.column_name,
        description=data.description,
        filter_condition=data.filter_condition,
        expression=data.expression,
        dimensions=data.dimensions,
        is_time_series=data.is_time_series,
        time_column=data.time_column,
        owner_id=str(current_user.id),
        tags=data.tags,
    )

    return MetricResponse(
        id=metric.id,
        name=metric.name,
        display_name=metric.display_name,
        metric_type=metric.metric_type.value,
        table_name=metric.table_name,
        column_name=metric.column_name,
        description=metric.description,
        dimensions=metric.dimensions,
        is_time_series=metric.is_time_series,
        time_column=metric.time_column,
        status=metric.status.value,
        created_at=metric.created_at.isoformat(),
    )


@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    status: Optional[MetricStatus] = None,
    owner_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all metrics"""
    manager = get_metric_manager(db)

    metrics = manager.list_metrics(
        status=status,
        owner_id=owner_id,
        tags=tags,
        limit=limit,
    )

    return [
        MetricResponse(
            id=m.id,
            name=m.name,
            display_name=m.display_name,
            metric_type=m.metric_type.value,
            table_name=m.table_name,
            column_name=m.column_name,
            description=m.description,
            dimensions=m.dimensions,
            is_time_series=m.is_time_series,
            time_column=m.time_column,
            status=m.status.value,
            created_at=m.created_at.isoformat(),
        )
        for m in metrics
    ]


@router.get("/metrics/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a metric by ID"""
    manager = get_metric_manager(db)
    metric = manager.get_metric(metric_id)

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    return MetricResponse(
        id=metric.id,
        name=metric.name,
        display_name=metric.display_name,
        metric_type=metric.metric_type.value,
        table_name=metric.table_name,
        column_name=metric.column_name,
        description=metric.description,
        dimensions=metric.dimensions,
        is_time_series=metric.is_time_series,
        time_column=metric.time_column,
        status=metric.status.value,
        created_at=metric.created_at.isoformat(),
    )


@router.put("/metrics/{metric_id}")
async def update_metric(
    metric_id: str,
    display_name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    expression: Optional[str] = Body(None),
    status: Optional[MetricStatus] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a metric"""
    manager = get_metric_manager(db)

    metric = manager.update_metric(
        metric_id=metric_id,
        display_name=display_name,
        description=description,
        expression=expression,
        status=status,
        tags=tags,
    )

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    return {"success": True, "message": "Metric updated"}


@router.delete("/metrics/{metric_id}")
async def delete_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a metric"""
    manager = get_metric_manager(db)
    success = manager.delete_metric(metric_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    return {"success": True, "message": "Metric deleted"}


# ============================================================================
# Metric Calculation Endpoints
# ============================================================================


@router.post("/metrics/calculate", response_model=MetricCalculateResponse)
async def calculate_metric(
    request: MetricCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate a metric"""
    manager = get_metric_manager(db)

    start_date = datetime.fromisoformat(request.start_date) if request.start_date else None
    end_date = datetime.fromisoformat(request.end_date) if request.end_date else None

    result = manager.calculate_metric(
        metric_id=request.metric_id,
        dimensions=request.dimensions,
        start_date=start_date,
        end_date=end_date,
        aggregation=request.aggregation,
    )

    return MetricCalculateResponse(
        metric_id=result.metric_id,
        metric_name=result.metric_name,
        values=[{
            "metric_id": v.metric_id,
            "value": float(v.value) if isinstance(v.value, (int, float)) else str(v.value),
            "dimensions": v.dimensions,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
        } for v in result.values],
        total=float(result.total) if result.total is not None else None,
        execution_time_ms=result.execution_time_ms,
        row_count=result.row_count,
        error=result.error,
    )


@router.post("/metrics/calculate/batch")
async def calculate_multiple_metrics(
    metric_ids: List[str] = Body(..., embed=True),
    start_date: Optional[str] = Body(None),
    end_date: Optional[str] = Body(None),
    aggregation: Optional[AggregationType] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate multiple metrics"""
    manager = get_metric_manager(db)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    results = manager.calculate_multiple_metrics(
        metric_ids=metric_ids,
        start_date=start,
        end_date=end,
        aggregation=aggregation,
    )

    return {
        "results": [
            {
                "metric_id": r.metric_id,
                "metric_name": r.metric_name,
                "total": float(r.total) if r.total is not None else None,
                "row_count": r.row_count,
                "error": r.error,
            }
            for r in results
        ]
    }


# ============================================================================
# Metric Lineage Endpoints
# ============================================================================


@router.get("/metrics/{metric_id}/lineage", response_model=MetricLineageResponse)
async def get_metric_lineage(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get lineage information for a metric"""
    manager = get_metric_manager(db)

    lineage = manager.get_metric_lineage(metric_id)

    return MetricLineageResponse(
        metric_id=lineage.metric_id,
        upstream_tables=lineage.upstream_tables,
        upstream_metrics=lineage.upstream_metrics,
        downstream_metrics=lineage.downstream_metrics,
        downstream_tables=lineage.downstream_tables,
    )


@router.post("/lineage/analyze-impact")
async def analyze_impact(
    table_name: str,
    column_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze impact of a table/column change on metrics"""
    manager = get_metric_manager(db)

    impact = manager.analyze_impact(
        table_name=table_name,
        column_name=column_name,
    )

    return impact


# ============================================================================
# Metric Explanation Endpoints
# ============================================================================


@router.get("/metrics/{metric_id}/explain")
async def explain_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a human-readable explanation of a metric"""
    manager = get_metric_manager(db)
    metric = manager.get_metric(metric_id)

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    explanation = MetricExplainer.explain_metric(metric)
    return explanation
