"""Data lineage tracking models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LineageNodeType(str, enum.Enum):
    """Types of nodes in the lineage graph."""
    DATA_SOURCE = "data_source"
    COLLECT_TASK = "collect_task"
    ETL_PIPELINE = "etl_pipeline"
    DATA_ASSET = "data_asset"
    EXTERNAL = "external"


class LineageEdgeType(str, enum.Enum):
    """Types of edges connecting lineage nodes."""
    COLLECTS_FROM = "collects_from"
    TRANSFORMS = "transforms"
    PRODUCES = "produces"
    DEPENDS_ON = "depends_on"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LineageNode(Base, TimestampMixin):
    """Represents a node in the data lineage graph."""
    __tablename__ = "lineage_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    node_type: Mapped[LineageNodeType] = mapped_column(SQLEnum(LineageNodeType))

    # Reference to the actual entity
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    reference_table: Mapped[str] = mapped_column(String(100))

    # Node metadata
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    node_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Relationships
    outgoing_edges: Mapped[list["LineageEdge"]] = relationship(
        "LineageEdge",
        foreign_keys="LineageEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["LineageEdge"]] = relationship(
        "LineageEdge",
        foreign_keys="LineageEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class LineageEdge(Base, TimestampMixin):
    """Represents an edge (connection) between lineage nodes."""
    __tablename__ = "lineage_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lineage_nodes.id", ondelete="CASCADE"),
        index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lineage_nodes.id", ondelete="CASCADE"),
        index=True
    )

    edge_type: Mapped[LineageEdgeType] = mapped_column(SQLEnum(LineageEdgeType))

    # Edge metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    transformation_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Relationships
    source_node: Mapped["LineageNode"] = relationship(
        "LineageNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node: Mapped["LineageNode"] = relationship(
        "LineageNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )
