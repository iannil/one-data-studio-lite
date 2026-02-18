"""Pydantic schemas for data lineage tracking."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LineageNodeBase(BaseModel):
    """Base schema for lineage nodes."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    metadata: dict[str, Any] | None = None


class LineageNodeCreate(LineageNodeBase):
    """Schema for creating a lineage node."""
    node_type: str = Field(..., pattern=r"^(data_source|collect_task|etl_pipeline|data_asset|external)$")
    reference_id: uuid.UUID
    reference_table: str = Field(..., min_length=1, max_length=100)


class LineageNodeResponse(LineageNodeBase):
    """Schema for lineage node response."""
    id: uuid.UUID
    node_type: str
    reference_id: uuid.UUID
    reference_table: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LineageEdgeBase(BaseModel):
    """Base schema for lineage edges."""
    description: str | None = None
    transformation_details: dict[str, Any] | None = None


class LineageEdgeCreate(LineageEdgeBase):
    """Schema for creating a lineage edge."""
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str = Field(..., pattern=r"^(collects_from|transforms|produces|depends_on)$")


class LineageEdgeResponse(LineageEdgeBase):
    """Schema for lineage edge response."""
    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LineageGraphNode(BaseModel):
    """Node representation in the lineage graph."""
    id: str
    type: str
    name: str
    description: str | None = None
    reference_id: str
    reference_table: str
    metadata: dict[str, Any] | None = None


class LineageGraphEdge(BaseModel):
    """Edge representation in the lineage graph."""
    id: str
    source: str
    target: str
    type: str
    description: str | None = None
    transformation_details: dict[str, Any] | None = None


class LineageGraphResponse(BaseModel):
    """Response schema for lineage graph queries."""
    nodes: list[LineageGraphNode]
    edges: list[LineageGraphEdge]
    root_node_id: str | None = None
    depth: int = 0


class AssetLineageRequest(BaseModel):
    """Request schema for getting asset lineage."""
    asset_id: uuid.UUID
    direction: str = Field(default="both", pattern=r"^(upstream|downstream|both)$")
    depth: int = Field(default=3, ge=1, le=10)


class ImpactAnalysisRequest(BaseModel):
    """Request schema for impact analysis."""
    asset_id: uuid.UUID
    include_downstream: bool = True
    include_dependent_assets: bool = True


class ImpactAnalysisResponse(BaseModel):
    """Response schema for impact analysis."""
    source_asset_id: str
    impacted_assets: list[LineageGraphNode]
    impacted_pipelines: list[LineageGraphNode]
    impacted_tasks: list[LineageGraphNode]
    total_impacted: int
    lineage_graph: LineageGraphResponse


class BuildLineageRequest(BaseModel):
    """Request schema for building/rebuilding lineage."""
    rebuild_all: bool = False
    source_ids: list[uuid.UUID] | None = None
    asset_ids: list[uuid.UUID] | None = None
