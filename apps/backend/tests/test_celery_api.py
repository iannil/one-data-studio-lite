"""Unit tests for Celery monitoring API endpoints."""
from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip tests if Celery is not enabled
pytestmark = pytest.mark.skipif(
    os.getenv("USE_CELERY", "false").lower() != "true",
    reason="Celery API tests require USE_CELERY=true"
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Create authenticated headers."""
    # Create admin user and get token
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "celery_test@example.com",
            "password": "testpass123",
            "full_name": "Celery Test",
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "celery_test@example.com", "password": "testpass123"},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCeleryStatusEndpoint:
    """Tests for GET /api/v1/celery/status"""

    @patch("app.api.v1.celery.USE_CELERY", False)
    def test_status_when_celery_disabled(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test status endpoint when Celery is disabled."""
        response = client.get("/api/v1/celery/status", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] is False
        assert data["workers_online"] == 0
        assert data["tasks_active"] == 0

    @patch("app.api.v1.celery.USE_CELERY", True)
    @patch("app.api.v1.celery.celery_app")
    def test_status_when_celery_enabled(self, mock_celery: Mock, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test status endpoint when Celery is enabled."""
        # Mock inspect
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {
            "worker1@host": {"pool": {"max-concurrency": 4}, "rusage": {}},
            "worker2@host": {"pool": {"max-concurrency": 4}, "rusage": {}},
        }
        mock_inspect.active.return_value = {
            "worker1@host": [{"id": "task1"}],
        }
        mock_inspect.scheduled.return_value = {
            "worker1@host": [{"id": "task2"}],
        }
        mock_inspect.reserved.return_value = {}

        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/celery/status", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] is True
        assert data["workers_online"] == 2
        assert data["tasks_active"] == 1


class TestCeleryWorkersEndpoint:
    """Tests for GET /api/v1/celery/workers"""

    @patch("app.api.v1.celery.USE_CELERY", False)
    def test_workers_when_celery_disabled(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test workers endpoint when Celery is disabled."""
        response = client.get("/api/v1/celery/workers", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.api.v1.celery.USE_CELERY", True)
    @patch("app.api.v1.celery.celery_app")
    def test_workers_when_celery_enabled(self, mock_celery: Mock, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test workers endpoint when Celery is enabled."""
        # Mock inspect
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {
            "worker1@host": {
                "pool": {"type": "gevent", "max-concurrency": 100, "max-tasks-per-child": 1000},
            },
        }
        mock_inspect.active.return_value = {
            "worker1@host": [{"id": "task1"}, {"id": "task2"}],
        }
        mock_inspect.scheduled.return_value = {}
        mock_inspect.reserved.return_value = {}

        mock_celery.control.inspect.return_value = mock_inspect

        response = client.get("/api/v1/celery/workers", headers=auth_headers)
        assert response.status_code == 200

        workers = response.json()
        assert len(workers) == 1
        assert workers[0]["name"] == "worker1@host"
        assert workers[0]["pools"] == ["gevent"]
        assert workers[0]["concurrency"] == 100
        assert workers[0]["active_tasks"] == 2


class TestCeleryQueuesEndpoint:
    """Tests for GET /api/v1/celery/queues"""

    @patch("app.api.v1.celery.USE_CELERY", False)
    def test_queues_when_celery_disabled(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test queues endpoint when Celery is disabled."""
        response = client.get("/api/v1/celery/queues", headers=auth_headers)
        assert response.status_code == 200
        assert "error" in response.json()

    @patch("app.api.v1.celery.USE_CELERY", True)
    @patch("app.api.v1.celery.Redis")
    def test_queues_when_celery_enabled(self, mock_redis: Mock, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test queues endpoint when Celery is enabled."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_client.llen.side_effect = [5, 0, 10, 2]  # collect, report, etl, system
        mock_redis.from_url.return_value = mock_redis_client

        response = client.get("/api/v1/celery/queues", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "queues" in data
        assert "total" in data
        assert data["total"] == 17


class TestCeleryFlowerUrlEndpoint:
    """Tests for GET /api/v1/celery/flower/url"""

    def test_flower_url(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test Flower URL endpoint."""
        response = client.get("/api/v1/celery/flower/url", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "url" in data
        assert "enabled" in data


class TestCeleryTaskCancellation:
    """Tests for POST /api/v1/celery/task/{task_id}/cancel"""

    @patch("app.api.v1.celery.USE_CELERY", False)
    def test_cancel_when_celery_disabled(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test task cancellation when Celery is disabled."""
        response = client.post("/api/v1/celery/task/test-task-id/cancel", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data

    @patch("app.api.v1.celery.USE_CELERY", True)
    @patch("app.api.v1.celery.celery_app")
    def test_cancel_when_celery_enabled(self, mock_celery: Mock, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test task cancellation when Celery is enabled."""
        response = client.post("/api/v1/celery/task/test-task-id/cancel", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["cancelled"] is True


class TestCeleryWorkerShutdown:
    """Tests for POST /api/v1/celery/worker/shutdown"""

    @patch("app.api.v1.celery.USE_CELERY", True)
    @patch("app.api.v1.celery.celery_app")
    def test_shutdown_workers(self, mock_celery: Mock, client: TestClient) -> None:
        """Test worker shutdown (admin only)."""
        # Create admin user
        client.post(
            "/api/v1/auth/register",
            json={"email": "admin@example.com", "password": "admin123", "full_name": "Admin"},
        )
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Mock control.broadcast
        mock_celery.control.broadcast = Mock()

        response = client.post(
            "/api/v1/celery/worker/shutdown",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        mock_celery.control.broadcast.assert_called_once_with("shutdown")

    def test_shutdown_workers_forbidden(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test worker shutdown forbidden for non-admin users."""
        # Regular user (non-admin)
        response = client.post(
            "/api/v1/celery/worker/shutdown",
            headers=auth_headers,
        )
        assert response.status_code == 403
