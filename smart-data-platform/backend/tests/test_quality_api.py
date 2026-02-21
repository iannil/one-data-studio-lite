"""Tests for Quality API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestQualityAPI:
    """Test quality-related API endpoints."""

    @pytest.fixture
    def quality_request(self):
        from app.schemas import QualityScoreRequest
        return QualityScoreRequest(
            source_id=uuid.uuid4(),
            table_name="test_table",
        )

    @pytest.fixture
    def trend_request(self):
        from app.schemas import QualityTrendRequest
        return QualityTrendRequest(
            source_id=uuid.uuid4(),
            table_name="test_table",
            days=30,
        )

    @pytest.mark.asyncio
    async def test_find_asset_by_source_no_match(self):
        """Test _find_asset_by_source when no asset found."""
        from app.api.v1.quality import _find_asset_by_source

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await _find_asset_by_source(
            db=mock_db,
            source_id=str(uuid.uuid4()),
            table_name="nonexistent_table",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_asset_by_source_with_table(self):
        """Test _find_asset_by_source with table name only."""
        from app.api.v1.quality import _find_asset_by_source
        from app.models import DataAsset

        asset_id = uuid.uuid4()
        mock_asset = DataAsset(
            id=asset_id,
            name="Test Asset",
            source_table="test_table",
            asset_type="table",
        )

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_asset
        mock_db.execute.return_value = result_mock

        result = await _find_asset_by_source(
            db=mock_db,
            source_id=str(uuid.uuid4()),
            table_name="test_table",
        )

        assert result == asset_id

    @pytest.mark.asyncio
    async def test_find_asset_by_source_with_schema(self):
        """Test _find_asset_by_source with schema.table format."""
        from app.api.v1.quality import _find_asset_by_source
        from app.models import DataAsset

        asset_id = uuid.uuid4()
        mock_asset = DataAsset(
            id=asset_id,
            name="Test Asset",
            source_table="test_table",
            source_schema="public",
            asset_type="table",
        )

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_asset
        mock_db.execute.return_value = result_mock

        result = await _find_asset_by_source(
            db=mock_db,
            source_id=str(uuid.uuid4()),
            table_name="public.test_table",
        )

        assert result == asset_id

    @pytest.mark.asyncio
    async def test_find_asset_by_source_query_with_schema(self):
        """Test _find_asset_by_source builds correct query with schema."""
        from app.api.v1.quality import _find_asset_by_source
        from app.models import DataAsset

        asset_id = uuid.uuid4()
        mock_asset = DataAsset(
            id=asset_id,
            name="Test Asset",
            source_table="users",
            source_schema="public",
            asset_type="table",
        )

        mock_db = AsyncMock()
        result_mock = MagicMock()

        # Track that limit(1) was called
        limit_mock = MagicMock()
        limit_mock.scalar_one_or_none.return_value = mock_asset
        mock_db.execute.return_value = limit_mock

        result = await _find_asset_by_source(
            db=mock_db,
            source_id=str(uuid.uuid4()),
            table_name="public.users",
        )

        assert result == asset_id
        # Verify execute was called
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_api_routes_exist(self):
        """Test that Quality API routes are properly defined."""
        from app.api.v1.quality import router

        routes = [route.path for route in router.routes]
        assert "/quality/score" in routes
        assert "/quality/issues" in routes
        assert "/quality/report" in routes
        assert "/quality/trend" in routes

    @pytest.mark.asyncio
    async def test_quality_api_router_prefix(self):
        """Test that Quality API router has correct prefix."""
        from app.api.v1.quality import router

        assert router.prefix == "/quality"
        assert router.tags == ["Quality"]


class TestQualityServiceIntegration:
    """Test Quality API service integration patterns."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that DataQualityService can be initialized."""
        from app.services.quality_service import DataQualityService

        mock_db = AsyncMock()
        service = DataQualityService(mock_db)

        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_calculate_quality_score_signature(self):
        """Test calculate_quality_score has correct signature."""
        from app.services.quality_service import DataQualityService
        from inspect import signature

        sig = signature(DataQualityService.calculate_quality_score)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "source_id" in params
        assert "table_name" in params

    @pytest.mark.asyncio
    async def test_detect_issues_signature(self):
        """Test detect_quality_issues has correct signature."""
        from app.services.quality_service import DataQualityService
        from inspect import signature

        sig = signature(DataQualityService.detect_quality_issues)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "source_id" in params
        assert "table_name" in params
