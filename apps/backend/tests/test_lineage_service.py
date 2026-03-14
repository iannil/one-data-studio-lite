"""Tests for lineage service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lineage import (
    LineageNode,
    LineageEdge,
    LineageNodeType,
    LineageEdgeType,
)
from app.services.lineage_service import LineageService


class TestLineageService:
    """Test suite for LineageService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a LineageService instance with mock database."""
        return LineageService(mock_db)

    @pytest.fixture
    def sample_node(self):
        """Create a sample LineageNode for testing."""
        node = MagicMock(spec=LineageNode)
        node.id = uuid.uuid4()
        node.node_type = LineageNodeType.DATA_ASSET
        node.reference_id = uuid.uuid4()
        node.reference_table = "data_assets"
        node.name = "Test Node"
        node.description = "Test lineage node"
        node.metadata = {"key": "value"}
        node.outgoing_edges = []
        node.incoming_edges = []
        return node

    @pytest.fixture
    def sample_edge(self, sample_node):
        """Create a sample LineageEdge for testing."""
        edge = MagicMock(spec=LineageEdge)
        edge.id = uuid.uuid4()
        edge.source_node_id = uuid.uuid4()
        edge.target_node_id = sample_node.id
        edge.edge_type = LineageEdgeType.PRODUCES
        edge.description = "Test edge"
        edge.transformation_details = None
        return edge

    @pytest.mark.asyncio
    async def test_get_or_create_node_creates_new(self, service, mock_db):
        """Test creating a new lineage node when none exists."""
        reference_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_or_create_node(
            node_type=LineageNodeType.DATA_SOURCE,
            reference_id=reference_id,
            reference_table="data_sources",
            name="Test Source",
            description="A test data source",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_node_returns_existing(
        self, service, mock_db, sample_node
    ):
        """Test returning existing node when one exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_node
        mock_db.execute.return_value = mock_result

        result = await service.get_or_create_node(
            node_type=LineageNodeType.DATA_ASSET,
            reference_id=sample_node.reference_id,
            reference_table="data_assets",
            name="Updated Name",
        )

        assert sample_node.name == "Updated Name"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_edge_creates_new(self, service, mock_db):
        """Test creating a new edge when none exists."""
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.create_edge(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=LineageEdgeType.TRANSFORMS,
            description="Test transformation",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_edge_updates_existing(self, service, mock_db, sample_edge):
        """Test updating existing edge when one exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_edge
        mock_db.execute.return_value = mock_result

        result = await service.create_edge(
            source_node_id=sample_edge.source_node_id,
            target_node_id=sample_edge.target_node_id,
            edge_type=LineageEdgeType.COLLECTS_FROM,
            description="Updated description",
        )

        assert sample_edge.edge_type == LineageEdgeType.COLLECTS_FROM
        assert sample_edge.description == "Updated description"
        mock_db.commit.assert_called_once()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_upstream_returns_graph(self, service, mock_db, sample_node):
        """Test getting upstream nodes returns correct graph structure."""
        upstream_node = MagicMock(spec=LineageNode)
        upstream_node.id = uuid.uuid4()
        upstream_node.node_type = LineageNodeType.DATA_SOURCE
        upstream_node.name = "Upstream Source"
        upstream_node.description = "Source node"
        upstream_node.reference_id = uuid.uuid4()
        upstream_node.reference_table = "data_sources"
        upstream_node.metadata = None

        edge = MagicMock(spec=LineageEdge)
        edge.id = uuid.uuid4()
        edge.source_node_id = upstream_node.id
        edge.target_node_id = sample_node.id
        edge.edge_type = LineageEdgeType.PRODUCES
        edge.description = "Produces asset"
        edge.transformation_details = None

        node_result_1 = MagicMock()
        node_result_1.scalar_one_or_none.return_value = sample_node

        edges_result = MagicMock()
        edges_result.scalars.return_value = [edge]

        node_result_2 = MagicMock()
        node_result_2.scalar_one_or_none.return_value = upstream_node

        edges_result_2 = MagicMock()
        edges_result_2.scalars.return_value = []

        mock_db.execute.side_effect = [
            node_result_1,
            edges_result,
            node_result_2,
            edges_result_2,
        ]

        result = await service.get_upstream(sample_node.id, depth=2)

        assert "nodes" in result
        assert "edges" in result
        assert result["root_node_id"] == str(sample_node.id)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    @pytest.mark.asyncio
    async def test_get_downstream_returns_graph(self, service, mock_db, sample_node):
        """Test getting downstream nodes returns correct graph structure."""
        downstream_node = MagicMock(spec=LineageNode)
        downstream_node.id = uuid.uuid4()
        downstream_node.node_type = LineageNodeType.DATA_ASSET
        downstream_node.name = "Downstream Asset"
        downstream_node.description = "Downstream node"
        downstream_node.reference_id = uuid.uuid4()
        downstream_node.reference_table = "data_assets"
        downstream_node.metadata = None

        edge = MagicMock(spec=LineageEdge)
        edge.id = uuid.uuid4()
        edge.source_node_id = sample_node.id
        edge.target_node_id = downstream_node.id
        edge.edge_type = LineageEdgeType.PRODUCES
        edge.description = "Produces downstream"
        edge.transformation_details = None

        node_result_1 = MagicMock()
        node_result_1.scalar_one_or_none.return_value = sample_node

        edges_result = MagicMock()
        edges_result.scalars.return_value = [edge]

        node_result_2 = MagicMock()
        node_result_2.scalar_one_or_none.return_value = downstream_node

        edges_result_2 = MagicMock()
        edges_result_2.scalars.return_value = []

        mock_db.execute.side_effect = [
            node_result_1,
            edges_result,
            node_result_2,
            edges_result_2,
        ]

        result = await service.get_downstream(sample_node.id, depth=2)

        assert "nodes" in result
        assert "edges" in result
        assert result["root_node_id"] == str(sample_node.id)

    @pytest.mark.asyncio
    async def test_impact_analysis(self, service, mock_db, sample_node):
        """Test impact analysis returns affected entities."""
        downstream_asset = MagicMock(spec=LineageNode)
        downstream_asset.id = uuid.uuid4()
        downstream_asset.node_type = LineageNodeType.DATA_ASSET
        downstream_asset.name = "Affected Asset"
        downstream_asset.description = "This asset is affected"
        downstream_asset.reference_id = uuid.uuid4()
        downstream_asset.reference_table = "data_assets"
        downstream_asset.metadata = None

        downstream_pipeline = MagicMock(spec=LineageNode)
        downstream_pipeline.id = uuid.uuid4()
        downstream_pipeline.node_type = LineageNodeType.ETL_PIPELINE
        downstream_pipeline.name = "Affected Pipeline"
        downstream_pipeline.description = "This pipeline is affected"
        downstream_pipeline.reference_id = uuid.uuid4()
        downstream_pipeline.reference_table = "etl_pipelines"
        downstream_pipeline.metadata = None

        edge_1 = MagicMock(spec=LineageEdge)
        edge_1.id = uuid.uuid4()
        edge_1.source_node_id = sample_node.id
        edge_1.target_node_id = downstream_asset.id
        edge_1.edge_type = LineageEdgeType.PRODUCES
        edge_1.description = None
        edge_1.transformation_details = None

        edge_2 = MagicMock(spec=LineageEdge)
        edge_2.id = uuid.uuid4()
        edge_2.source_node_id = sample_node.id
        edge_2.target_node_id = downstream_pipeline.id
        edge_2.edge_type = LineageEdgeType.DEPENDS_ON
        edge_2.description = None
        edge_2.transformation_details = None

        lineage_node_result = MagicMock()
        lineage_node_result.scalar_one_or_none.return_value = sample_node

        node_result_1 = MagicMock()
        node_result_1.scalar_one_or_none.return_value = sample_node

        edges_result = MagicMock()
        edges_result.scalars.return_value = [edge_1, edge_2]

        node_result_2 = MagicMock()
        node_result_2.scalar_one_or_none.return_value = downstream_asset

        edges_result_2 = MagicMock()
        edges_result_2.scalars.return_value = []

        node_result_3 = MagicMock()
        node_result_3.scalar_one_or_none.return_value = downstream_pipeline

        edges_result_3 = MagicMock()
        edges_result_3.scalars.return_value = []

        mock_db.execute.side_effect = [
            lineage_node_result,
            node_result_1,
            edges_result,
            node_result_2,
            edges_result_2,
            node_result_3,
            edges_result_3,
        ]

        result = await service.impact_analysis(sample_node.reference_id)

        assert "source_asset_id" in result
        assert "impacted_assets" in result
        assert "impacted_pipelines" in result
        assert "total_impacted" in result
        assert "lineage_graph" in result

    @pytest.mark.asyncio
    async def test_get_global_graph(self, service, mock_db):
        """Test getting global lineage graph."""
        node_1 = MagicMock(spec=LineageNode)
        node_1.id = uuid.uuid4()
        node_1.node_type = LineageNodeType.DATA_SOURCE
        node_1.name = "Source 1"
        node_1.description = None
        node_1.reference_id = uuid.uuid4()
        node_1.reference_table = "data_sources"
        node_1.metadata = None

        node_2 = MagicMock(spec=LineageNode)
        node_2.id = uuid.uuid4()
        node_2.node_type = LineageNodeType.DATA_ASSET
        node_2.name = "Asset 1"
        node_2.description = None
        node_2.reference_id = uuid.uuid4()
        node_2.reference_table = "data_assets"
        node_2.metadata = None

        edge = MagicMock(spec=LineageEdge)
        edge.id = uuid.uuid4()
        edge.source_node_id = node_1.id
        edge.target_node_id = node_2.id
        edge.edge_type = LineageEdgeType.PRODUCES
        edge.description = None
        edge.transformation_details = None

        nodes_result = MagicMock()
        nodes_result.scalars.return_value = [node_1, node_2]

        edges_result = MagicMock()
        edges_result.scalars.return_value = [edge]

        mock_db.execute.side_effect = [nodes_result, edges_result]

        result = await service.get_global_graph(limit=100)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    @pytest.mark.asyncio
    async def test_build_lineage_creates_nodes(self, service, mock_db):
        """Test building lineage creates nodes from existing data."""
        mock_sources_result = MagicMock()
        mock_sources_result.scalars.return_value = []

        mock_tasks_result = MagicMock()
        mock_tasks_result.scalars.return_value = []

        mock_pipelines_result = MagicMock()
        mock_pipelines_result.scalars.return_value = []

        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            mock_sources_result,
            mock_tasks_result,
            mock_pipelines_result,
            mock_assets_result,
        ]

        result = await service.build_lineage(rebuild_all=False)

        assert "nodes_created" in result
        assert "edges_created" in result
        assert "errors" in result


class TestLineageNodeType:
    """Test LineageNodeType enum values."""

    def test_node_types_exist(self):
        """Test that all expected node types exist."""
        assert LineageNodeType.DATA_SOURCE.value == "data_source"
        assert LineageNodeType.COLLECT_TASK.value == "collect_task"
        assert LineageNodeType.ETL_PIPELINE.value == "etl_pipeline"
        assert LineageNodeType.DATA_ASSET.value == "data_asset"
        assert LineageNodeType.EXTERNAL.value == "external"


class TestLineageEdgeType:
    """Test LineageEdgeType enum values."""

    def test_edge_types_exist(self):
        """Test that all expected edge types exist."""
        assert LineageEdgeType.COLLECTS_FROM.value == "collects_from"
        assert LineageEdgeType.TRANSFORMS.value == "transforms"
        assert LineageEdgeType.PRODUCES.value == "produces"
        assert LineageEdgeType.DEPENDS_ON.value == "depends_on"
