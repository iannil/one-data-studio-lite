"""
Data Lineage Visualization Service

Provides graph visualization support for data lineage including:
- D3.js compatible graph format
- React Flow compatible format
- Path analysis
- Critical path identification
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select

from app.models.lineage import (
    LineageNode,
    LineageEdge,
    LineageNodeType,
    LineageEdgeType,
)

logger = logging.getLogger(__name__)


class GraphLayout(str, Enum):
    """Graph layout algorithms"""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    TREE = "tree"
    RADIAL = "radial"
    DAGRE = "dagre"


class PathType(str, Enum):
    """Types of paths to analyze"""
    SHORTEST = "shortest"
    ALL = "all"
    CRITICAL = "critical"


@dataclass
class GraphNode:
    """A node in the visualization graph"""
    id: str
    label: str
    type: str
    # Position (for some layouts)
    x: Optional[float] = None
    y: Optional[float] = None
    # Styling
    color: Optional[str] = None
    size: Optional[int] = None
    # Metadata
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "size": self.size,
            "metadata": self.metadata or {},
        }


@dataclass
class GraphEdge:
    """An edge in the visualization graph"""
    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: Optional[str] = None
    # Styling
    color: Optional[str] = None
    width: Optional[float] = None
    dashed: bool = False
    # Metadata
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "type": self.type,
            "color": self.color,
            "width": self.width,
            "dashed": self.dashed,
            "metadata": self.metadata or {},
        }


@dataclass
class GraphVisualization:
    """A complete graph visualization"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    layout: GraphLayout = GraphLayout.FORCE_DIRECTED
    # Viewport
    width: int = 800
    height: int = 600
    # Statistics
    total_nodes: int = 0
    total_edges: int = 0
    max_depth: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "layout": self.layout.value,
            "width": self.width,
            "height": self.height,
            "stats": {
                "total_nodes": self.total_nodes,
                "total_edges": self.total_edges,
                "max_depth": self.max_depth,
            }
        }

    def to_react_flow_format(self) -> Dict[str, Any]:
        """Convert to React Flow compatible format"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "data": {
                        "label": n.label,
                        "type": n.type,
                        "metadata": n.metadata or {},
                    },
                    "position": {"x": n.x, "y": n.y} if n.x is not None else None,
                    "style": {
                        "background": n.color,
                        "width": n.size,
                        "height": n.size,
                    } if n.color else None,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "label": e.label,
                    "type": e.type,
                    "style": {
                        "stroke": e.color,
                        "strokeWidth": e.width,
                        "strokeDasharray": "5,5" if e.dashed else None,
                    } if e.color or e.dashed else None,
                }
                for e in self.edges
            ],
        }

    def to_d3_format(self) -> Dict[str, Any]:
        """Convert to D3.js force layout format"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.label,
                    "group": n.type,
                    "x": n.x,
                    "y": n.y,
                }
                for n in self.nodes
            ],
            "links": [
                {
                    "source": e.source,
                    "target": e.target,
                    "value": e.width or 1,
                }
                for e in self.edges
            ],
        }


@dataclass
class PathAnalysisResult:
    """Result of path analysis"""
    source_id: str
    target_id: str
    paths: List[List[str]]  # List of paths, each path is list of node IDs
    shortest_path: Optional[List[str]] = None
    shortest_length: int = 0
    all_paths_count: int = 0


class LineageVisualizer:
    """
    Data lineage visualization service

    Converts lineage data to visualization-ready formats.
    """

    # Color scheme for node types
    NODE_COLORS = {
        "data_source": "#6366f1",    # Indigo
        "collect_task": "#22c55e",   # Green
        "etl_pipeline": "#f59e0b",   # Amber
        "data_asset": "#3b82f6",    # Blue
        "external": "#8b5cf6",      # Violet
    }

    # Edge colors
    EDGE_COLORS = {
        "collects_from": "#94a3b8",
        "transforms": "#fbbf24",
        "produces": "#a3e635",
        "depends_on": "#f472b6",
    }

    def __init__(self, db: Session):
        self.db = db

    async def create_visualization(
        self,
        nodes: List[LineageNode],
        edges: List[LineageEdge],
        layout: GraphLayout = GraphLayout.FORCE_DIRECTED,
        root_node_id: Optional[str] = None,
    ) -> GraphVisualization:
        """Create a visualization from lineage nodes and edges"""
        graph_nodes = []
        graph_edges = []

        # Convert nodes
        for node in nodes:
            graph_nodes.append(GraphNode(
                id=str(node.id),
                label=node.name,
                type=node.node_type.value,
                color=self.NODE_COLORS.get(node.node_type.value),
                size=20,
                metadata={
                    "reference_id": str(node.reference_id),
                    "reference_table": node.reference_table,
                    "description": node.description,
                },
            ))

        # Convert edges
        for edge in edges:
            graph_edges.append(GraphEdge(
                id=str(edge.id),
                source=str(edge.source_node_id),
                target=str(edge.target_node_id),
                label=edge.description,
                type=edge.edge_type.value,
                color=self.EDGE_COLORS.get(edge.edge_type.value),
                width=2,
                dashed=edge.edge_type == LineageEdgeType.DEPENDS_ON,
                metadata={
                    "transformation_details": edge.transformation_details,
                },
            ))

        # Calculate positions for hierarchical layout
        if layout == GraphLayout.HIERARCHICAL and root_node_id:
            self._calculate_hierarchical_positions(graph_nodes, graph_edges, root_node_id)

        return GraphVisualization(
            nodes=graph_nodes,
            edges=graph_edges,
            layout=layout,
            total_nodes=len(graph_nodes),
            total_edges=len(graph_edges),
        )

    def _calculate_hierarchical_positions(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        root_id: str,
    ):
        """Calculate positions for hierarchical layout"""
        # Build adjacency list
        children = defaultdict(list)
        parents = defaultdict(list)
        depth_map = {}

        # Find root
        root_map = {n.id: n for n in nodes}
        if root_id not in root_map:
            return

        # BFS to calculate depths
        queue = deque([(root_id, 0)])
        visited = set()
        max_depth = 0

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            depth_map[node_id] = depth
            max_depth = max(max_depth, depth)

            # Find children
            for edge in edges:
                if edge.source == node_id:
                    children[node_id].append(edge.target)
                    parents[edge.target].append(node_id)
                    if edge.target not in visited:
                        queue.append((edge.target, depth + 1))

        # Assign positions
        level_width = 200
        level_height = 100

        for node_id, depth in depth_map.items():
            # Count nodes at this level
            level_nodes = [n for n, d in depth_map.items() if d == depth]
            index = level_nodes.index(node_id)

            nodes[root_map[node_id].x = 100 + depth * level_width
            nodes[root_map[node_id]].y = 50 + index * level_height

    async def get_subgraph_visualization(
        self,
        node_id: str,
        direction: str = "both",
        depth: int = 3,
        layout: GraphLayout = GraphLayout.HIERARCHICAL,
    ) -> GraphVisualization:
        """Get visualization for a subgraph"""
        # Fetch nodes and edges from database
        # This would query LineageNode and LineageEdge tables
        # For now, return empty visualization
        return GraphVisualization(
            nodes=[],
            edges=[],
            layout=layout,
        )

    async def get_full_graph_visualization(
        self,
        node_types: Optional[List[str]] = None,
        limit: int = 100,
        layout: GraphLayout = GraphLayout.FORCE_DIRECTED,
    ) -> GraphVisualization:
        """Get visualization for the full lineage graph"""
        # Fetch from database
        return GraphVisualization(
            nodes=[],
            edges=[],
            layout=layout,
        )


class PathAnalyzer:
    """
    Path analysis for lineage graphs

    Analyzes paths between nodes in the lineage graph.
    """

    def __init__(self, db: Session):
        self.db = db

    async def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS"""
        # Build adjacency list from database
        adj = await self._build_adjacency_list(edge_types)

        # BFS
        queue = deque([(source_id, [source_id])])
        visited = set([source_id])

        while queue:
            current, path = queue.popleft()

            if current == target_id:
                return path

            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        edge_types: Optional[List[str]] = None,
    ) -> List[List[str]]:
        """Find all paths between two nodes using DFS"""
        adj = await self._build_adjacency_list(edge_types)
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_depth:
                return
            if current == target_id:
                paths.append(path[:])
                return

            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs(neighbor, path + [neighbor], visited)
                    visited.remove(neighbor)

        dfs(source_id, [source_id], set([source_id]))
        return paths

    async def find_critical_path(
        self,
        source_id: str,
        target_id: str,
    ) -> Optional[List[str]]:
        """Find critical path (path with most dependencies)"""
        # Get all paths
        all_paths = await self.find_all_paths(source_id, target_id, max_depth=10)

        if not all_paths:
            return None

        # Score paths by number of high-impact nodes
        scored_paths = []
        for path in all_paths:
            score = 0
            for node_id in path:
                # Count how many downstream nodes depend on this node
                downstream_count = await self._count_downstream(node_id)
                score += downstream_count
            scored_paths.append((score, path))

        # Return path with highest score
        scored_paths.sort(key=lambda x: x[0], reverse=True)
        return scored_paths[0][1] if scored_paths else None

    async def analyze_paths(
        self,
        source_id: str,
        target_id: str,
    ) -> PathAnalysisResult:
        """Perform comprehensive path analysis"""
        shortest_path = await self.find_shortest_path(source_id, target_id)
        all_paths = await self.find_all_paths(source_id, target_id)
        critical_path = await self.find_critical_path(source_id, target_id)

        return PathAnalysisResult(
            source_id=source_id,
            target_id=target_id,
            paths=all_paths,
            shortest_path=shortest_path,
            shortest_length=len(shortest_path) if shortest_path else 0,
            all_paths_count=len(all_paths),
        )

    async def _build_adjacency_list(
        self,
        edge_types: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """Build adjacency list from database edges"""
        adj = defaultdict(list)

        # Query edges from database
        # In production, this would query LineageEdge table
        # For now, return empty
        return adj

    async def _count_downstream(self, node_id: str) -> int:
        """Count number of downstream nodes"""
        # In production, query from database
        return 0


class ImpactAnalyzer:
    """
    Impact analysis for data lineage

    Analyzes the impact of changes to data assets.
    """

    def __init__(self, db: Session):
        self.db = db
        self.path_analyzer = PathAnalyzer(db)

    async def analyze_column_impact(
        self,
        table_name: str,
        column_name: str,
        include_transformation: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze impact of a column change

        Returns all downstream columns and affected assets.
        """
        # Get downstream column lineage
        # In production, query from LineageColumnNode table

        impacted_columns = []
        impacted_assets = []
        impacted_pipelines = []

        return {
            "source_column": f"{table_name}.{column_name}",
            "impacted_columns": impacted_columns,
            "impacted_assets": impacted_assets,
            "impacted_pipelines": impacted_pipelines,
            "total_impact": len(impacted_columns),
        }

    async def analyze_table_impact(
        self,
        table_name: str,
        depth: int = 5,
    ) -> Dict[str, Any]:
        """
        Analyze impact of a table change

        Returns all downstream assets and their dependency depth.
        """
        # Get downstream assets
        # In production, query from LineageNode and LineageEdge tables

        impacted_assets = []
        depth_distribution = defaultdict(int)

        return {
            "source_table": table_name,
            "impacted_assets": impacted_assets,
            "depth_distribution": dict(depth_distribution),
            "total_impacted": len(impacted_assets),
        }

    async def get_impact_summary(
        self,
        asset_ids: List[str],
    ) -> Dict[str, Any]:
        """Get impact summary for multiple assets"""
        summaries = []

        for asset_id in asset_ids:
            # Get impact for each asset
            summary = await self.analyze_table_impact(asset_id)
            summaries.append(summary)

        # Aggregate statistics
        total_impacted = sum(s["total_impacted"] for s in summaries)

        # Find shared downstream assets (dependencies that would affect multiple upstreams)
        shared_downstream = self._find_shared_dependencies(summaries)

        return {
            "summaries": summaries,
            "total_impacted": total_impacted,
            "shared_dependencies": shared_downstream,
        }

    def _find_shared_dependencies(
        self,
        summaries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Find assets that depend on multiple upstream assets"""
        # Count how many upstreams each downstream depends on
        dependency_count = defaultdict(list)

        for summary in summaries:
            for asset in summary["impacted_assets"]:
                dependency_count[asset["id"]].append(summary["source_table"])

        # Find downstream with multiple upstream dependencies
        shared = [
            {
                "asset_id": asset_id,
                "asset_name": asset.get("name", ""),
                "upstream_count": len(upstreams),
                "upstreams": upstreams,
            }
            for asset_id, upstreams in dependency_count.items()
            if len(upstreams) > 1
        ]

        # Sort by number of upstreams (most critical first)
        shared.sort(key=lambda x: x["upstream_count"], reverse=True)

        return shared


# Singleton instances
_visualizer: Optional[LineageVisualizer] = None
_path_analyzer: Optional[PathAnalyzer] = None
_impact_analyzer: Optional[ImpactAnalyzer] = None


def get_lineage_visualizer(db: Session) -> LineageVisualizer:
    """Get or create the lineage visualizer instance"""
    return LineageVisualizer(db)


def get_path_analyzer(db: Session) -> PathAnalyzer:
    """Get or create the path analyzer instance"""
    return PathAnalyzer(db)


def get_impact_analyzer(db: Session) -> ImpactAnalyzer:
    """Get or create the impact analyzer instance"""
    return ImpactAnalyzer(db)
