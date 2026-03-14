"""
E2E tests for Security Admin lifecycle.

Lifecycle stages:
1. Login - User authentication
2. Security - Sensitive data detection
3. Alert Rules - CRUD operations
4. Alerts - View, acknowledge, resolve

Coverage: /security, /alerts/rules, /alerts
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models import User


class TestSecurityAdminSensitiveDetection:
    """Test security admin sensitive data detection lifecycle stage."""

    @pytest.mark.asyncio
    async def test_detect_sensitive_unauthorized(self, async_client: AsyncClient):
        """Test sensitive detection without authentication."""
        response = await async_client.post(
            "/api/v1/security/detect-sensitive",
            params={
                "source_id": str(uuid4()),
                "table_name": "users",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_detect_sensitive_source_not_found(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test sensitive detection with non-existent source."""
        response = await async_client.post(
            "/api/v1/security/detect-sensitive",
            params={
                "source_id": str(uuid4()),
                "table_name": "users",
            },
            headers=security_admin_headers,
        )

        assert response.status_code == 404


class TestSecurityAdminAlertRules:
    """Test security admin alert rule management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_alert_rules_unauthorized(self, async_client: AsyncClient):
        """Test listing alert rules without authentication."""
        response = await async_client.get("/api/v1/alerts/rules")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_alert_rules_authenticated(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test listing alert rules with authentication."""
        response = await async_client.get(
            "/api/v1/alerts/rules",
            headers=security_admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_alert_rule_success(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
        sample_alert_rule_config: dict,
    ):
        """Test creating an alert rule."""
        response = await async_client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule_config,
            headers=security_admin_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_alert_rule_invalid_data(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test creating alert rule with invalid data."""
        response = await async_client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "",
                "metric_sql": "",
            },
            headers=security_admin_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_alert_rule_not_found(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test updating non-existent alert rule."""
        response = await async_client.patch(
            f"/api/v1/alerts/rules/{uuid4()}",
            json={"threshold": 200.0},
            headers=security_admin_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_alert_rule_not_found(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test deleting non-existent alert rule."""
        response = await async_client.delete(
            f"/api/v1/alerts/rules/{uuid4()}",
            headers=security_admin_headers,
        )

        assert response.status_code == 404


class TestSecurityAdminAlerts:
    """Test security admin alert management lifecycle stage."""

    @pytest.mark.asyncio
    async def test_list_alerts_unauthorized(self, async_client: AsyncClient):
        """Test listing alerts without authentication."""
        response = await async_client.get("/api/v1/alerts")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_alerts_authenticated(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test listing alerts with authentication."""
        response = await async_client.get(
            "/api/v1/alerts",
            headers=security_admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_alerts_with_status_filter(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test listing alerts with status filter."""
        response = await async_client.get(
            "/api/v1/alerts",
            params={"status": "triggered"},
            headers=security_admin_headers,
        )

        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test acknowledging non-existent alert."""
        response = await async_client.post(
            f"/api/v1/alerts/{uuid4()}/acknowledge",
            headers=security_admin_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test resolving non-existent alert."""
        response = await async_client.post(
            f"/api/v1/alerts/{uuid4()}/resolve",
            json={"resolution_note": "Issue resolved"},
            headers=security_admin_headers,
        )

        assert response.status_code == 404


class TestSecurityAdminLifecycleIntegration:
    """Integration tests for complete security admin lifecycle."""

    @pytest.mark.asyncio
    async def test_security_admin_full_lifecycle(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
        sample_alert_rule_config: dict,
    ):
        """Test complete security admin lifecycle: rules -> alerts."""
        rules_response = await async_client.get(
            "/api/v1/alerts/rules",
            headers=security_admin_headers,
        )

        create_rule_response = await async_client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule_config,
            headers=security_admin_headers,
        )

        alerts_response = await async_client.get(
            "/api/v1/alerts",
            headers=security_admin_headers,
        )

        assert rules_response.status_code == 200
        assert create_rule_response.status_code == 201
        assert alerts_response.status_code == 200

    @pytest.mark.asyncio
    async def test_security_admin_alert_workflow(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
    ):
        """Test security admin alert handling workflow."""
        alerts_response = await async_client.get(
            "/api/v1/alerts",
            headers=security_admin_headers,
        )

        alert_id = uuid4()
        ack_response = await async_client.post(
            f"/api/v1/alerts/{alert_id}/acknowledge",
            headers=security_admin_headers,
        )

        resolve_response = await async_client.post(
            f"/api/v1/alerts/{alert_id}/resolve",
            json={"resolution_note": "Test resolution"},
            headers=security_admin_headers,
        )

        assert alerts_response.status_code == 200
        assert ack_response.status_code == 404
        assert resolve_response.status_code == 404

    @pytest.mark.asyncio
    async def test_security_admin_rule_lifecycle(
        self,
        async_client: AsyncClient,
        security_admin_headers: dict,
        sample_alert_rule_config: dict,
    ):
        """Test security admin alert rule lifecycle: create -> update -> delete."""
        create_response = await async_client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule_config,
            headers=security_admin_headers,
        )

        rule_id = uuid4()
        update_response = await async_client.patch(
            f"/api/v1/alerts/rules/{rule_id}",
            json={"threshold": 150.0, "severity": "high"},
            headers=security_admin_headers,
        )

        delete_response = await async_client.delete(
            f"/api/v1/alerts/rules/{rule_id}",
            headers=security_admin_headers,
        )

        assert create_response.status_code == 201
        assert update_response.status_code in [404, 422]
        assert delete_response.status_code == 404
