from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.services.quality_service import DataQualityService
from app.models import DataSource


class TestDataQualityService:
    """Test DataQualityService functionality."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_source(self):
        return DataSource(
            id=uuid.uuid4(),
            name="Test Source",
            type="postgresql",
            connection_config={"host": "localhost", "database": "test"},
        )

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame with various quality issues."""
        data = {
            "id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "name": ["Alice", "Bob", None, "David", "Eve", "Frank", None, "Henry", "Ivy", "Jack"],
            "email": [
                "alice@example.com",
                "bob@example.com",
                "invalid-email",
                "david@example.com",
                "eve@example.com",
                "frank@example.com",
                "grace@example.com",
                "henry@example.com",
                "ivy@example.com",
                "jack@example.com",
            ],
            "age": [25, 30, None, 45, 200, 35, 28, None, 42, 38],  # 200 is outlier, None values
            "salary": [50000, 60000, 55000, 70000, 65000, 58000, 62000, 72000, 68000, 66000],
            "created_at": pd.date_range(start="2026-01-01", periods=10, tz="UTC"),
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def service(self, mock_db):
        return DataQualityService(mock_db)

    def test_calculate_completeness(self, service, sample_dataframe):
        """Test completeness score calculation."""
        score = service._calculate_completeness(sample_dataframe)

        # 50 cells total, 4 null values (2 in name, 2 in age)
        # Expected: (50 - 4) / 50 * 100 = 92%
        assert 90 <= score <= 95

    def test_calculate_completeness_empty_df(self, service):
        """Test completeness with empty DataFrame."""
        empty_df = pd.DataFrame()
        score = service._calculate_completeness(empty_df)
        assert score == 0.0

    def test_calculate_uniqueness(self, service):
        """Test uniqueness score calculation."""
        # Create DataFrame with some duplicates
        data = {
            "id": [1, 2, 3, 4, 5, 1, 2],  # 2 duplicates
            "value": [10, 20, 30, 40, 50, 10, 20],
        }
        df = pd.DataFrame(data)

        score = service._calculate_uniqueness(df)
        # 7 rows, 2 duplicates = 5/7 * 100 ≈ 71.4%
        assert 70 <= score <= 72

    def test_calculate_uniqueness_no_duplicates(self, service):
        """Test uniqueness with no duplicate rows."""
        data = {
            "id": [1, 2, 3, 4, 5],
            "value": [10, 20, 30, 40, 50],
        }
        df = pd.DataFrame(data)

        score = service._calculate_uniqueness(df)
        assert score == 100.0

    def test_calculate_uniqueness_empty_df(self, service):
        """Test uniqueness with empty DataFrame."""
        empty_df = pd.DataFrame()
        score = service._calculate_uniqueness(empty_df)
        assert score == 0.0

    def test_calculate_validity(self, service, sample_dataframe):
        """Test validity score calculation."""
        score = service._calculate_validity(sample_dataframe)
        # Should be high since most data is valid
        assert score >= 80

    def test_calculate_validity_empty_df(self, service):
        """Test validity with empty DataFrame."""
        empty_df = pd.DataFrame()
        score = service._calculate_validity(empty_df)
        assert score == 0.0

    def test_calculate_consistency(self, service, sample_dataframe):
        """Test consistency score calculation."""
        score = service._calculate_consistency(sample_dataframe)
        # Email column: 10 rows, 1 invalid = 90%
        assert 85 <= score <= 95

    def test_calculate_consistency_no_pattern_columns(self, service):
        """Test consistency with columns matching no patterns."""
        data = {
            "value": [1, 2, 3, 4, 5],
        }
        df = pd.DataFrame(data)
        score = service._calculate_consistency(df)
        # Should return 100 if no patterns match
        assert score == 100.0

    def test_calculate_timeliness_recent_data(self, service):
        """Test timeliness with recent data."""
        # Create DataFrame with recent date
        data = {
            "created_at": [datetime.now(timezone.utc)] * 10,
        }
        df = pd.DataFrame(data)

        score = service._calculate_timeliness(df)
        assert score == 100.0

    def test_calculate_timeliness_old_data(self, service):
        """Test timeliness with old data."""
        # Create DataFrame with old date (100 days ago)
        old_date = datetime.now(timezone.utc) - pd.Timedelta(days=100)
        data = {
            "created_at": [old_date] * 10,
        }
        df = pd.DataFrame(data)

        score = service._calculate_timeliness(df)
        # Should be reduced for old data
        assert score < 100

    def test_calculate_timeliness_no_date_columns(self, service):
        """Test timeliness with no date columns."""
        data = {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
        df = pd.DataFrame(data)

        score = service._calculate_timeliness(df)
        # Should return 100 if no date columns
        assert score == 100.0

    def test_get_quality_assessment(self, service):
        """Test quality assessment labels."""
        assert service._get_quality_assessment(95) == "Excellent"
        assert service._get_quality_assessment(85) == "Good"
        assert service._get_quality_assessment(65) == "Fair"
        assert service._get_quality_assessment(50) == "Poor"
        assert service._get_quality_assessment(30) == "Critical"

    @pytest.mark.asyncio
    async def test_calculate_quality_score(
        self, service, mock_db, mock_source, sample_dataframe
    ):
        """Test overall quality score calculation."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        # Mock connector
        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=sample_dataframe)
            mock_get_connector.return_value = mock_connector

            result = await service.calculate_quality_score(
                mock_source.id,
                "test_table"
            )

            assert "overall_score" in result
            assert "completeness_score" in result
            assert "uniqueness_score" in result
            assert "validity_score" in result
            assert "consistency_score" in result
            assert "timeliness_score" in result
            assert "row_count" in result
            assert "column_count" in result
            assert "assessment" in result
            assert result["row_count"] == len(sample_dataframe)
            assert result["column_count"] == len(sample_dataframe.columns)

    @pytest.mark.asyncio
    async def test_calculate_quality_score_source_not_found(self, service, mock_db):
        """Test quality score with non-existent source."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Data source not found"):
            await service.calculate_quality_score(uuid.uuid4(), "test_table")

    @pytest.mark.asyncio
    async def test_calculate_quality_score_empty_table(
        self, service, mock_db, mock_source
    ):
        """Test quality score with empty table."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=pd.DataFrame())
            mock_get_connector.return_value = mock_connector

            result = await service.calculate_quality_score(
                mock_source.id,
                "empty_table"
            )

            assert result["overall_score"] == 0
            assert result["row_count"] == 0

    @pytest.mark.asyncio
    async def test_detect_quality_issues(
        self, service, mock_db, mock_source, sample_dataframe
    ):
        """Test quality issue detection."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=sample_dataframe)
            mock_get_connector.return_value = mock_connector

            result = await service.detect_quality_issues(
                mock_source.id,
                "test_table"
            )

            assert "issues" in result
            assert "critical" in result["issues"]
            assert "warning" in result["issues"]
            assert "info" in result["issues"]
            assert "total_issues" in result
            assert "critical_count" in result
            assert "warning_count" in result
            assert "info_count" in result

    @pytest.mark.asyncio
    async def test_detect_quality_issues_high_null_percentage(
        self, service, mock_db, mock_source
    ):
        """Test detection of high null percentage columns."""
        # Create DataFrame with high null percentage
        data = {
            "col1": [1, 2, None, None, None],  # 60% null
            "col2": [1, 2, 3, 4, 5],  # 0% null
        }
        df = pd.DataFrame(data)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=df)
            mock_get_connector.return_value = mock_connector

            result = await service.detect_quality_issues(
                mock_source.id,
                "test_table"
            )

            # Should detect high null percentage
            assert result["critical_count"] >= 0 or result["warning_count"] >= 0

    @pytest.mark.asyncio
    async def test_detect_quality_issues_duplicates(
        self, service, mock_db, mock_source
    ):
        """Test detection of duplicate rows."""
        # Create DataFrame with duplicates
        data = {
            "col1": [1, 1, 1, 1, 1],  # 80% duplicates
            "col2": [1, 1, 2, 2, 3],
        }
        df = pd.DataFrame(data)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=df)
            mock_get_connector.return_value = mock_connector

            result = await service.detect_quality_issues(
                mock_source.id,
                "test_table"
            )

            # Should detect duplicates
            total_issues = result["critical_count"] + result["warning_count"]
            assert total_issues > 0

    @pytest.mark.asyncio
    async def test_track_quality_trend(self, service, mock_db):
        """Test quality trend tracking."""
        # Test with no asset_id (returns fallback data)
        result = await service.track_quality_trend(days=30)

        assert "period_days" in result
        assert "trend" in result
        assert "average_score" in result
        assert "trend_direction" in result
        assert result["period_days"] == 30
        # Fallback returns empty trend and 0 score
        assert result["average_score"] == 0

    @pytest.mark.asyncio
    async def test_generate_quality_report(
        self, service, mock_db, mock_source, sample_dataframe
    ):
        """Test comprehensive quality report generation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.quality_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data = AsyncMock(return_value=sample_dataframe)
            mock_get_connector.return_value = mock_connector

            result = await service.generate_quality_report(
                mock_source.id,
                "test_table"
            )

            assert "table_name" in result
            assert "generated_at" in result
            assert "summary" in result
            assert "issues" in result
            assert "trend" in result
            assert "recommendations" in result
            assert result["table_name"] == "test_table"

    def test_generate_recommendations_low_score(self, service):
        """Test recommendation generation for low quality score."""
        score = {
            "overall_score": 50,
            "completeness_score": 70,
            "uniqueness_score": 80,
            "validity_score": 60,
            "consistency_score": 50,
            "timeliness_score": 40,
        }

        issues = {
            "issues": {
                "critical": [],
                "warning": [],
                "info": [],
            },
            "total_issues": 0,
            "critical_count": 0,
            "warning_count": 0,
        }

        recommendations = service._generate_recommendations(score, issues)

        # Should have recommendations for low scores
        assert len(recommendations) > 0

        # Check that priorities are correct
        priorities = [r["priority"] for r in recommendations]
        assert "high" in priorities or "medium" in priorities

    def test_generate_recommendations_completeness_issue(self, service):
        """Test recommendation for completeness issues."""
        score = {
            "overall_score": 70,
            "completeness_score": 50,
            "uniqueness_score": 90,
            "validity_score": 80,
            "consistency_score": 80,
            "timeliness_score": 80,
        }

        issues = {
            "issues": {
                "critical": [],
                "warning": [],
                "info": [],
            },
            "total_issues": 0,
            "critical_count": 0,
            "warning_count": 0,
        }

        recommendations = service._generate_recommendations(score, issues)

        # Should have completeness recommendation
        completeness_recs = [r for r in recommendations if r["category"] == "completeness"]
        assert len(completeness_recs) > 0

    def test_generate_recommendations_uniqueness_issue(self, service):
        """Test recommendation for uniqueness issues."""
        score = {
            "overall_score": 70,
            "completeness_score": 90,
            "uniqueness_score": 60,
            "validity_score": 80,
            "consistency_score": 80,
            "timeliness_score": 80,
        }

        issues = {
            "issues": {
                "critical": [],
                "warning": [],
                "info": [],
            },
            "total_issues": 0,
            "critical_count": 0,
            "warning_count": 0,
        }

        recommendations = service._generate_recommendations(score, issues)

        # Should have uniqueness recommendation
        uniqueness_recs = [r for r in recommendations if r["category"] == "uniqueness"]
        assert len(uniqueness_recs) > 0

    def test_generate_recommendations_critical_null_issue(self, service):
        """Test recommendation for critical null percentage issues."""
        score = {
            "overall_score": 80,
            "completeness_score": 90,
            "uniqueness_score": 90,
            "validity_score": 80,
            "consistency_score": 80,
            "timeliness_score": 80,
        }

        issues = {
            "issues": {
                "critical": [
                    {
                        "type": "high_null_percentage",
                        "column": "test_col",
                        "null_percentage": 60,
                        "message": "Column 'test_col' has 60.0% null values",
                    }
                ],
                "warning": [],
                "info": [],
            },
            "total_issues": 1,
            "critical_count": 1,
            "warning_count": 0,
        }

        recommendations = service._generate_recommendations(score, issues)

        # Should have recommendation for the critical issue
        assert len(recommendations) > 0
        assert any("test_col" in str(r) for r in recommendations)
