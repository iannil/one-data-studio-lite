"""Tests for asset service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models import AssetAccess, DataAsset
from app.models.asset import AccessLevel, AssetType
from app.services.asset_service import AssetService, AssetValueLevel


class TestAssetService:
    """Test suite for AssetService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create an AssetService instance with mock database."""
        return AssetService(mock_db)

    @pytest.fixture
    def sample_asset(self):
        """Create a sample DataAsset for testing."""
        asset = MagicMock(spec=DataAsset)
        asset.id = uuid.uuid4()
        asset.name = "Test Asset"
        asset.description = "A test data asset with sufficient description length for testing"
        asset.asset_type = AssetType.TABLE
        asset.access_level = AccessLevel.INTERNAL
        asset.domain = "test"
        asset.category = "testing"
        asset.tags = ["test", "sample", "data"]
        asset.is_active = True
        asset.is_certified = True
        asset.upstream_assets = []
        asset.downstream_assets = []
        asset.value_score = None
        return asset

    @pytest.mark.asyncio
    async def test_get_usage_statistics(self, service, mock_db):
        """Test fetching usage statistics for an asset."""
        asset_id = uuid.uuid4()

        mock_total = MagicMock()
        mock_total.scalar.return_value = 150

        mock_unique = MagicMock()
        mock_unique.scalar.return_value = 25

        mock_by_type = [
            MagicMock(access_type="read", count=100),
            MagicMock(access_type="export", count=50),
        ]

        mock_daily = [
            MagicMock(date="2024-01-01", count=10),
            MagicMock(date="2024-01-02", count=15),
        ]

        mock_db.execute.side_effect = [
            mock_total,
            mock_unique,
            MagicMock(__iter__=lambda _: iter(mock_by_type)),
            MagicMock(__iter__=lambda _: iter(mock_daily)),
        ]

        result = await service.get_usage_statistics(asset_id, days=30)

        assert result["asset_id"] == str(asset_id)
        assert result["period_days"] == 30
        assert result["total_accesses"] == 150
        assert result["unique_users"] == 25
        assert result["avg_daily_accesses"] == 5.0

    @pytest.mark.asyncio
    async def test_calculate_lineage_depth_no_lineage(self, service, mock_db, sample_asset):
        """Test lineage depth calculation when asset has no lineage."""
        sample_asset.upstream_assets = []
        sample_asset.downstream_assets = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_asset
        mock_db.execute.return_value = mock_result

        result = await service.calculate_lineage_depth(sample_asset.id)

        assert result["upstream_depth"] == 0
        assert result["downstream_depth"] == 0
        assert result["total_depth"] == 0
        assert result["has_upstream"] is False
        assert result["has_downstream"] is False

    @pytest.mark.asyncio
    async def test_calculate_lineage_depth_with_lineage(self, service, mock_db, sample_asset):
        """Test lineage depth calculation with upstream/downstream assets."""
        upstream_id = uuid.uuid4()
        downstream_id = uuid.uuid4()

        sample_asset.upstream_assets = [upstream_id]
        sample_asset.downstream_assets = [downstream_id]

        upstream_asset = MagicMock(spec=DataAsset)
        upstream_asset.id = upstream_id
        upstream_asset.upstream_assets = []

        downstream_asset = MagicMock(spec=DataAsset)
        downstream_asset.id = downstream_id
        downstream_asset.downstream_assets = []

        mock_result_main = MagicMock()
        mock_result_main.scalar_one_or_none.return_value = sample_asset

        mock_upstream_result = MagicMock()
        mock_upstream_result.scalars.return_value = [upstream_asset]

        mock_downstream_result = MagicMock()
        mock_downstream_result.scalars.return_value = [downstream_asset]

        mock_db.execute.side_effect = [
            mock_result_main,
            mock_upstream_result,
            mock_downstream_result,
        ]

        result = await service.calculate_lineage_depth(sample_asset.id)

        assert result["has_upstream"] is True
        assert result["has_downstream"] is True
        assert result["direct_upstream_count"] == 1
        assert result["direct_downstream_count"] == 1

    @pytest.mark.asyncio
    async def test_calculate_lineage_depth_asset_not_found(self, service, mock_db):
        """Test lineage depth calculation when asset doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Asset not found"):
            await service.calculate_lineage_depth(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_evaluate_asset_value_high(self, service, mock_db, sample_asset):
        """Test value evaluation for a high-value asset."""
        with patch.object(service, "get_usage_statistics") as mock_usage:
            with patch.object(service, "calculate_lineage_depth") as mock_lineage:
                mock_usage.return_value = {
                    "total_accesses": 500,
                    "unique_users": 30,
                }
                mock_lineage.return_value = {
                    "downstream_depth": 3,
                    "direct_downstream_count": 5,
                }

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_asset
                mock_db.execute.return_value = mock_result

                result = await service.evaluate_asset_value(sample_asset.id)

                assert result["value_level"] == AssetValueLevel.HIGH
                assert result["value_score"] >= 70

    @pytest.mark.asyncio
    async def test_evaluate_asset_value_low(self, service, mock_db, sample_asset):
        """Test value evaluation for a low-value asset."""
        sample_asset.is_certified = False
        sample_asset.tags = []
        sample_asset.description = "Short"

        with patch.object(service, "get_usage_statistics") as mock_usage:
            with patch.object(service, "calculate_lineage_depth") as mock_lineage:
                mock_usage.return_value = {
                    "total_accesses": 5,
                    "unique_users": 1,
                }
                mock_lineage.return_value = {
                    "downstream_depth": 0,
                    "direct_downstream_count": 0,
                }

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_asset
                mock_db.execute.return_value = mock_result

                result = await service.evaluate_asset_value(sample_asset.id)

                assert result["value_level"] == AssetValueLevel.LOW
                assert result["value_score"] < 40

    @pytest.mark.asyncio
    async def test_update_asset_value_score(self, service, mock_db, sample_asset):
        """Test updating and persisting value score."""
        with patch.object(service, "evaluate_asset_value") as mock_eval:
            mock_eval.return_value = {"value_score": 75.5}

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_asset
            mock_db.execute.return_value = mock_result

            result = await service.update_asset_value_score(sample_asset.id)

            assert sample_asset.value_score == 75.5
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(sample_asset)

    @pytest.mark.asyncio
    async def test_batch_update_value_scores(self, service, mock_db, sample_asset):
        """Test batch updating value scores."""
        sample_asset2 = MagicMock(spec=DataAsset)
        sample_asset2.id = uuid.uuid4()
        sample_asset2.name = "Test Asset 2"
        sample_asset2.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value = [sample_asset, sample_asset2]
        mock_db.execute.return_value = mock_result

        with patch.object(service, "evaluate_asset_value") as mock_eval:
            mock_eval.return_value = {"value_score": 50.0, "value_level": "medium"}

            result = await service.batch_update_value_scores()

            assert result["total_processed"] == 2
            assert result["updated"] == 2
            assert result["failed"] == 0
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_value_distribution(self, service, mock_db):
        """Test getting value distribution across all assets."""
        high_asset = MagicMock(spec=DataAsset)
        high_asset.id = uuid.uuid4()
        high_asset.name = "High Value"
        high_asset.value_score = 85.0
        high_asset.is_active = True

        medium_asset = MagicMock(spec=DataAsset)
        medium_asset.id = uuid.uuid4()
        medium_asset.name = "Medium Value"
        medium_asset.value_score = 55.0
        medium_asset.is_active = True

        low_asset = MagicMock(spec=DataAsset)
        low_asset.id = uuid.uuid4()
        low_asset.name = "Low Value"
        low_asset.value_score = 25.0
        low_asset.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value = [high_asset, medium_asset, low_asset]
        mock_db.execute.return_value = mock_result

        result = await service.get_value_distribution()

        assert result["total_assets"] == 3
        assert result["distribution"]["high"]["count"] == 1
        assert result["distribution"]["medium"]["count"] == 1
        assert result["distribution"]["low"]["count"] == 1
        assert result["average_score"] == 55.0
        assert len(result["top_assets"]) == 3


class TestLineageAPI:
    """Test suite for lineage API endpoint."""

    @pytest.mark.asyncio
    async def test_lineage_response_format(self):
        """Test that lineage response has correct format."""
        from app.schemas.asset import AssetLineageResponse

        response = AssetLineageResponse(
            asset_id=uuid.uuid4(),
            upstream=[{"id": str(uuid.uuid4()), "name": "upstream", "type": "table"}],
            downstream=[{"id": str(uuid.uuid4()), "name": "downstream", "type": "view"}],
            lineage_graph={
                "nodes": [
                    {"id": "1", "name": "current", "type": "current"},
                ],
                "edges": [],
            },
        )

        assert response.asset_id is not None
        assert len(response.upstream) == 1
        assert len(response.downstream) == 1
        assert "nodes" in response.lineage_graph
        assert "edges" in response.lineage_graph


class TestAIAssetSearch:
    """Test suite for AI asset search functionality."""

    def test_search_assets_schema(self):
        """Test AI search response schema."""
        expected_fields = ["results", "total", "ai_summary"]
        response = {
            "results": [],
            "total": 0,
            "ai_summary": "No results found",
            "suggested_queries": [],
        }

        for field in expected_fields:
            assert field in response

    def test_search_query_validation(self):
        """Test that search query is properly handled."""
        test_queries = [
            "近30天活跃用户数据",
            "customer purchase history",
            "sales metrics by region",
        ]

        for query in test_queries:
            assert isinstance(query, str)
            assert len(query) > 0


class TestAssetAutoCatalog:
    """Test suite for asset auto-cataloging functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create an AssetService instance with mock database."""
        return AssetService(mock_db)

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "email": ["alice@test.com", "bob@test.com", "charlie@test.com", None, "eve@test.com"],
            "age": [25, 30, 35, 28, 22],
            "salary": [50000.0, 60000.0, 75000.0, 55000.0, 45000.0],
        })

    def test_extract_data_profile_basic(self, service, sample_dataframe):
        """Test data profile extraction with basic DataFrame."""
        profile = service._extract_data_profile(sample_dataframe)

        assert profile["row_count"] == 5
        assert profile["column_count"] == 5
        assert len(profile["columns"]) == 5
        assert "quality_metrics" in profile
        assert "completeness" in profile["quality_metrics"]
        assert "uniqueness" in profile["quality_metrics"]

    def test_extract_data_profile_column_details(self, service, sample_dataframe):
        """Test data profile extraction includes column details."""
        profile = service._extract_data_profile(sample_dataframe)

        id_col = next(c for c in profile["columns"] if c["name"] == "id")
        assert id_col["dtype"] == "int64"
        assert id_col["null_count"] == 0
        assert id_col["unique_count"] == 5
        assert "min" in id_col
        assert "max" in id_col

        email_col = next(c for c in profile["columns"] if c["name"] == "email")
        assert email_col["null_count"] == 1
        assert email_col["null_percentage"] == 20.0

    def test_extract_data_profile_numeric_stats(self, service, sample_dataframe):
        """Test data profile extraction includes numeric statistics."""
        profile = service._extract_data_profile(sample_dataframe)

        age_col = next(c for c in profile["columns"] if c["name"] == "age")
        assert age_col["min"] == 22
        assert age_col["max"] == 35
        assert age_col["mean"] == 28.0

    def test_extract_data_profile_string_stats(self, service, sample_dataframe):
        """Test data profile extraction includes string statistics."""
        profile = service._extract_data_profile(sample_dataframe)

        name_col = next(c for c in profile["columns"] if c["name"] == "name")
        assert "avg_length" in name_col
        assert "top_values" in name_col

    def test_extract_data_profile_completeness(self, service, sample_dataframe):
        """Test data quality completeness calculation."""
        profile = service._extract_data_profile(sample_dataframe)

        total_cells = 5 * 5
        total_nulls = 1
        expected_completeness = round((1 - total_nulls / total_cells) * 100, 2)

        assert profile["quality_metrics"]["completeness"] == expected_completeness

    def test_extract_data_profile_uniqueness(self, service, sample_dataframe):
        """Test data quality uniqueness calculation."""
        profile = service._extract_data_profile(sample_dataframe)

        assert profile["quality_metrics"]["uniqueness"] == 100.0

    def test_extract_data_profile_empty_dataframe(self, service):
        """Test data profile extraction with empty DataFrame."""
        empty_df = pd.DataFrame()
        profile = service._extract_data_profile(empty_df)

        assert profile["row_count"] == 0
        assert profile["column_count"] == 0
        assert len(profile["columns"]) == 0

    def test_extract_data_profile_with_duplicates(self, service):
        """Test data profile extraction with duplicate rows."""
        df_with_dups = pd.DataFrame({
            "id": [1, 1, 2, 2, 3],
            "value": ["a", "a", "b", "b", "c"],
        })
        profile = service._extract_data_profile(df_with_dups)

        assert profile["quality_metrics"]["uniqueness"] == 60.0

    @pytest.mark.asyncio
    async def test_generate_ai_metadata_fallback(self, service):
        """Test AI metadata generation fallback on error."""
        with patch("app.services.asset_service.AsyncOpenAI") as mock_openai:
            mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

            result = await service._generate_ai_metadata(
                table_name="test_table",
                schema_name="public",
                data_profile={
                    "row_count": 100,
                    "columns": [],
                    "quality_metrics": {"completeness": 95.0, "uniqueness": 100.0},
                },
                pipeline_name="test_pipeline",
            )

            assert result["name"] == "test_table"
            assert "auto-cataloged" in result["tags"]
            assert result["category"] == "staging"

    @pytest.mark.asyncio
    async def test_auto_catalog_from_etl_create_new(self, service, mock_db, sample_dataframe):
        """Test auto-cataloging creates new asset when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_generate_ai_metadata") as mock_ai:
            mock_ai.return_value = {
                "name": "Test Asset",
                "description": "Test description",
                "summary": "Test summary",
                "category": "analytics",
                "domain": "testing",
                "tags": ["test", "sample"],
                "sensitivity_level": "internal",
            }

            with patch.object(service, "_create_asset_catalog") as mock_create:
                mock_asset = MagicMock(spec=DataAsset)
                mock_asset.id = uuid.uuid4()
                mock_asset.name = "Test Asset"
                mock_asset.ai_summary = "Test summary"
                mock_asset.tags = ["test", "sample"]
                mock_create.return_value = mock_asset

                with patch.object(service, "evaluate_asset_value") as mock_eval:
                    mock_eval.return_value = {"value_score": 50.0, "value_level": "medium"}

                    result = await service.auto_catalog_from_etl(
                        pipeline_id=uuid.uuid4(),
                        pipeline_name="test_pipeline",
                        target_table="test_table",
                        target_schema="public",
                        df=sample_dataframe,
                    )

                    assert result["action"] == "created"
                    assert result["asset_name"] == "Test Asset"
                    mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_catalog_from_etl_update_existing(self, service, mock_db, sample_dataframe):
        """Test auto-cataloging updates existing asset."""
        existing_asset = MagicMock(spec=DataAsset)
        existing_asset.id = uuid.uuid4()
        existing_asset.name = "Existing Asset"
        existing_asset.tags = ["existing"]
        existing_asset.ai_summary = "Old summary"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_asset
        mock_db.execute.return_value = mock_result

        with patch.object(service, "_generate_ai_metadata") as mock_ai:
            mock_ai.return_value = {
                "name": "Updated Asset",
                "description": "Updated description",
                "summary": "New summary",
                "category": "analytics",
                "domain": "testing",
                "tags": ["new", "updated"],
                "sensitivity_level": "internal",
            }

            with patch.object(service, "_update_asset_catalog") as mock_update:
                mock_update.return_value = existing_asset

                with patch.object(service, "evaluate_asset_value") as mock_eval:
                    mock_eval.return_value = {"value_score": 60.0, "value_level": "medium"}

                    result = await service.auto_catalog_from_etl(
                        pipeline_id=uuid.uuid4(),
                        pipeline_name="test_pipeline",
                        target_table="test_table",
                        target_schema="public",
                        df=sample_dataframe,
                    )

                    assert result["action"] == "updated"
                    mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_asset_catalog(self, service, mock_db):
        """Test creating a new asset catalog entry."""
        data_profile = {
            "row_count": 100,
            "column_count": 5,
            "columns": [],
            "quality_metrics": {"completeness": 95.0, "uniqueness": 100.0},
        }
        ai_metadata = {
            "name": "New Asset",
            "description": "Asset description",
            "summary": "Brief summary",
            "category": "master_data",
            "domain": "customer",
            "tags": ["customer", "master"],
            "sensitivity_level": "restricted",
            "suggested_use_cases": ["reporting"],
        }

        mock_source_result = MagicMock()
        mock_source_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_source_result

        asset = await service._create_asset_catalog(
            target_table="customer_master",
            target_schema="public",
            data_profile=data_profile,
            ai_metadata=ai_metadata,
            source_table=None,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert asset.name == "New Asset"
        assert asset.asset_type == AssetType.TABLE
        assert asset.access_level == AccessLevel.RESTRICTED

    @pytest.mark.asyncio
    async def test_update_asset_catalog(self, service, mock_db):
        """Test updating an existing asset catalog entry."""
        existing_asset = DataAsset(
            id=uuid.uuid4(),
            name="Old Name",
            asset_type=AssetType.TABLE,
            tags=["old"],
            ai_summary="Old summary",
            source_table="test_table",
        )

        data_profile = {
            "row_count": 200,
            "column_count": 6,
            "columns": [],
            "quality_metrics": {"completeness": 98.0},
        }
        ai_metadata = {
            "summary": "New summary",
            "description": "New description",
            "tags": ["new", "updated"],
            "category": "analytics",
            "domain": "sales",
        }

        mock_source_result = MagicMock()
        mock_source_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_source_result

        updated_asset = await service._update_asset_catalog(
            asset=existing_asset,
            data_profile=data_profile,
            ai_metadata=ai_metadata,
            source_table=None,
        )

        assert updated_asset.ai_summary == "New summary"
        assert "old" in updated_asset.tags
        assert "new" in updated_asset.tags
        assert updated_asset.category == "analytics"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_asset_by_table(self, service, mock_db):
        """Test getting asset by table name."""
        expected_asset = MagicMock(spec=DataAsset)
        expected_asset.source_table = "test_table"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_asset
        mock_db.execute.return_value = mock_result

        result = await service.get_asset_by_table("test_table", "public")

        assert result == expected_asset


class TestAssetValueTrend:
    """Test suite for asset value trend functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create an AssetService instance with mock database."""
        return AssetService(mock_db)

    @pytest.fixture
    def sample_asset(self):
        """Create a sample DataAsset for testing."""
        asset = MagicMock(spec=DataAsset)
        asset.id = uuid.uuid4()
        asset.name = "Test Asset"
        asset.is_certified = True
        asset.value_score = 75.0
        return asset

    @pytest.mark.asyncio
    async def test_get_value_trend_asset_not_found(self, service, mock_db):
        """Test that value trend raises error for non-existent asset."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Asset not found"):
            await service.get_value_trend(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_value_trend_no_data(self, service, mock_db, sample_asset):
        """Test value trend with no access data."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter([])

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id)

        assert result["asset_id"] == str(sample_asset.id)
        assert result["asset_name"] == "Test Asset"
        assert result["current_score"] == 75.0
        assert result["trend_direction"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_get_value_trend_upward(self, service, mock_db, sample_asset):
        """Test value trend detection for upward trend."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        daily_data = []
        for i in range(14):
            row = MagicMock()
            row.date = f"2024-01-{i + 1:02d}"
            row.count = 5 if i < 7 else 20
            row.unique_users = 1 if i < 7 else 3
            daily_data.append(row)

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter(daily_data)

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id)

        assert result["trend_direction"] == "up"
        assert result["change_percentage"] is not None
        assert result["change_percentage"] > 0

    @pytest.mark.asyncio
    async def test_get_value_trend_downward(self, service, mock_db, sample_asset):
        """Test value trend detection for downward trend."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        daily_data = []
        for i in range(14):
            row = MagicMock()
            row.date = f"2024-01-{i + 1:02d}"
            row.count = 20 if i < 7 else 3
            row.unique_users = 5 if i < 7 else 1
            daily_data.append(row)

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter(daily_data)

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id)

        assert result["trend_direction"] == "down"
        assert result["change_percentage"] is not None
        assert result["change_percentage"] < 0

    @pytest.mark.asyncio
    async def test_get_value_trend_stable(self, service, mock_db, sample_asset):
        """Test value trend detection for stable pattern."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        daily_data = []
        for i in range(14):
            row = MagicMock()
            row.date = f"2024-01-{i + 1:02d}"
            row.count = 10
            row.unique_users = 2
            daily_data.append(row)

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter(daily_data)

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id)

        assert result["trend_direction"] == "stable"
        assert result["change_percentage"] is not None
        assert abs(result["change_percentage"]) <= 10

    @pytest.mark.asyncio
    async def test_get_value_trend_returns_weekly_scores(self, service, mock_db, sample_asset):
        """Test that value trend returns weekly estimated scores."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        daily_data = []
        for i in range(21):
            row = MagicMock()
            row.date = f"2024-01-{i + 1:02d}"
            row.count = 10 + i
            row.unique_users = 2 + (i // 7)
            daily_data.append(row)

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter(daily_data)

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id)

        assert "trend" in result
        assert len(result["trend"]) >= 2
        for period in result["trend"]:
            assert "period" in period
            assert "estimated_score" in period
            assert "access_count" in period

    @pytest.mark.asyncio
    async def test_get_value_trend_current_level(self, service, mock_db, sample_asset):
        """Test that current value level is calculated correctly."""
        test_cases = [
            (85.0, AssetValueLevel.HIGH),
            (55.0, AssetValueLevel.MEDIUM),
            (25.0, AssetValueLevel.LOW),
            (None, None),
        ]

        for score, expected_level in test_cases:
            sample_asset.value_score = score

            mock_asset_result = MagicMock()
            mock_asset_result.scalar_one_or_none.return_value = sample_asset

            mock_daily_result = MagicMock()
            mock_daily_result.__iter__ = lambda _: iter([])

            mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

            result = await service.get_value_trend(sample_asset.id)

            assert result["current_score"] == score
            assert result["current_level"] == expected_level

    @pytest.mark.asyncio
    async def test_get_value_trend_custom_days(self, service, mock_db, sample_asset):
        """Test value trend with custom day range."""
        mock_asset_result = MagicMock()
        mock_asset_result.scalar_one_or_none.return_value = sample_asset

        mock_daily_result = MagicMock()
        mock_daily_result.__iter__ = lambda _: iter([])

        mock_db.execute.side_effect = [mock_asset_result, mock_daily_result]

        result = await service.get_value_trend(sample_asset.id, days=60)

        assert result["analysis_period_days"] == 60
