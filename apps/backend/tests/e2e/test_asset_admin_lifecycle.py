"""
E2E tests for Data Asset Admin lifecycle.

Lifecycle stages:
1. Login - User authentication
2. Asset Management - CRUD operations
3. Certification - Certify assets
4. Lineage - Manage data lineage

Coverage: /assets CRUD, /assets/{id}/certify, /assets/{id}/lineage
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models import User


class TestAssetAdminAssetCRUD:
    """Test asset admin asset CRUD lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_assets_unauthorized(self, async_client: AsyncClient):
        """Test listing assets without authentication."""
        response = await async_client.get("/api/v1/assets")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_assets_authenticated(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test listing assets with authentication."""
        response = await async_client.get(
            "/api/v1/assets",
            headers=asset_admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_assets_with_filters(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test listing assets with filters."""
        response = await async_client.get(
            "/api/v1/assets",
            params={
                "category": "master_data",
                "domain": "user",
                "skip": 0,
                "limit": 50,
            },
            headers=asset_admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_asset_success(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
        sample_asset_config: dict,
    ):
        """Test creating a data asset."""
        response = await async_client.post(
            "/api/v1/assets",
            json=sample_asset_config,
            headers=asset_admin_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_asset_invalid_data(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test creating asset with invalid data."""
        response = await async_client.post(
            "/api/v1/assets",
            json={
                "name": "",
                "asset_type": "invalid_type",
            },
            headers=asset_admin_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_asset_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test getting non-existent asset."""
        response = await async_client.get(
            f"/api/v1/assets/{uuid4()}",
            headers=asset_admin_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_asset_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test updating non-existent asset."""
        response = await async_client.patch(
            f"/api/v1/assets/{uuid4()}",
            json={"description": "Updated description"},
            headers=asset_admin_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_asset_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test deleting non-existent asset."""
        response = await async_client.delete(
            f"/api/v1/assets/{uuid4()}",
            headers=asset_admin_headers,
        )

        assert response.status_code == 404


class TestAssetAdminCertification:
    """Test asset admin certification lifecycle stage."""

    @pytest.mark.asyncio
    async def test_certify_asset_unauthorized(self, async_client: AsyncClient):
        """Test certifying asset without authentication."""
        response = await async_client.post(f"/api/v1/assets/{uuid4()}/certify")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_certify_asset_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test certifying non-existent asset."""
        response = await async_client.post(
            f"/api/v1/assets/{uuid4()}/certify",
            headers=asset_admin_headers,
        )

        assert response.status_code == 404


class TestAssetAdminLineage:
    """Test asset admin lineage management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_get_lineage_unauthorized(self, async_client: AsyncClient):
        """Test getting lineage without authentication."""
        response = await async_client.get(f"/api/v1/assets/{uuid4()}/lineage")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_lineage_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test getting lineage for non-existent asset."""
        response = await async_client.get(
            f"/api/v1/assets/{uuid4()}/lineage",
            headers=asset_admin_headers,
        )

        assert response.status_code == 404


class TestAssetAdminSearch:
    """Test asset admin search lifecycle stage."""

    @pytest.mark.asyncio
    async def test_search_assets_authenticated(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test searching assets with authentication."""
        response = await async_client.post(
            "/api/v1/assets/search",
            json={
                "query": "customer data",
                "asset_types": ["table"],
                "limit": 50,
            },
            headers=asset_admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_assets_with_tags(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test searching assets with tags filter."""
        response = await async_client.post(
            "/api/v1/assets/search",
            json={
                "query": "sales",
                "tags": ["certified", "production"],
                "limit": 25,
            },
            headers=asset_admin_headers,
        )

        assert response.status_code == 200


class TestAssetAdminExport:
    """Test asset admin export lifecycle stage."""

    @pytest.mark.asyncio
    async def test_export_asset_not_found(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test exporting non-existent asset."""
        response = await async_client.post(
            f"/api/v1/assets/{uuid4()}/export",
            json={"format": "json"},
            headers=asset_admin_headers,
        )

        assert response.status_code == 404


class TestAssetAdminLifecycleIntegration:
    """Integration tests for complete asset admin lifecycle."""

    @pytest.mark.asyncio
    async def test_asset_admin_full_lifecycle(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
        sample_asset_config: dict,
    ):
        """Test complete asset admin lifecycle: list -> create -> search -> certify."""
        list_response = await async_client.get(
            "/api/v1/assets",
            headers=asset_admin_headers,
        )

        create_response = await async_client.post(
            "/api/v1/assets",
            json=sample_asset_config,
            headers=asset_admin_headers,
        )

        search_response = await async_client.post(
            "/api/v1/assets/search",
            json={"query": sample_asset_config["name"], "limit": 10},
            headers=asset_admin_headers,
        )

        assert list_response.status_code == 200
        assert create_response.status_code == 201
        assert search_response.status_code == 200

    @pytest.mark.asyncio
    async def test_asset_admin_certification_workflow(
        self,
        async_client: AsyncClient,
        asset_admin_headers: dict,
    ):
        """Test asset admin certification workflow."""
        asset_id = uuid4()
        get_response = await async_client.get(
            f"/api/v1/assets/{asset_id}",
            headers=asset_admin_headers,
        )

        lineage_response = await async_client.get(
            f"/api/v1/assets/{asset_id}/lineage",
            headers=asset_admin_headers,
        )

        certify_response = await async_client.post(
            f"/api/v1/assets/{asset_id}/certify",
            headers=asset_admin_headers,
        )

        assert get_response.status_code == 404
        assert lineage_response.status_code == 404
        assert certify_response.status_code == 404
