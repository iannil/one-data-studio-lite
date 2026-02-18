"""Data lineage API endpoints."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models import User
from app.services.lineage_service import LineageService
from app.services.ai_service import AIService
from app.schemas.lineage import (
    LineageGraphResponse,
    AssetLineageRequest,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    BuildLineageRequest,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])


class DiscoverRelationsRequest(BaseModel):
    """Request for discovering cross-source relations."""
    source_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of source IDs to analyze"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to include"
    )


class RelationColumn(BaseModel):
    """Column in a discovered relation."""
    source_id: str
    source_name: str
    table_name: str
    column_name: str


class DiscoveredRelation(BaseModel):
    """A discovered cross-source relation."""
    source_column: RelationColumn
    target_column: RelationColumn
    confidence: float
    relation_type: str
    reason: str


class DiscoverRelationsResponse(BaseModel):
    """Response from relation discovery."""
    relations: list[DiscoveredRelation]
    summary: str
    recommendations: list[str]
    sources_analyzed: int
    columns_analyzed: int


@router.get(
    "/asset/{asset_id}",
    response_model=LineageGraphResponse,
    summary="Get asset lineage",
)
async def get_asset_lineage(
    asset_id: uuid.UUID,
    direction: str = "both",
    depth: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get lineage graph for a data asset.

    Args:
        asset_id: The asset ID
        direction: "upstream", "downstream", or "both"
        depth: Maximum depth to traverse (1-10)

    Returns:
        Lineage graph with nodes and edges
    """
    if direction not in ("upstream", "downstream", "both"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'upstream', 'downstream', or 'both'",
        )

    if not 1 <= depth <= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Depth must be between 1 and 10",
        )

    service = LineageService(db)
    try:
        result = await service.get_asset_lineage(asset_id, direction, depth)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/graph",
    response_model=LineageGraphResponse,
    summary="Get global lineage graph",
)
async def get_global_graph(
    node_types: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the global lineage graph.

    Args:
        node_types: Comma-separated node types to filter
        limit: Maximum nodes to return (max 500)

    Returns:
        Global lineage graph
    """
    if limit > 500:
        limit = 500

    type_list = node_types.split(",") if node_types else None

    service = LineageService(db)
    return await service.get_global_graph(type_list, limit)


@router.post(
    "/impact/{asset_id}",
    response_model=ImpactAnalysisResponse,
    summary="Perform impact analysis",
)
async def impact_analysis(
    asset_id: uuid.UUID,
    include_downstream: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Perform impact analysis for an asset.

    Identifies all downstream assets, pipelines, and tasks that would be
    affected if this asset changes.

    Args:
        asset_id: The asset ID to analyze
        include_downstream: Whether to include downstream impacts

    Returns:
        Impact analysis results
    """
    service = LineageService(db)
    try:
        return await service.impact_analysis(asset_id, include_downstream)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/build",
    summary="Build lineage graph",
)
async def build_lineage(
    request: BuildLineageRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Build or rebuild the lineage graph.

    This scans existing data sources, collect tasks, ETL pipelines,
    and assets to build the lineage graph.

    Args:
        request: Optional build configuration

    Returns:
        Build summary with statistics
    """
    rebuild_all = request.rebuild_all if request else False
    source_ids = request.source_ids if request else None
    asset_ids = request.asset_ids if request else None

    service = LineageService(db)
    return await service.build_lineage(rebuild_all, source_ids, asset_ids)


@router.get(
    "/upstream/{node_id}",
    response_model=LineageGraphResponse,
    summary="Get upstream nodes",
)
async def get_upstream(
    node_id: uuid.UUID,
    depth: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all upstream nodes for a given lineage node.

    Args:
        node_id: The lineage node ID
        depth: Maximum depth to traverse (1-10)

    Returns:
        Graph with upstream nodes and edges
    """
    if not 1 <= depth <= 10:
        depth = 3

    service = LineageService(db)
    return await service.get_upstream(node_id, depth)


@router.get(
    "/downstream/{node_id}",
    response_model=LineageGraphResponse,
    summary="Get downstream nodes",
)
async def get_downstream(
    node_id: uuid.UUID,
    depth: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all downstream nodes for a given lineage node.

    Args:
        node_id: The lineage node ID
        depth: Maximum depth to traverse (1-10)

    Returns:
        Graph with downstream nodes and edges
    """
    if not 1 <= depth <= 10:
        depth = 3

    service = LineageService(db)
    return await service.get_downstream(node_id, depth)


@router.post(
    "/discover-relations",
    response_model=DiscoverRelationsResponse,
    summary="Discover cross-source relations",
)
async def discover_relations(
    request: DiscoverRelationsRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Discover potential cross-data source relationships.

    Analyzes column names, types, and metadata across data sources
    to identify potential join relationships and foreign key references.

    Args:
        request: Optional discovery configuration

    Returns:
        List of discovered relations with confidence scores
    """
    source_ids = request.source_ids if request else None
    confidence_threshold = request.confidence_threshold if request else 0.7

    ai_service = AIService(db)
    return await ai_service.discover_cross_source_relations(
        source_ids=source_ids,
        confidence_threshold=confidence_threshold,
    )
