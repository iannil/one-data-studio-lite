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


# Column-level lineage models
class CreateColumnLineageRequest(BaseModel):
    """Request to create column-level lineage."""
    edge_id: uuid.UUID
    source_column_name: str
    target_column_name: str
    source_column_id: uuid.UUID | None = None
    target_column_id: uuid.UUID | None = None
    source_table_name: str | None = None
    target_table_name: str | None = None
    transformation_type: str | None = None
    transformation_expression: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ColumnLineageNode(BaseModel):
    """A node in the column lineage graph."""
    id: str
    column_name: str
    table_name: str | None = None
    column_id: str | None = None


class ColumnLineageEdge(BaseModel):
    """An edge in the column lineage graph."""
    id: str
    source: str
    target: str
    transformation_type: str | None = None
    transformation_expression: str | None = None
    confidence: float


class ColumnLineageGraphResponse(BaseModel):
    """Response containing column-level lineage graph."""
    nodes: list[ColumnLineageNode]
    edges: list[ColumnLineageEdge]
    root_column: str
    root_table: str | None = None
    depth: int


@router.post(
    "/column",
    summary="Create column lineage",
)
async def create_column_lineage(
    request: CreateColumnLineageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a column-level lineage record.

    Tracks how data flows at the column level between source and target.

    Args:
        request: Column lineage details

    Returns:
        Created column lineage record
    """
    service = LineageService(db)
    column_lineage = await service.create_column_lineage(
        edge_id=request.edge_id,
        source_column_name=request.source_column_name,
        target_column_name=request.target_column_name,
        source_column_id=request.source_column_id,
        target_column_id=request.target_column_id,
        source_table_name=request.source_table_name,
        target_table_name=request.target_table_name,
        transformation_type=request.transformation_type,
        transformation_expression=request.transformation_expression,
        confidence=request.confidence,
    )
    return {
        "id": str(column_lineage.id),
        "edge_id": str(column_lineage.edge_id),
        "source_column_name": column_lineage.source_column_name,
        "target_column_name": column_lineage.target_column_name,
    }


@router.get(
    "/column",
    summary="Get column lineage",
)
async def get_column_lineage(
    edge_id: uuid.UUID | None = None,
    source_column_id: uuid.UUID | None = None,
    target_column_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get column-level lineage records.

    Args:
        edge_id: Optional edge ID to filter by
        source_column_id: Optional source column ID to filter by
        target_column_id: Optional target column ID to filter by

    Returns:
        List of column lineage records
    """
    service = LineageService(db)
    return await service.get_column_lineage(
        edge_id=edge_id,
        source_column_id=source_column_id,
        target_column_id=target_column_id,
    )


@router.get(
    "/column/upstream",
    response_model=ColumnLineageGraphResponse,
    summary="Get column upstream lineage",
)
async def get_column_upstream(
    column_name: str,
    table_name: str | None = None,
    depth: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get upstream column lineage for a specific column.

    Traces back through the lineage graph to find all source columns
    that contribute to this column.

    Args:
        column_name: The target column name
        table_name: Optional table name to disambiguate
        depth: Maximum depth to traverse (1-10)

    Returns:
        Column lineage graph with source columns and transformations
    """
    if not 1 <= depth <= 10:
        depth = 3

    service = LineageService(db)
    return await service.get_column_upstream(column_name, table_name, depth)


@router.get(
    "/column/downstream",
    response_model=ColumnLineageGraphResponse,
    summary="Get column downstream lineage",
)
async def get_column_downstream(
    column_name: str,
    table_name: str | None = None,
    depth: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get downstream column lineage for a specific column.

    Traces forward through the lineage graph to find all target columns
    that depend on this column.

    Args:
        column_name: The source column name
        table_name: Optional table name to disambiguate
        depth: Maximum depth to traverse (1-10)

    Returns:
        Column lineage graph with target columns and transformations
    """
    if not 1 <= depth <= 10:
        depth = 3

    service = LineageService(db)
    return await service.get_column_downstream(column_name, table_name, depth)


# ============================================================================
# Visualization Endpoints
# ============================================================================


@router.get("/visualization/node/{node_id}")
async def get_node_visualization(
    node_id: str,
    direction: str = "both",
    depth: int = 3,
    format: str = "react_flow",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get visualization for a specific node.

    Args:
        node_id: The node ID to visualize
        direction: "upstream", "downstream", or "both"
        depth: Maximum depth to traverse
        format: "react_flow" or "d3"

    Returns:
        Graph visualization in requested format
    """
    from app.services.lineage.visualization_service import (
        get_lineage_visualizer,
        GraphLayout,
    )

    visualizer = get_lineage_visualizer(db)
    node_uuid = uuid.UUID(node_id)

    # Get upstream and/or downstream
    service = LineageService(db)
    if direction == "upstream":
        graph = await service.get_upstream(node_uuid, depth)
    elif direction == "downstream":
        graph = await service.get_downstream(node_uuid, depth)
    else:
        # Get both and merge
        upstream = await service.get_upstream(node_uuid, depth)
        downstream = await service.get_downstream(node_uuid, depth)

        # Merge nodes and edges
        all_nodes = {n["id"]: n for n in upstream["nodes"]}
        for n in downstream["nodes"]:
            all_nodes[n["id"]] = n

        all_edges = upstream["edges"] + [e for e in downstream["edges"]]

        graph = {
            "nodes": list(all_nodes.values()),
            "edges": all_edges,
        }

    # Create visualization
    layout = GraphLayout.HIERARCHICAL if direction != "both" else GraphLayout.FORCE_DIRECTED
    visualization = await visualizer.create_visualization(
        nodes=[],
        edges=[],
        layout=layout,
        root_node_id=node_id,
    )

    # Override with actual data
    visualization.nodes = [
        {
            "id": n["id"],
            "label": n.get("name", ""),
            "type": n.get("type", ""),
            "color": visualizer.NODE_COLORS.get(n.get("type", "")),
        }
        for n in graph.get("nodes", [])
    ]
    visualization.edges = [
        {
            "id": e["id"],
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "label": e.get("description"),
            "type": e.get("type", ""),
            "color": visualizer.EDGE_COLORS.get(e.get("type", "")),
        }
        for e in graph.get("edges", [])
    ]

    # Return in requested format
    if format == "react_flow":
        return visualization.to_react_flow_format()
    elif format == "d3":
        return visualization.to_d3_format()
    else:
        return visualization.to_dict()


@router.get("/visualization/global")
async def get_global_visualization(
    node_types: str | None = None,
    limit: int = 100,
    layout: str = "force_directed",
    format: str = "react_flow",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get global lineage graph visualization.

    Args:
        node_types: Comma-separated node types to filter
        limit: Maximum nodes to return
        layout: Graph layout algorithm
        format: Output format

    Returns:
        Complete graph visualization
    """
    from app.services.lineage.visualization_service import (
        get_lineage_visualizer,
        GraphLayout,
    )

    visualizer = get_lineage_visualizer(db)
    service = LineageService(db)

    # Get graph data
    graph = await service.get_global_graph(
        node_types=node_types.split(",") if node_types else None,
        limit=limit,
    )

    # Create visualization
    layout_enum = GraphLayout(layout)
    visualization = await visualizer.create_visualization(
        nodes=[],
        edges=[],
        layout=layout_enum,
    )

    # Add actual data
    visualization.nodes = [
        {
            "id": n["id"],
            "label": n.get("name", ""),
            "type": n.get("type", ""),
            "color": visualizer.NODE_COLORS.get(n.get("type", "")),
        }
        for n in graph.get("nodes", [])
    ]
    visualization.edges = [
        {
            "id": e["id"],
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "label": e.get("description"),
            "type": e.get("type", ""),
            "color": visualizer.EDGE_COLORS.get(e.get("type", "")),
        }
        for e in graph.get("edges", [])
    ]

    # Return in requested format
    if format == "react_flow":
        return visualization.to_react_flow_format()
    elif format == "d3":
        return visualization.to_d3_format()
    else:
        return visualization.to_dict()


# ============================================================================
# Path Analysis Endpoints
# ============================================================================


@router.get("/paths/analyze/{source_id}/{target_id}")
async def analyze_paths(
    source_id: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze all paths between two nodes.

    Args:
        source_id: Source node ID
        target_id: Target node ID

    Returns:
        Path analysis results including shortest path and all paths
    """
    from app.services.lineage.visualization_service import get_path_analyzer

    analyzer = get_path_analyzer(db)

    result = await analyzer.analyze_paths(
        source_id=source_id,
        target_id=target_id,
    )

    return {
        "source_id": result.source_id,
        "target_id": result.target_id,
        "paths": result.paths,
        "shortest_path": result.shortest_path,
        "shortest_length": result.shortest_length,
        "all_paths_count": result.all_paths_count,
    }


@router.get("/paths/shortest/{source_id}/{target_id}")
async def get_shortest_path(
    source_id: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get shortest path between two nodes.

    Args:
        source_id: Source node ID
        target_id: Target node ID

    Returns:
        Shortest path as list of node IDs
    """
    from app.services.lineage.visualization_service import get_path_analyzer

    analyzer = get_path_analyzer(db)

    path = await analyzer.find_shortest_path(source_id, target_id)

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No path found between nodes",
        )

    return {
        "source_id": source_id,
        "target_id": target_id,
        "path": path,
        "length": len(path),
    }


# ============================================================================
# Impact Analysis Endpoints
# ============================================================================


@router.post("/impact/analyze/column")
async def analyze_column_impact(
    table_name: str,
    column_name: str,
    include_transformation: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze impact of a column change.

    Args:
        table_name: Source table name
        column_name: Source column name
        include_transformation: Include transformation details

    Returns:
        Impact analysis results
    """
    from app.services.lineage.visualization_service import get_impact_analyzer

    analyzer = get_impact_analyzer(db)

    impact = await analyzer.analyze_column_impact(
        table_name=table_name,
        column_name=column_name,
        include_transformation=include_transformation,
    )

    return impact


@router.post("/impact/analyze/table")
async def analyze_table_impact(
    table_name: str,
    depth: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze impact of a table change.

    Args:
        table_name: Source table name
        depth: Maximum depth to traverse

    Returns:
        Impact analysis results
    """
    from app.services.lineage.visualization_service import get_impact_analyzer

    analyzer = get_impact_analyzer(db)

    impact = await analyzer.analyze_table_impact(
        table_name=table_name,
        depth=depth,
    )

    return impact


@router.post("/impact/summary")
async def get_impact_summary(
    asset_ids: List[str] = [],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get impact summary for multiple assets.

    Args:
        asset_ids: List of asset IDs to analyze

    Returns:
        Aggregated impact summary
    """
    from app.services.lineage.visualization_service import get_impact_analyzer

    analyzer = get_impact_analyzer(db)

    summary = await analyzer.get_impact_summary(asset_ids)

    return summary
