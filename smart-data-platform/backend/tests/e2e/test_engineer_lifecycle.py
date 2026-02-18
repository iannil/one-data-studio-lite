"""
E2E tests for Data Engineer lifecycle.

Lifecycle stages:
1. Login - User authentication
2. Data Source - CRUD operations
3. Metadata - Scan and analyze
4. Collection - Create and run tasks
5. ETL - Pipeline management

Coverage: /sources, /metadata, /collect, /etl
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models import User


class TestEngineerDataSource:
    """Test data engineer data source management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_sources_unauthorized(self, async_client: AsyncClient):
        """Test listing sources without authentication."""
        response = await async_client.get("/api/v1/sources")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_source_validation(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test creating source with invalid data."""
        response = await async_client.post(
            "/api/v1/sources",
            json={
                "name": "",
                "type": "postgresql",
                "connection_config": {},
            },
            headers=data_engineer_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_source_success(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
        sample_data_source_config: dict,
    ):
        """Test creating a data source successfully."""
        response = await async_client.post(
            "/api/v1/sources",
            json={
                "name": f"Test Source {uuid4().hex[:8]}",
                "description": "E2E test data source",
                "type": "postgresql",
                "connection_config": sample_data_source_config,
            },
            headers=data_engineer_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_list_sources_authenticated(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test listing sources with authentication."""
        response = await async_client.get(
            "/api/v1/sources",
            headers=data_engineer_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_source_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test getting non-existent source."""
        response = await async_client.get(
            f"/api/v1/sources/{uuid4()}",
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_test_source_connection_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test testing connection for non-existent source."""
        response = await async_client.post(
            f"/api/v1/sources/{uuid4()}/test",
            headers=data_engineer_headers,
        )

        assert response.status_code == 404


class TestEngineerMetadata:
    """Test data engineer metadata management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_tables_unauthorized(self, async_client: AsyncClient):
        """Test listing tables without authentication."""
        response = await async_client.get("/api/v1/metadata/tables")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_tables_authenticated(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test listing metadata tables with authentication."""
        response = await async_client.get(
            "/api/v1/metadata/tables",
            headers=data_engineer_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_table_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test getting non-existent table metadata."""
        response = await async_client.get(
            f"/api/v1/metadata/tables/{uuid4()}",
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scan_source_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test scanning non-existent source."""
        response = await async_client.post(
            f"/api/v1/sources/{uuid4()}/scan",
            json={
                "include_row_count": True,
                "table_filter": None,
            },
            headers=data_engineer_headers,
        )

        assert response.status_code == 404


class TestEngineerCollectTask:
    """Test data engineer collection task lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_collect_tasks_unauthorized(self, async_client: AsyncClient):
        """Test listing collection tasks without authentication."""
        response = await async_client.get("/api/v1/collect/tasks")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_collect_tasks_authenticated(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test listing collection tasks with authentication."""
        response = await async_client.get(
            "/api/v1/collect/tasks",
            headers=data_engineer_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_collect_task_source_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test creating collection task with non-existent source."""
        response = await async_client.post(
            "/api/v1/collect/tasks",
            json={
                "name": "Test Collect Task",
                "source_id": str(uuid4()),
                "source_table": "users",
                "target_table": "users_copy",
            },
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_collect_task_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test getting non-existent collection task."""
        response = await async_client.get(
            f"/api/v1/collect/tasks/{uuid4()}",
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_collect_task_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test running non-existent collection task."""
        response = await async_client.post(
            f"/api/v1/collect/tasks/{uuid4()}/run",
            json={"force_full_sync": False},
            headers=data_engineer_headers,
        )

        assert response.status_code == 404


class TestEngineerETLPipeline:
    """Test data engineer ETL pipeline lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_pipelines_unauthorized(self, async_client: AsyncClient):
        """Test listing pipelines without authentication."""
        response = await async_client.get("/api/v1/etl/pipelines")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_pipelines_authenticated(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test listing ETL pipelines with authentication."""
        response = await async_client.get(
            "/api/v1/etl/pipelines",
            headers=data_engineer_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_pipeline_success(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
        sample_etl_pipeline_config: dict,
    ):
        """Test creating an ETL pipeline."""
        response = await async_client.post(
            "/api/v1/etl/pipelines",
            json=sample_etl_pipeline_config,
            headers=data_engineer_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test getting non-existent pipeline."""
        response = await async_client.get(
            f"/api/v1/etl/pipelines/{uuid4()}",
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_step_pipeline_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test adding step to non-existent pipeline."""
        response = await async_client.post(
            f"/api/v1/etl/pipelines/{uuid4()}/steps",
            json={
                "name": "Filter Step",
                "step_type": "filter",
                "config": {"column": "status", "operator": "eq", "value": "active"},
                "order": 0,
                "is_enabled": True,
            },
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_preview_pipeline_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test previewing non-existent pipeline."""
        response = await async_client.post(
            f"/api/v1/etl/pipelines/{uuid4()}/preview",
            params={"rows": 100},
            headers=data_engineer_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_pipeline_not_found(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test running non-existent pipeline."""
        response = await async_client.post(
            f"/api/v1/etl/pipelines/{uuid4()}/run",
            json={"preview_mode": False, "preview_rows": 100},
            headers=data_engineer_headers,
        )

        assert response.status_code == 404


class TestEngineerAISuggestions:
    """Test data engineer AI suggestions lifecycle stage."""

    @pytest.mark.asyncio
    async def test_ai_suggest_rules_unauthorized(self, async_client: AsyncClient):
        """Test AI suggest rules without authentication."""
        response = await async_client.post(
            "/api/v1/etl/ai/suggest-rules",
            json={
                "source_id": str(uuid4()),
                "table_name": "users",
                "sample_size": 100,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ai_predict_fill_unauthorized(self, async_client: AsyncClient):
        """Test AI predict fill without authentication."""
        response = await async_client.post(
            "/api/v1/etl/ai/predict-fill",
            json={
                "source_id": str(uuid4()),
                "table_name": "users",
                "target_column": "age",
                "feature_columns": ["name", "email"],
            },
        )

        assert response.status_code == 401


class TestEngineerLifecycleIntegration:
    """Integration tests for complete data engineer lifecycle."""

    @pytest.mark.asyncio
    async def test_engineer_full_lifecycle(
        self,
        async_client: AsyncClient,
        data_engineer_headers: dict,
    ):
        """Test complete engineer lifecycle: sources -> metadata -> collect -> etl."""
        sources_response = await async_client.get(
            "/api/v1/sources",
            headers=data_engineer_headers,
        )

        tables_response = await async_client.get(
            "/api/v1/metadata/tables",
            headers=data_engineer_headers,
        )

        tasks_response = await async_client.get(
            "/api/v1/collect/tasks",
            headers=data_engineer_headers,
        )

        pipelines_response = await async_client.get(
            "/api/v1/etl/pipelines",
            headers=data_engineer_headers,
        )

        assert sources_response.status_code == 200
        assert tables_response.status_code == 200
        assert tasks_response.status_code == 200
        assert pipelines_response.status_code == 200
