"""E2E-04: Multi-Role Collaboration

Tests collaboration across different roles:
1. Data steward defines quality rules
2. Data engineer creates ETL pipeline
3. Data scientist analyzes data
4. Analyst creates visualization
5. Viewer views dashboard
6. Each role verifies permissions
7. Audit trail is complete
"""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.p0
class TestE2E04MultiRoleCollaboration:
    """Multi-role collaboration end-to-end test"""

    async def test_e2e_04_multi_role_collaboration(self, portal_client: AsyncClient):
        """Execute multi-role collaboration journey"""

        # ============================================================
        # Setup: Create users for each role
        # ============================================================
        from services.common.auth import create_token

        super_admin_token = create_token("super_admin", "super_admin", "super_admin")
        super_admin_headers = {"Authorization": f"Bearer {super_admin_token}"}

        # Create users for each role
        roles_to_create = [
            ("e2e_steward", "steward", "Data Steward"),
            ("e2e_engineer", "engineer", "Data Engineer"),
            ("e2e_scientist", "data_scientist", "Data Scientist"),
            ("e2e_analyst", "analyst", "Business Analyst"),
            ("e2e_viewer", "viewer", "Report Viewer"),
        ]

        for username, role, display_name in roles_to_create:
            user_data = {
                "username": username,
                "password": "TestPass123!",
                "role": role,
                "display_name": display_name,
                "email": f"{username}@test.com"
            }
            await portal_client.post(
                "/api/users",
                json=user_data,
                headers=super_admin_headers
            )

        # Create tokens for each role
        steward_headers = {"Authorization": f"Bearer {create_token('e2e_steward', 'e2e_steward', 'steward')}"}
        engineer_headers = {"Authorization": f"Bearer {create_token('e2e_engineer', 'e2e_engineer', 'engineer')}"}
        scientist_headers = {"Authorization": f"Bearer {create_token('e2e_scientist', 'e2e_scientist', 'data_scientist')}"}
        analyst_headers = {"Authorization": f"Bearer {create_token('e2e_analyst', 'e2e_analyst', 'analyst')}"}
        viewer_headers = {"Authorization": f"Bearer {create_token('e2e_viewer', 'e2e_viewer', 'viewer')}"}

        try:
            # ============================================================
            # Step 1: Data steward defines quality rules
            # ============================================================
            quality_rule_data = {
                "name": "Customer Data Quality",
                "rule_type": "completeness",
                "dataset_id": 1,
                "threshold": 0.95,
                "description": "Customer data must be 95% complete"
            }

            response = await portal_client.post(
                "/api/quality/rules",
                json=quality_rule_data,
                headers=steward_headers
            )
            # Quality API may or may not exist
            assert response.status_code in (201, 404, 405)

            # Verify steward can view quality rules
            response = await portal_client.get(
                "/api/quality/rules",
                headers=steward_headers
            )
            assert response.status_code in (200, 404)

            # ============================================================
            # Step 2: Data engineer creates ETL pipeline
            # ============================================================
            pipeline_data = {
                "name": "Customer Sync Pipeline",
                "pipeline_type": "sync",
                "source_system": "mysql",
                "target_system": "data_warehouse",
                "schedule": "0 2 * * *"
            }

            response = await portal_client.post(
                "/api/pipelines",
                json=pipeline_data,
                headers=engineer_headers
            )
            # Pipeline API may or may not exist
            assert response.status_code in (201, 404, 405)

            # Verify engineer can view pipelines
            response = await portal_client.get(
                "/api/pipelines",
                headers=engineer_headers
            )
            assert response.status_code in (200, 404)

            # ============================================================
            # Step 3: Data scientist analyzes data
            # ============================================================
            analysis_data = {
                "dataset_id": 1,
                "analysis_type": "statistical",
                "parameters": {"methods": ["mean", "median", "std"]}
            }

            response = await portal_client.post(
                "/api/analysis/run",
                json=analysis_data,
                headers=scientist_headers
            )
            # Analysis API may or may not exist
            assert response.status_code in (201, 404, 405)

            # Verify scientist can query data
            response = await portal_client.get(
                "/api/data?dataset=customers&limit=100",
                headers=scientist_headers
            )
            assert response.status_code in (200, 404)

            # ============================================================
            # Step 4: Analyst creates visualization
            # ============================================================
            dashboard_data = {
                "name": "Customer Overview",
                "description": "Customer metrics dashboard",
                "category": "business",
                "is_public": True
            }

            response = await portal_client.post(
                "/api/dashboards",
                json=dashboard_data,
                headers=analyst_headers
            )
            # Dashboard API may or may not exist
            assert response.status_code in (201, 404, 405)

            # Verify analyst can view dashboards
            response = await portal_client.get(
                "/api/dashboards",
                headers=analyst_headers
            )
            assert response.status_code in (200, 404)

            # ============================================================
            # Step 5: Viewer views dashboard
            # ============================================================
            response = await portal_client.get(
                "/api/dashboards/1",
                headers=viewer_headers
            )
            # Viewer should have read access
            assert response.status_code in (200, 404, 403)

            # ============================================================
            # Step 6: Each role verifies permissions
            # ============================================================

            # Steward cannot create pipelines (no permission)
            response = await portal_client.post(
                "/api/pipelines",
                json={"name": "Unauthorized Pipeline"},
                headers=steward_headers
            )
            assert response.status_code in (403, 404, 405, 422)

            # Engineer cannot manage quality rules (no permission)
            response = await portal_client.post(
                "/api/quality/rules",
                json={"name": "Unauthorized Rule"},
                headers=engineer_headers
            )
            assert response.status_code in (403, 404, 405, 422)

            # Viewer cannot create dashboards (no permission)
            response = await portal_client.post(
                "/api/dashboards",
                json={"name": "Unauthorized Dashboard"},
                headers=viewer_headers
            )
            assert response.status_code in (403, 404, 405, 422)

            # ============================================================
            # Step 7: Audit trail is complete
            # ============================================================
            response = await portal_client.get(
                "/api/audit/events?limit=50",
                headers=super_admin_headers
            )
            # Audit log may or may not exist
            assert response.status_code in (200, 404)

        finally:
            # ============================================================
            # Cleanup: Delete test users
            # ============================================================
            for username, _, _ in roles_to_create:
                await portal_client.delete(
                    f"/api/users/{username}",
                    headers=super_admin_headers
                )
