"""Tests for data service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models import AssetAccess, DataAsset, DataSource
from app.models.asset import AccessLevel, AssetType
from app.services.data_service import DataService, RateLimitExceeded


class TestDataService:
    """Test suite for DataService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a DataService instance with mock database."""
        svc = DataService(mock_db)
        svc._rate_limit_cache.clear()
        return svc

    @pytest.fixture
    def sample_asset(self):
        """Create a sample DataAsset for testing."""
        asset = MagicMock(spec=DataAsset)
        asset.id = uuid.uuid4()
        asset.name = "Test Asset"
        asset.description = "Test data asset"
        asset.asset_type = AssetType.TABLE
        asset.source_table = "test_table"
        asset.source_schema = "public"
        asset.access_level = AccessLevel.INTERNAL
        asset.is_active = True
        asset.usage_count = 0
        return asset

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 22],
            "status": ["active", "inactive", "active", "pending", "active"],
        })


class TestDataQuery(TestDataService):
    """Test data query operations."""

    def test_apply_query_params_filter_eq(self, service, sample_dataframe):
        """Test filtering with eq operator."""
        query_params = {
            "filters": [{"column": "status", "operator": "eq", "value": "active"}]
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 3
        assert all(result["status"] == "active")

    def test_apply_query_params_filter_gt(self, service, sample_dataframe):
        """Test filtering with gt operator."""
        query_params = {
            "filters": [{"column": "age", "operator": "gt", "value": 28}]
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 2
        assert all(result["age"] > 28)

    def test_apply_query_params_filter_in(self, service, sample_dataframe):
        """Test filtering with in operator."""
        query_params = {
            "filters": [{"column": "name", "operator": "in", "value": ["Alice", "Bob"]}]
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 2

    def test_apply_query_params_filter_contains(self, service, sample_dataframe):
        """Test filtering with contains operator."""
        query_params = {
            "filters": [{"column": "name", "operator": "contains", "value": "li"}]
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 2
        assert "Alice" in result["name"].values
        assert "Charlie" in result["name"].values

    def test_apply_query_params_sort_asc(self, service, sample_dataframe):
        """Test sorting ascending."""
        query_params = {"sort_by": "age", "sort_order": "asc"}

        result = service._apply_query_params(sample_dataframe, query_params)

        assert result["age"].tolist() == [22, 25, 28, 30, 35]

    def test_apply_query_params_sort_desc(self, service, sample_dataframe):
        """Test sorting descending."""
        query_params = {"sort_by": "age", "sort_order": "desc"}

        result = service._apply_query_params(sample_dataframe, query_params)

        assert result["age"].tolist() == [35, 30, 28, 25, 22]

    def test_apply_query_params_select_columns(self, service, sample_dataframe):
        """Test column selection."""
        query_params = {"columns": ["id", "name"]}

        result = service._apply_query_params(sample_dataframe, query_params)

        assert list(result.columns) == ["id", "name"]

    def test_apply_query_params_combined(self, service, sample_dataframe):
        """Test combined filter, sort, and column selection."""
        query_params = {
            "filters": [{"column": "status", "operator": "eq", "value": "active"}],
            "sort_by": "age",
            "sort_order": "desc",
            "columns": ["name", "age"],
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 3
        assert list(result.columns) == ["name", "age"]
        assert result["age"].tolist() == [35, 25, 22]

    def test_apply_query_params_invalid_column_filter(self, service, sample_dataframe):
        """Test filtering on nonexistent column is ignored."""
        query_params = {
            "filters": [{"column": "nonexistent", "operator": "eq", "value": "test"}]
        }

        result = service._apply_query_params(sample_dataframe, query_params)

        assert len(result) == 5


class TestDataExport(TestDataService):
    """Test data export operations."""

    def test_export_csv(self, service, sample_dataframe):
        """Test CSV export."""
        content, content_type, filename = service._export_dataframe(
            sample_dataframe, "csv", "Test Asset"
        )

        assert content_type == "text/csv"
        assert filename.endswith(".csv")
        assert "Test_Asset_" in filename
        assert "id,name,age,status" in content

    def test_export_json(self, service, sample_dataframe):
        """Test JSON export."""
        content, content_type, filename = service._export_dataframe(
            sample_dataframe, "json", "Test Asset"
        )

        assert content_type == "application/json"
        assert filename.endswith(".json")
        import json
        data = json.loads(content)
        assert len(data) == 5
        assert data[0]["name"] == "Alice"

    @pytest.mark.skipif(
        not pytest.importorskip("pyarrow"),
        reason="pyarrow not installed"
    )
    def test_export_parquet(self, service, sample_dataframe):
        """Test Parquet export."""
        content, content_type, filename = service._export_dataframe(
            sample_dataframe, "parquet", "Test Asset"
        )

        assert content_type == "application/octet-stream"
        assert filename.endswith(".parquet")
        assert isinstance(content, bytes)

    def test_export_excel(self, service, sample_dataframe):
        """Test Excel export."""
        content, content_type, filename = service._export_dataframe(
            sample_dataframe, "excel", "Test Asset"
        )

        assert content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert filename.endswith(".xlsx")
        assert isinstance(content, bytes)

    def test_export_invalid_format(self, service, sample_dataframe):
        """Test export with invalid format raises error."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            service._export_dataframe(sample_dataframe, "invalid", "Test")


class TestAssetAccess(TestDataService):
    """Test asset access operations."""

    @pytest.mark.asyncio
    async def test_record_access(self, service, mock_db):
        """Test recording asset access."""
        asset_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await service._record_access(
            asset_id=asset_id,
            user_id=user_id,
            access_type="query",
            details={"limit": 100},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_statistics(self, service, mock_db):
        """Test getting access statistics."""
        access1 = MagicMock(spec=AssetAccess)
        access1.access_type = "query"
        access1.accessed_at = datetime.now(timezone.utc)
        access1.user_id = uuid.uuid4()
        access1.asset_id = uuid.uuid4()

        access2 = MagicMock(spec=AssetAccess)
        access2.access_type = "export"
        access2.accessed_at = datetime.now(timezone.utc)
        access2.user_id = uuid.uuid4()
        access2.asset_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value = [access1, access2]
        mock_db.execute.return_value = mock_result

        result = await service.get_access_statistics(days=30)

        assert result["total_accesses"] == 2
        assert result["access_by_type"]["query"] == 1
        assert result["access_by_type"]["export"] == 1

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, service, mock_db):
        """Test getting nonexistent asset raises error."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Asset not found"):
            await service._get_asset(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_asset_inactive(self, service, mock_db, sample_asset):
        """Test getting inactive asset raises error."""
        sample_asset.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_asset
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not active"):
            await service._get_asset(sample_asset.id)

    @pytest.mark.asyncio
    async def test_get_asset_without_source_table(self, service, mock_db, sample_asset):
        """Test querying asset without source table raises error."""
        sample_asset.source_table = None
        sample_asset.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_asset
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="does not have a source table"):
            await service.query_asset_data(
                asset_id=sample_asset.id,
                user_id=uuid.uuid4(),
            )


class TestRateLimiting(TestDataService):
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self, service):
        """Test that requests within limit are allowed."""
        user_id = uuid.uuid4()

        for _ in range(5):
            result = await service.check_rate_limit(user_id, "query")
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeds_limit(self, service):
        """Test that exceeding limit raises exception."""
        user_id = uuid.uuid4()
        custom_limits = {"requests": 3, "window_seconds": 60}

        for _ in range(3):
            await service.check_rate_limit(user_id, "query", custom_limits)

        with pytest.raises(RateLimitExceeded, match="Rate limit exceeded"):
            await service.check_rate_limit(user_id, "query", custom_limits)

    @pytest.mark.asyncio
    async def test_rate_limit_per_user(self, service):
        """Test that rate limits are per user."""
        user_1 = uuid.uuid4()
        user_2 = uuid.uuid4()
        custom_limits = {"requests": 2, "window_seconds": 60}

        await service.check_rate_limit(user_1, "query", custom_limits)
        await service.check_rate_limit(user_1, "query", custom_limits)

        result = await service.check_rate_limit(user_2, "query", custom_limits)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_per_operation(self, service):
        """Test that rate limits are per operation type."""
        user_id = uuid.uuid4()
        custom_limits = {"requests": 2, "window_seconds": 60}

        await service.check_rate_limit(user_id, "query", custom_limits)
        await service.check_rate_limit(user_id, "query", custom_limits)

        result = await service.check_rate_limit(user_id, "export", custom_limits)
        assert result is True


class TestDesensitization(TestDataService):
    """Test auto-desensitization functionality."""

    @pytest.fixture
    def sensitive_dataframe(self):
        """Create a DataFrame with sensitive data."""
        return pd.DataFrame({
            "id": [1, 2, 3],
            "email": ["alice@example.com", "bob@test.org", "charlie@demo.net"],
            "phone": ["13812345678", "13987654321", "13567891234"],
            "id_card": ["110101199001011234", "310101198505052345", "440101199212123456"],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        })

    def test_detect_sensitive_columns_by_name(self, service, sensitive_dataframe):
        """Test detecting sensitive columns by column name."""
        sensitive_cols = service.detect_sensitive_columns(sensitive_dataframe)

        assert "email" in sensitive_cols
        assert "phone" in sensitive_cols
        assert "id_card" in sensitive_cols

    def test_detect_sensitive_columns_excludes_safe(self, service, sensitive_dataframe):
        """Test that non-sensitive columns are not detected."""
        sensitive_cols = service.detect_sensitive_columns(sensitive_dataframe)

        assert "name" not in sensitive_cols
        assert "age" not in sensitive_cols
        assert "id" not in sensitive_cols

    def test_detect_sensitive_columns_by_pattern(self, service):
        """Test detecting sensitive columns by content patterns."""
        df = pd.DataFrame({
            "contact": ["user1@test.com", "user2@example.org"],
            "mobile": ["138-1234-5678", "139-8765-4321"],
        })

        sensitive_cols = service.detect_sensitive_columns(df)

        assert "contact" in sensitive_cols
        assert "mobile" in sensitive_cols

    def test_apply_desensitization_masks_email(self, service, sensitive_dataframe):
        """Test that emails are properly masked."""
        result = service.apply_auto_desensitization(
            sensitive_dataframe, ["email"]
        )

        assert "@" in result["email"].iloc[0]
        assert "alice@example.com" != result["email"].iloc[0]
        assert "*" in result["email"].iloc[0]

    def test_apply_desensitization_masks_phone(self, service, sensitive_dataframe):
        """Test that phone numbers are properly masked."""
        result = service.apply_auto_desensitization(
            sensitive_dataframe, ["phone"]
        )

        assert "*" in result["phone"].iloc[0]
        assert result["phone"].iloc[0].startswith("138")
        assert result["phone"].iloc[0].endswith("5678")

    def test_apply_desensitization_masks_id_card(self, service, sensitive_dataframe):
        """Test that ID cards are properly masked."""
        result = service.apply_auto_desensitization(
            sensitive_dataframe, ["id_card"]
        )

        assert "*" in result["id_card"].iloc[0]
        assert result["id_card"].iloc[0].endswith("1234")

    def test_apply_desensitization_preserves_non_sensitive(self, service, sensitive_dataframe):
        """Test that non-sensitive columns remain unchanged."""
        result = service.apply_auto_desensitization(
            sensitive_dataframe, ["email", "phone", "id_card"]
        )

        assert list(result["name"]) == ["Alice", "Bob", "Charlie"]
        assert list(result["age"]) == [25, 30, 35]

    def test_apply_desensitization_auto_detect(self, service, sensitive_dataframe):
        """Test auto-detection and masking of sensitive columns."""
        result = service.apply_auto_desensitization(sensitive_dataframe)

        assert "*" in result["email"].iloc[0]
        assert "*" in result["phone"].iloc[0]
        assert "*" in result["id_card"].iloc[0]

    def test_apply_desensitization_handles_null(self, service):
        """Test that null values are handled correctly."""
        df = pd.DataFrame({
            "email": ["alice@test.com", None, "bob@test.com"],
        })

        result = service.apply_auto_desensitization(df, ["email"])

        assert pd.isna(result["email"].iloc[1])
        assert "*" in result["email"].iloc[0]

    def test_mask_email_function(self, service):
        """Test email masking function directly."""
        result = service._mask_email("alice.smith@example.com")

        assert "@example.com" in result
        assert "alice.smith@example.com" != result
        assert "*" in result

    def test_mask_phone_function(self, service):
        """Test phone masking function directly."""
        result = service._mask_phone("13812345678")

        assert result.startswith("138")
        assert result.endswith("5678")
        assert "*" in result

    def test_mask_id_card_function(self, service):
        """Test ID card masking function directly."""
        result = service._mask_id_card("110101199001011234")

        assert result.startswith("110")
        assert result.endswith("1234")
        assert "*" in result

    def test_mask_bank_card_function(self, service):
        """Test bank card masking function directly."""
        result = service._mask_bank_card("6222021234567890")

        assert result.startswith("6222")
        assert result.endswith("7890")
        assert "*" in result

    def test_partial_mask_function(self, service):
        """Test partial masking function directly."""
        result = service._partial_mask("SensitiveData")

        assert result.startswith("Se")
        assert result.endswith("ta")
        assert "*" in result
