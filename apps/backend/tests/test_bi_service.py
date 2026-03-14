"""Tests for BI service and Superset integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.bi_service import (
    BIService,
    SupersetClient,
    SupersetAPIError,
)


class TestSupersetClient:
    """Tests for Superset API client."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        with patch("app.services.bi_service.httpx.AsyncClient") as mock:
            yield mock

    @pytest.fixture
    def superset_client(self):
        """Create a SupersetClient instance."""
        return SupersetClient(
            base_url="http://localhost:8088",
            username="admin",
            password="admin",
        )

    @pytest.mark.asyncio
    async def test_login_success(self, superset_client, mock_httpx_client):
        """Test successful login."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_httpx_client.return_value = mock_client_instance

        token = await superset_client.login()

        assert token == "test_token"
        assert superset_client._access_token == "test_token"

    @pytest.mark.asyncio
    async def test_login_failure(self, superset_client, mock_httpx_client):
        """Test login failure raises SupersetAPIError."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.HTTPStatusError(
            message="401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_httpx_client.return_value = mock_client_instance

        with pytest.raises(SupersetAPIError) as exc_info:
            await superset_client.login()

        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_health_healthy(self, superset_client, mock_httpx_client):
        """Test health check when Superset is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_httpx_client.return_value = mock_client_instance

        result = await superset_client.check_health()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_health_unreachable(self, superset_client, mock_httpx_client):
        """Test health check when Superset is unreachable."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("Connection refused")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_httpx_client.return_value = mock_client_instance

        result = await superset_client.check_health()

        assert result["status"] == "unreachable"
        assert "Connection refused" in result["error"]


class TestBIService:
    """Tests for BI service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def bi_service(self, mock_db):
        """Create a BIService instance with mocked dependencies."""
        return BIService(mock_db)

    @pytest.mark.asyncio
    async def test_sync_table_to_superset_create(self, bi_service):
        """Test syncing a new table to Superset."""
        with patch.object(bi_service.superset, "list_databases", return_value=[]):
            with patch.object(bi_service.superset, "create_database", return_value=1):
                with patch.object(bi_service.superset, "list_datasets", return_value=[]):
                    with patch.object(bi_service.superset, "create_dataset", return_value=123):
                        with patch.object(bi_service.superset, "get_dataset", return_value={
                            "result": {"columns": [{"column_name": "id"}]}
                        }):
                            result = await bi_service.sync_table_to_superset("test_table")

        assert result["success"] is True
        assert result["action"] == "created"
        assert result["dataset_id"] == 123

    @pytest.mark.asyncio
    async def test_sync_table_to_superset_refresh(self, bi_service):
        """Test syncing an existing table (refresh)."""
        existing_dataset = {
            "id": 123,
            "table_name": "test_table",
            "schema": "public",
        }

        with patch.object(bi_service.superset, "list_databases", return_value=[
            {"id": 1, "database_name": "SmartDataPlatform"}
        ]):
            with patch.object(bi_service.superset, "list_datasets", return_value=[existing_dataset]):
                with patch.object(bi_service.superset, "refresh_dataset", return_value=True):
                    with patch.object(bi_service.superset, "get_dataset", return_value={
                        "result": {"columns": []}
                    }):
                        bi_service._database_id = 1
                        result = await bi_service.sync_table_to_superset("test_table")

        assert result["success"] is True
        assert result["action"] == "refreshed"

    @pytest.mark.asyncio
    async def test_get_sync_status_synced(self, bi_service):
        """Test getting sync status for a synced table."""
        existing_dataset = {
            "id": 123,
            "table_name": "test_table",
            "schema": "public",
            "changed_on": "2024-01-01T00:00:00",
        }

        with patch.object(bi_service.superset, "list_databases", return_value=[
            {"id": 1, "database_name": "SmartDataPlatform"}
        ]):
            with patch.object(bi_service.superset, "list_datasets", return_value=[existing_dataset]):
                bi_service._database_id = 1
                result = await bi_service.get_sync_status("test_table")

        assert result["synced"] is True
        assert result["dataset_id"] == 123

    @pytest.mark.asyncio
    async def test_get_sync_status_not_synced(self, bi_service):
        """Test getting sync status for a non-synced table."""
        with patch.object(bi_service.superset, "list_databases", return_value=[
            {"id": 1, "database_name": "SmartDataPlatform"}
        ]):
            with patch.object(bi_service.superset, "list_datasets", return_value=[]):
                bi_service._database_id = 1
                result = await bi_service.get_sync_status("nonexistent_table")

        assert result["synced"] is False

    @pytest.mark.asyncio
    async def test_list_synced_datasets(self, bi_service):
        """Test listing synced datasets."""
        datasets = [
            {"id": 1, "table_name": "table1", "schema": "public"},
            {"id": 2, "table_name": "table2", "schema": "public"},
        ]

        with patch.object(bi_service.superset, "list_databases", return_value=[
            {"id": 1, "database_name": "SmartDataPlatform"}
        ]):
            with patch.object(bi_service.superset, "list_datasets", return_value=datasets):
                bi_service._database_id = 1
                result = await bi_service.list_synced_datasets()

        assert len(result) == 2
        assert result[0]["table_name"] == "table1"

    @pytest.mark.asyncio
    async def test_get_superset_status(self, bi_service):
        """Test getting Superset connection status."""
        with patch.object(bi_service.superset, "check_health", return_value={"status": "healthy"}):
            with patch.object(bi_service.superset, "login", return_value="token"):
                with patch.object(bi_service.superset, "list_databases", return_value=[]):
                    result = await bi_service.get_superset_status()

        assert result["health"] == "healthy"
        assert result["authenticated"] is True

    @pytest.mark.asyncio
    async def test_delete_dataset(self, bi_service):
        """Test deleting a dataset."""
        existing_dataset = {
            "id": 123,
            "table_name": "test_table",
            "schema": "public",
        }

        with patch.object(bi_service.superset, "list_databases", return_value=[
            {"id": 1, "database_name": "SmartDataPlatform"}
        ]):
            with patch.object(bi_service.superset, "list_datasets", return_value=[existing_dataset]):
                with patch.object(bi_service.superset, "delete_dataset", return_value=True):
                    bi_service._database_id = 1
                    result = await bi_service.delete_dataset("test_table")

        assert result is True


class TestSupersetAPIError:
    """Tests for SupersetAPIError exception."""

    def test_error_with_status_code(self):
        """Test error includes status code."""
        error = SupersetAPIError("Test error", status_code=403)
        assert error.message == "Test error"
        assert error.status_code == 403

    def test_error_without_status_code(self):
        """Test error without status code."""
        error = SupersetAPIError("Connection failed")
        assert error.message == "Connection failed"
        assert error.status_code is None
