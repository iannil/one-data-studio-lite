"""Tests for report API functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.report import Report, ReportChart, ReportStatus, ChartType


class TestReportModel:
    """Test Report model attributes."""

    def test_report_status_values(self):
        """Test ReportStatus enum values."""
        assert ReportStatus.DRAFT.value == "draft"
        assert ReportStatus.PUBLISHED.value == "published"
        assert ReportStatus.ARCHIVED.value == "archived"

    def test_chart_type_values(self):
        """Test ChartType enum values."""
        assert ChartType.BAR.value == "bar"
        assert ChartType.LINE.value == "line"
        assert ChartType.PIE.value == "pie"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.AREA.value == "area"
        assert ChartType.TABLE.value == "table"
        assert ChartType.STAT.value == "stat"
        assert ChartType.GAUGE.value == "gauge"


class TestReportSchemas:
    """Test Report Pydantic schemas."""

    def test_report_create_schema(self):
        """Test ReportCreate schema validation."""
        from app.schemas.report import ReportCreate

        data = {
            "name": "Test Report",
            "description": "A test report",
            "is_public": False,
            "tags": ["test", "demo"],
            "charts": [
                {
                    "title": "Test Chart",
                    "chart_type": "bar",
                    "nl_query": "Show sales by region",
                }
            ],
        }

        schema = ReportCreate(**data)
        assert schema.name == "Test Report"
        assert schema.is_public is False
        assert len(schema.charts) == 1
        assert schema.charts[0].title == "Test Chart"

    def test_report_create_minimal(self):
        """Test ReportCreate with minimal data."""
        from app.schemas.report import ReportCreate

        data = {"name": "Minimal Report"}
        schema = ReportCreate(**data)
        assert schema.name == "Minimal Report"
        assert schema.charts == []
        assert schema.is_public is False

    def test_report_update_schema(self):
        """Test ReportUpdate schema allows partial updates."""
        from app.schemas.report import ReportUpdate

        data = {"name": "Updated Name"}
        schema = ReportUpdate(**data)
        assert schema.name == "Updated Name"
        assert schema.description is None

    def test_report_chart_create_schema(self):
        """Test ReportChartCreate schema."""
        from app.schemas.report import ReportChartCreate

        data = {
            "title": "Sales Chart",
            "chart_type": "line",
            "query_type": "nl_query",
            "nl_query": "Show monthly sales trend",
            "x_field": "month",
            "y_field": "total_sales",
            "grid_width": 8,
            "grid_height": 6,
        }

        schema = ReportChartCreate(**data)
        assert schema.title == "Sales Chart"
        assert schema.chart_type == "line"
        assert schema.grid_width == 8


class TestReportChartValidation:
    """Test ReportChart validation rules."""

    def test_valid_chart_types(self):
        """Test that all valid chart types are accepted."""
        from app.schemas.report import ReportChartCreate

        valid_types = ["bar", "line", "pie", "scatter", "area", "table", "stat", "gauge"]

        for chart_type in valid_types:
            schema = ReportChartCreate(
                title="Test Chart",
                chart_type=chart_type,
            )
            assert schema.chart_type == chart_type

    def test_invalid_chart_type_rejected(self):
        """Test that invalid chart types are rejected."""
        from app.schemas.report import ReportChartCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ReportChartCreate(
                title="Test Chart",
                chart_type="invalid_type",
            )

    def test_valid_query_types(self):
        """Test that valid query types are accepted."""
        from app.schemas.report import ReportChartCreate

        valid_types = ["nl_query", "sql_query", "asset"]

        for query_type in valid_types:
            schema = ReportChartCreate(
                title="Test Chart",
                chart_type="bar",
                query_type=query_type,
            )
            assert schema.query_type == query_type


class TestReportListResponse:
    """Test ReportListResponse schema."""

    def test_report_list_response(self):
        """Test ReportListResponse structure."""
        from app.schemas.report import ReportListResponse, ReportResponse

        response = ReportListResponse(
            items=[],
            total=0,
        )
        assert response.items == []
        assert response.total == 0


class TestReportRefreshResponse:
    """Test ReportRefreshResponse schema."""

    def test_report_refresh_response(self):
        """Test ReportRefreshResponse structure."""
        from app.schemas.report import ReportRefreshResponse

        response = ReportRefreshResponse(
            report_id=uuid.uuid4(),
            refreshed_charts=3,
            failed_charts=1,
            errors=[{"chart_id": "abc", "error": "Query failed"}],
            refreshed_at=datetime.now(timezone.utc),
        )
        assert response.refreshed_charts == 3
        assert response.failed_charts == 1
        assert len(response.errors) == 1
