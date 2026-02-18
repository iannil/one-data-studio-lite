from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID

from app.main import app
from app.core.security import create_access_token
from app.api.deps import get_current_user


@pytest.fixture
def auth_headers():
    token = create_access_token("550e8400-e29b-41d4-a716-446655440000")
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_missing_credentials(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_validation(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "invalid-email",
                    "password": "test123",
                    "full_name": "Test User",
                },
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401  # No auth token provided


class TestSourcesEndpoints:
    @pytest.mark.asyncio
    async def test_list_sources_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/sources")

        assert response.status_code == 401  # No auth token provided

    @pytest.mark.asyncio
    async def test_create_source_validation(self, auth_headers):
        mock_user = MagicMock(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            is_active=True,
            is_superuser=False
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/sources",
                    json={
                        "name": "",  # Invalid: empty name
                        "type": "postgresql",
                        "connection_config": {},
                    },
                    headers=auth_headers,
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestETLEndpoints:
    @pytest.mark.asyncio
    async def test_list_pipelines_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/etl/pipelines")

        assert response.status_code == 401  # No auth token provided


class TestAnalysisEndpoints:
    @pytest.mark.asyncio
    async def test_nl_query_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/analysis/nl-query",
                json={"query": "Show me all users"},
            )

        assert response.status_code == 401  # No auth token provided


class TestAssetsEndpoints:
    @pytest.mark.asyncio
    async def test_list_assets_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/assets")

        assert response.status_code == 401  # No auth token provided

    @pytest.mark.asyncio
    async def test_search_assets_unauthorized(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/assets/search",
                json={"query": "sales data"},
            )

        assert response.status_code == 401  # No auth token provided
