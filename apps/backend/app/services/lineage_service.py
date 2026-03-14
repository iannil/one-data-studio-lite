"""Data lineage tracking service for building and querying lineage graphs."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DataAsset,
    DataSource,
    CollectTask,
    ETLPipeline,
)
from app.models.lineage import (
    LineageNode,
    LineageEdge,
    LineageColumnNode,
    LineageNodeType,
    LineageEdgeType,
)


class LineageService:
    """Service for building and querying data lineage graphs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_node(
        self,
        node_type: LineageNodeType,
        reference_id: uuid.UUID,
        reference_table: str,
        name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LineageNode:
        """Get existing node or create new one.

        Args:
            node_type: Type of the lineage node
            reference_id: ID of the referenced entity
            reference_table: Name of the referenced table
            name: Display name for the node
            description: Optional description
            metadata: Optional metadata dictionary

        Returns:
            The lineage node (existing or newly created)
        """
        result = await self.db.execute(
            select(LineageNode).where(
                LineageNode.reference_id == reference_id,
                LineageNode.reference_table == reference_table,
            )
        )
        node = result.scalar_one_or_none()

        if node:
            node.name = name
            if description:
                node.description = description
            if metadata:
                node.node_metadata = {**(node.node_metadata or {}), **metadata}
            await self.db.commit()
            await self.db.refresh(node)
            return node

        node = LineageNode(
            node_type=node_type,
            reference_id=reference_id,
            reference_table=reference_table,
            name=name,
            description=description,
            node_metadata=metadata,
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def create_edge(
        self,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        edge_type: LineageEdgeType,
        description: str | None = None,
        transformation_details: dict[str, Any] | None = None,
    ) -> LineageEdge:
        """Create an edge between two lineage nodes.

        Args:
            source_node_id: Source node ID
            target_node_id: Target node ID
            edge_type: Type of the edge
            description: Optional description
            transformation_details: Optional transformation metadata

        Returns:
            The created or existing edge
        """
        result = await self.db.execute(
            select(LineageEdge).where(
                LineageEdge.source_node_id == source_node_id,
                LineageEdge.target_node_id == target_node_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.edge_type = edge_type
            if description:
                existing.description = description
            if transformation_details:
                existing.transformation_details = transformation_details
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        edge = LineageEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            description=description,
            transformation_details=transformation_details,
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def build_lineage(
        self,
        rebuild_all: bool = False,
        source_ids: list[uuid.UUID] | None = None,
        asset_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        """Build or rebuild the lineage graph from existing data.

        Args:
            rebuild_all: If True, rebuild entire lineage graph
            source_ids: Optional list of source IDs to rebuild
            asset_ids: Optional list of asset IDs to rebuild

        Returns:
            Summary of the build operation
        """
        stats = {
            "nodes_created": 0,
            "nodes_updated": 0,
            "edges_created": 0,
            "errors": [],
        }

        if rebuild_all:
            await self.db.execute(
                LineageEdge.__table__.delete()
            )
            await self.db.execute(
                LineageNode.__table__.delete()
            )
            await self.db.commit()

        sources_result = await self.db.execute(select(DataSource))
        sources = list(sources_result.scalars())

        for source in sources:
            if source_ids and source.id not in source_ids:
                continue
            try:
                await self.get_or_create_node(
                    node_type=LineageNodeType.DATA_SOURCE,
                    reference_id=source.id,
                    reference_table="data_sources",
                    name=source.name,
                    description=f"Data source: {source.source_type.value}",
                    metadata={"source_type": source.source_type.value},
                )
                stats["nodes_created"] += 1
            except Exception as e:
                stats["errors"].append(f"Source {source.id}: {str(e)}")

        tasks_result = await self.db.execute(select(CollectTask))
        tasks = list(tasks_result.scalars())

        for task in tasks:
            try:
                task_node = await self.get_or_create_node(
                    node_type=LineageNodeType.COLLECT_TASK,
                    reference_id=task.id,
                    reference_table="collect_tasks",
                    name=task.name,
                    description=f"Collection task: {task.collect_type}",
                    metadata={"collect_type": task.collect_type},
                )
                stats["nodes_created"] += 1

                source_node_result = await self.db.execute(
                    select(LineageNode).where(
                        LineageNode.reference_id == task.source_id,
                        LineageNode.reference_table == "data_sources",
                    )
                )
                source_node = source_node_result.scalar_one_or_none()

                if source_node:
                    await self.create_edge(
                        source_node_id=source_node.id,
                        target_node_id=task_node.id,
                        edge_type=LineageEdgeType.COLLECTS_FROM,
                        description=f"Collects from {source_node.name}",
                    )
                    stats["edges_created"] += 1

            except Exception as e:
                stats["errors"].append(f"Task {task.id}: {str(e)}")

        pipelines_result = await self.db.execute(select(ETLPipeline))
        pipelines = list(pipelines_result.scalars())

        for pipeline in pipelines:
            try:
                pipeline_node = await self.get_or_create_node(
                    node_type=LineageNodeType.ETL_PIPELINE,
                    reference_id=pipeline.id,
                    reference_table="etl_pipelines",
                    name=pipeline.name,
                    description=pipeline.description,
                    metadata={
                        "source_type": pipeline.source_type,
                        "target_type": pipeline.target_type,
                        "steps_count": len(pipeline.steps) if pipeline.steps else 0,
                    },
                )
                stats["nodes_created"] += 1

                source_config = pipeline.source_config or {}
                if "source_id" in source_config:
                    source_node_result = await self.db.execute(
                        select(LineageNode).where(
                            LineageNode.reference_id == uuid.UUID(str(source_config["source_id"])),
                            LineageNode.reference_table == "data_sources",
                        )
                    )
                    source_node = source_node_result.scalar_one_or_none()

                    if source_node:
                        await self.create_edge(
                            source_node_id=source_node.id,
                            target_node_id=pipeline_node.id,
                            edge_type=LineageEdgeType.TRANSFORMS,
                            description=f"ETL reads from {source_node.name}",
                            transformation_details={
                                "table_name": source_config.get("table_name"),
                            },
                        )
                        stats["edges_created"] += 1

            except Exception as e:
                stats["errors"].append(f"Pipeline {pipeline.id}: {str(e)}")

        assets_result = await self.db.execute(
            select(DataAsset).where(DataAsset.is_active.is_(True))
        )
        assets = list(assets_result.scalars())

        for asset in assets:
            if asset_ids and asset.id not in asset_ids:
                continue
            try:
                asset_node = await self.get_or_create_node(
                    node_type=LineageNodeType.DATA_ASSET,
                    reference_id=asset.id,
                    reference_table="data_assets",
                    name=asset.name,
                    description=asset.description,
                    metadata={
                        "asset_type": asset.asset_type.value,
                        "source_table": asset.source_table,
                        "source_schema": asset.source_schema,
                    },
                )
                stats["nodes_created"] += 1

                if asset.upstream_assets:
                    for upstream_id in asset.upstream_assets:
                        upstream_node_result = await self.db.execute(
                            select(LineageNode).where(
                                LineageNode.reference_id == upstream_id,
                                LineageNode.reference_table == "data_assets",
                            )
                        )
                        upstream_node = upstream_node_result.scalar_one_or_none()

                        if upstream_node:
                            await self.create_edge(
                                source_node_id=upstream_node.id,
                                target_node_id=asset_node.id,
                                edge_type=LineageEdgeType.PRODUCES,
                                description=f"Produces {asset.name}",
                            )
                            stats["edges_created"] += 1

            except Exception as e:
                stats["errors"].append(f"Asset {asset.id}: {str(e)}")

        return stats

    async def get_upstream(
        self,
        node_id: uuid.UUID,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get all upstream nodes for a given node.

        Args:
            node_id: The node ID to find upstream for
            depth: Maximum depth to traverse

        Returns:
            Graph with upstream nodes and edges
        """
        return await self._traverse_lineage(node_id, "upstream", depth)

    async def get_downstream(
        self,
        node_id: uuid.UUID,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get all downstream nodes for a given node.

        Args:
            node_id: The node ID to find downstream for
            depth: Maximum depth to traverse

        Returns:
            Graph with downstream nodes and edges
        """
        return await self._traverse_lineage(node_id, "downstream", depth)

    async def _traverse_lineage(
        self,
        start_node_id: uuid.UUID,
        direction: str,
        max_depth: int,
    ) -> dict[str, Any]:
        """Traverse the lineage graph in a given direction.

        Args:
            start_node_id: Starting node ID
            direction: "upstream" or "downstream"
            max_depth: Maximum depth to traverse

        Returns:
            Graph structure with nodes and edges
        """
        visited_nodes: dict[str, dict[str, Any]] = {}
        collected_edges: list[dict[str, Any]] = []
        to_visit = [(start_node_id, 0)]
        visited_ids: set[uuid.UUID] = set()

        while to_visit:
            current_id, current_depth = to_visit.pop(0)

            if current_id in visited_ids or current_depth > max_depth:
                continue

            visited_ids.add(current_id)

            node_result = await self.db.execute(
                select(LineageNode).where(LineageNode.id == current_id)
            )
            node = node_result.scalar_one_or_none()

            if not node:
                continue

            visited_nodes[str(node.id)] = {
                "id": str(node.id),
                "type": node.node_type.value,
                "name": node.name,
                "description": node.description,
                "reference_id": str(node.reference_id),
                "reference_table": node.reference_table,
                "metadata": node.node_metadata,
            }

            if direction == "upstream":
                edges_result = await self.db.execute(
                    select(LineageEdge).where(LineageEdge.target_node_id == current_id)
                )
            else:
                edges_result = await self.db.execute(
                    select(LineageEdge).where(LineageEdge.source_node_id == current_id)
                )

            edges = list(edges_result.scalars())

            for edge in edges:
                edge_data = {
                    "id": str(edge.id),
                    "source": str(edge.source_node_id),
                    "target": str(edge.target_node_id),
                    "type": edge.edge_type.value,
                    "description": edge.description,
                    "transformation_details": edge.transformation_details,
                }

                if edge_data not in collected_edges:
                    collected_edges.append(edge_data)

                next_id = edge.source_node_id if direction == "upstream" else edge.target_node_id
                if next_id not in visited_ids:
                    to_visit.append((next_id, current_depth + 1))

        return {
            "nodes": list(visited_nodes.values()),
            "edges": collected_edges,
            "root_node_id": str(start_node_id),
            "depth": max_depth,
        }

    async def get_asset_lineage(
        self,
        asset_id: uuid.UUID,
        direction: str = "both",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get lineage for a data asset.

        Args:
            asset_id: The asset ID
            direction: "upstream", "downstream", or "both"
            depth: Maximum depth to traverse

        Returns:
            Complete lineage graph for the asset
        """
        node_result = await self.db.execute(
            select(LineageNode).where(
                LineageNode.reference_id == asset_id,
                LineageNode.reference_table == "data_assets",
            )
        )
        node = node_result.scalar_one_or_none()

        if not node:
            asset_result = await self.db.execute(
                select(DataAsset).where(DataAsset.id == asset_id)
            )
            asset = asset_result.scalar_one_or_none()

            if not asset:
                raise ValueError(f"Asset not found: {asset_id}")

            node = await self.get_or_create_node(
                node_type=LineageNodeType.DATA_ASSET,
                reference_id=asset_id,
                reference_table="data_assets",
                name=asset.name,
                description=asset.description,
            )

        all_nodes: dict[str, dict[str, Any]] = {}
        all_edges: list[dict[str, Any]] = []

        if direction in ("upstream", "both"):
            upstream = await self.get_upstream(node.id, depth)
            for n in upstream["nodes"]:
                all_nodes[n["id"]] = n
            all_edges.extend(upstream["edges"])

        if direction in ("downstream", "both"):
            downstream = await self.get_downstream(node.id, depth)
            for n in downstream["nodes"]:
                all_nodes[n["id"]] = n
            for e in downstream["edges"]:
                if e not in all_edges:
                    all_edges.append(e)

        return {
            "nodes": list(all_nodes.values()),
            "edges": all_edges,
            "root_node_id": str(node.id),
            "depth": depth,
        }

    async def impact_analysis(
        self,
        asset_id: uuid.UUID,
        include_downstream: bool = True,
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
        lineage = await self.get_asset_lineage(
            asset_id,
            direction="downstream" if include_downstream else "both",
            depth=10,
        )

        impacted_assets = []
        impacted_pipelines = []
        impacted_tasks = []

        for node in lineage["nodes"]:
            if node["id"] == lineage["root_node_id"]:
                continue

            if node["type"] == "data_asset":
                impacted_assets.append(node)
            elif node["type"] == "etl_pipeline":
                impacted_pipelines.append(node)
            elif node["type"] == "collect_task":
                impacted_tasks.append(node)

        return {
            "source_asset_id": str(asset_id),
            "impacted_assets": impacted_assets,
            "impacted_pipelines": impacted_pipelines,
            "impacted_tasks": impacted_tasks,
            "total_impacted": len(impacted_assets) + len(impacted_pipelines) + len(impacted_tasks),
            "lineage_graph": lineage,
        }

    async def get_global_graph(
        self,
        node_types: list[str] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get the global lineage graph.

        Args:
            node_types: Optional filter for node types
            limit: Maximum number of nodes to return

        Returns:
            Global lineage graph
        """
        query = select(LineageNode)
        if node_types:
            type_enums = [LineageNodeType(t) for t in node_types]
            query = query.where(LineageNode.node_type.in_(type_enums))
        query = query.limit(limit)

        nodes_result = await self.db.execute(query)
        nodes = list(nodes_result.scalars())

        node_ids = [n.id for n in nodes]

        edges_result = await self.db.execute(
            select(LineageEdge).where(
                or_(
                    LineageEdge.source_node_id.in_(node_ids),
                    LineageEdge.target_node_id.in_(node_ids),
                )
            )
        )
        edges = list(edges_result.scalars())

        return {
            "nodes": [
                {
                    "id": str(n.id),
                    "type": n.node_type.value,
                    "name": n.name,
                    "description": n.description,
                    "reference_id": str(n.reference_id),
                    "reference_table": n.reference_table,
                    "metadata": n.node_metadata,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": str(e.id),
                    "source": str(e.source_node_id),
                    "target": str(e.target_node_id),
                    "type": e.edge_type.value,
                    "description": e.description,
                    "transformation_details": e.transformation_details,
                }
                for e in edges
            ],
            "depth": 0,
        }

    async def create_column_lineage(
        self,
        edge_id: uuid.UUID,
        source_column_name: str,
        target_column_name: str,
        source_column_id: uuid.UUID | None = None,
        target_column_id: uuid.UUID | None = None,
        source_table_name: str | None = None,
        target_table_name: str | None = None,
        transformation_type: str | None = None,
        transformation_expression: str | None = None,
        confidence: float = 1.0,
    ) -> LineageColumnNode:
        """Create a column-level lineage record.

        Args:
            edge_id: The parent edge ID
            source_column_name: Name of the source column
            target_column_name: Name of the target column
            source_column_id: Optional reference to MetadataColumn
            target_column_id: Optional reference to MetadataColumn
            source_table_name: Optional source table name
            target_table_name: Optional target table name
            transformation_type: Type of transformation (e.g., 'direct', 'computed', 'aggregated')
            transformation_expression: SQL/expression describing the transformation
            confidence: Confidence score for inferred lineage (0.0-1.0)

        Returns:
            The created LineageColumnNode
        """
        column_lineage = LineageColumnNode(
            edge_id=edge_id,
            source_column_id=source_column_id,
            source_column_name=source_column_name,
            source_table_name=source_table_name,
            target_column_id=target_column_id,
            target_column_name=target_column_name,
            target_table_name=target_table_name,
            transformation_type=transformation_type,
            transformation_expression=transformation_expression,
            confidence=confidence,
        )
        self.db.add(column_lineage)
        await self.db.commit()
        await self.db.refresh(column_lineage)
        return column_lineage

    async def get_column_lineage(
        self,
        edge_id: uuid.UUID | None = None,
        source_column_id: uuid.UUID | None = None,
        target_column_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Get column-level lineage records.

        Args:
            edge_id: Optional edge ID to filter by
            source_column_id: Optional source column ID to filter by
            target_column_id: Optional target column ID to filter by

        Returns:
            List of column lineage records
        """
        query = select(LineageColumnNode)

        conditions = []
        if edge_id:
            conditions.append(LineageColumnNode.edge_id == edge_id)
        if source_column_id:
            conditions.append(LineageColumnNode.source_column_id == source_column_id)
        if target_column_id:
            conditions.append(LineageColumnNode.target_column_id == target_column_id)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        column_lineage = list(result.scalars())

        return [
            {
                "id": str(cl.id),
                "edge_id": str(cl.edge_id),
                "source_column_id": str(cl.source_column_id) if cl.source_column_id else None,
                "source_column_name": cl.source_column_name,
                "source_table_name": cl.source_table_name,
                "target_column_id": str(cl.target_column_id) if cl.target_column_id else None,
                "target_column_name": cl.target_column_name,
                "target_table_name": cl.target_table_name,
                "transformation_type": cl.transformation_type,
                "transformation_expression": cl.transformation_expression,
                "confidence": cl.confidence,
            }
            for cl in column_lineage
        ]

    async def get_column_upstream(
        self,
        column_name: str,
        table_name: str | None = None,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get upstream column lineage for a specific column.

        Traces back through the lineage graph to find all source columns
        that contribute to this column.

        Args:
            column_name: The target column name
            table_name: Optional table name to disambiguate
            depth: Maximum depth to traverse

        Returns:
            Column lineage graph with source columns and transformations
        """
        column_nodes: list[dict[str, Any]] = []
        column_edges: list[dict[str, Any]] = []
        visited: set[str] = set()

        async def traverse(col_name: str, tbl_name: str | None, current_depth: int) -> None:
            if current_depth > depth:
                return

            key = f"{tbl_name or ''}.{col_name}"
            if key in visited:
                return
            visited.add(key)

            query = select(LineageColumnNode).where(
                LineageColumnNode.target_column_name == col_name
            )
            if tbl_name:
                query = query.where(LineageColumnNode.target_table_name == tbl_name)

            result = await self.db.execute(query)
            records = list(result.scalars())

            for record in records:
                target_key = f"{record.target_table_name or ''}.{record.target_column_name}"
                source_key = f"{record.source_table_name or ''}.{record.source_column_name}"

                target_node = {
                    "id": target_key,
                    "column_name": record.target_column_name,
                    "table_name": record.target_table_name,
                    "column_id": str(record.target_column_id) if record.target_column_id else None,
                }
                source_node = {
                    "id": source_key,
                    "column_name": record.source_column_name,
                    "table_name": record.source_table_name,
                    "column_id": str(record.source_column_id) if record.source_column_id else None,
                }

                if target_key not in [n["id"] for n in column_nodes]:
                    column_nodes.append(target_node)
                if source_key not in [n["id"] for n in column_nodes]:
                    column_nodes.append(source_node)

                edge = {
                    "id": str(record.id),
                    "source": source_key,
                    "target": target_key,
                    "transformation_type": record.transformation_type,
                    "transformation_expression": record.transformation_expression,
                    "confidence": record.confidence,
                }
                if edge["id"] not in [e["id"] for e in column_edges]:
                    column_edges.append(edge)

                await traverse(
                    record.source_column_name,
                    record.source_table_name,
                    current_depth + 1
                )

        await traverse(column_name, table_name, 0)

        return {
            "nodes": column_nodes,
            "edges": column_edges,
            "root_column": column_name,
            "root_table": table_name,
            "depth": depth,
        }

    async def get_column_downstream(
        self,
        column_name: str,
        table_name: str | None = None,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get downstream column lineage for a specific column.

        Traces forward through the lineage graph to find all target columns
        that depend on this column.

        Args:
            column_name: The source column name
            table_name: Optional table name to disambiguate
            depth: Maximum depth to traverse

        Returns:
            Column lineage graph with target columns and transformations
        """
        column_nodes: list[dict[str, Any]] = []
        column_edges: list[dict[str, Any]] = []
        visited: set[str] = set()

        async def traverse(col_name: str, tbl_name: str | None, current_depth: int) -> None:
            if current_depth > depth:
                return

            key = f"{tbl_name or ''}.{col_name}"
            if key in visited:
                return
            visited.add(key)

            query = select(LineageColumnNode).where(
                LineageColumnNode.source_column_name == col_name
            )
            if tbl_name:
                query = query.where(LineageColumnNode.source_table_name == tbl_name)

            result = await self.db.execute(query)
            records = list(result.scalars())

            for record in records:
                source_key = f"{record.source_table_name or ''}.{record.source_column_name}"
                target_key = f"{record.target_table_name or ''}.{record.target_column_name}"

                source_node = {
                    "id": source_key,
                    "column_name": record.source_column_name,
                    "table_name": record.source_table_name,
                    "column_id": str(record.source_column_id) if record.source_column_id else None,
                }
                target_node = {
                    "id": target_key,
                    "column_name": record.target_column_name,
                    "table_name": record.target_table_name,
                    "column_id": str(record.target_column_id) if record.target_column_id else None,
                }

                if source_key not in [n["id"] for n in column_nodes]:
                    column_nodes.append(source_node)
                if target_key not in [n["id"] for n in column_nodes]:
                    column_nodes.append(target_node)

                edge = {
                    "id": str(record.id),
                    "source": source_key,
                    "target": target_key,
                    "transformation_type": record.transformation_type,
                    "transformation_expression": record.transformation_expression,
                    "confidence": record.confidence,
                }
                if edge["id"] not in [e["id"] for e in column_edges]:
                    column_edges.append(edge)

                await traverse(
                    record.target_column_name,
                    record.target_table_name,
                    current_depth + 1
                )

        await traverse(column_name, table_name, 0)

        return {
            "nodes": column_nodes,
            "edges": column_edges,
            "root_column": column_name,
            "root_table": table_name,
            "depth": depth,
        }
