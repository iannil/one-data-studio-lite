from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pandas as pd

from app.services.report_service import ReportService, ReportTemplate, CeleryReportTask


class TestReportTemplate:
    """Test ReportTemplate class."""

    def test_report_template_initialization(self):
        """Test ReportTemplate initialization."""
        name = "Test Report"
        description = "A test report template"
        charts = [{"type": "bar", "title": "Chart 1"}]
        schedule = {"cron": "0 0 * * *"}

        template = ReportTemplate(
            name=name,
            description=description,
            charts=charts,
            schedule=schedule,
        )

        assert template.name == name
        assert template.description == description
        assert template.charts == charts
        assert template.schedule == schedule

    def test_report_template_without_schedule(self):
        """Test ReportTemplate without schedule."""
        template = ReportTemplate(
            name="Test",
            description="Test",
            charts=[],
        )

        assert template.schedule is None


class TestReportService:
    """Test ReportService functionality."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return ReportService(mock_db)

    @pytest.fixture
    def sample_owner_id(self):
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_create_report_template(self, service, sample_owner_id):
        """Test creating a report template."""
        name = "Daily Sales Report"
        description = "Daily sales summary"
        charts = [
            {"type": "bar", "title": "Sales by Region"},
            {"type": "line", "title": "Sales Trend"},
        ]

        result = await service.create_report_template(
            name=name,
            description=description,
            charts=charts,
            owner_id=sample_owner_id,
        )

        assert "template_id" in result
        assert result["name"] == name
        assert result["description"] == description
        assert result["charts"] == charts
        assert result["owner_id"] == str(sample_owner_id)
        assert result["status"] == "active"
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_report_template_with_schedule(self, service, sample_owner_id):
        """Test creating a template with schedule."""
        schedule = {"cron": "0 8 * * *", "timezone": "UTC"}

        result = await service.create_report_template(
            name="Scheduled Report",
            description="A scheduled report",
            charts=[],
            owner_id=sample_owner_id,
            schedule=schedule,
        )

        assert result["schedule"] == schedule

    @pytest.mark.asyncio
    async def test_generate_report_json(self, service):
        """Test generating a report in JSON format."""
        template_id = str(uuid.uuid4())

        result = await service.generate_report(
            template_id=template_id,
            format_type="json",
        )

        assert "report_id" in result
        assert result["template_id"] == template_id
        assert result["format"] == "json"
        assert "charts" in result
        assert len(result["charts"]) == 3
        assert "summary" in result
        assert result["summary"]["total_charts"] == 3

    @pytest.mark.asyncio
    async def test_generate_report_with_parameters(self, service):
        """Test generating a report with parameters."""
        template_id = str(uuid.uuid4())
        parameters = {
            "date_range": "last_30_days",
            "regions": ["North", "South"],
        }

        result = await service.generate_report(
            template_id=template_id,
            format_type="json",
            parameters=parameters,
        )

        assert result["parameters"] == parameters

    @pytest.mark.asyncio
    async def test_generate_report_different_formats(self, service):
        """Test generating reports in different formats."""
        formats = ["json", "csv", "excel", "pdf"]

        for fmt in formats:
            result = await service.generate_report(
                template_id=str(uuid.uuid4()),
                format_type=fmt,
            )

            assert result["format"] == fmt

    @pytest.mark.asyncio
    async def test_schedule_report(self, service):
        """Test scheduling a report."""
        template_id = str(uuid.uuid4())
        cron_expression = "0 8 * * *"
        recipients = ["user1@example.com", "user2@example.com"]

        result = await service.schedule_report(
            template_id=template_id,
            cron_expression=cron_expression,
            recipients=recipients,
            format_type="pdf",
        )

        assert "schedule_id" in result
        assert result["template_id"] == template_id
        assert result["cron_expression"] == cron_expression
        assert result["recipients"] == recipients
        assert result["format"] == "pdf"
        assert result["status"] == "active"
        assert "next_run" in result

    @pytest.mark.asyncio
    async def test_deliver_report(self, service):
        """Test delivering a report."""
        report_id = str(uuid.uuid4())
        recipients = ["recipient@example.com"]

        result = await service.deliver_report(
            report_id=report_id,
            recipients=recipients,
            format_type="pdf",
        )

        assert result["report_id"] == report_id
        assert result["recipients"] == recipients
        assert result["format"] == "pdf"
        assert result["status"] == "delivered"
        assert "delivered_at" in result

    @pytest.mark.asyncio
    async def test_get_report_history(self, service):
        """Test getting report generation history."""
        template_id = str(uuid.uuid4())

        result = await service.get_report_history(
            template_id=template_id,
            limit=50,
        )

        assert result["template_id"] == template_id
        assert "history" in result
        assert result["total_runs"] == len(result["history"])
        assert len(result["history"]) <= 10  # Mock returns max 10

        # Check history items structure
        if result["history"]:
            history_item = result["history"][0]
            assert "report_id" in history_item
            assert "generated_at" in history_item
            assert "status" in history_item

    @pytest.mark.asyncio
    async def test_get_report_history_with_limit(self, service):
        """Test history with custom limit."""
        template_id = str(uuid.uuid4())

        result = await service.get_report_history(template_id, limit=5)

        assert len(result["history"]) <= 5

    @pytest.mark.asyncio
    async def test_list_templates(self, service):
        """Test listing report templates."""
        result = await service.list_templates()

        assert "templates" in result
        assert "total" in result
        assert result["total"] == len(result["templates"])
        assert len(result["templates"]) == 2  # Mock returns 2

        # Check template structure
        template = result["templates"][0]
        assert "template_id" in template
        assert "name" in template
        assert "description" in template
        assert "charts" in template
        assert "schedule" in template

    @pytest.mark.asyncio
    async def test_list_templates_with_owner(self, service, sample_owner_id):
        """Test listing templates filtered by owner."""
        result = await service.list_templates(owner_id=sample_owner_id)

        # All templates should belong to the owner
        for template in result["templates"]:
            assert template["owner_id"] == str(sample_owner_id)

    @pytest.mark.asyncio
    async def test_update_template(self, service):
        """Test updating a report template."""
        template_id = str(uuid.uuid4())
        updates = {
            "name": "Updated Report Name",
            "description": "Updated description",
        }

        result = await service.update_template(
            template_id=template_id,
            updates=updates,
        )

        assert result["template_id"] == template_id
        assert "updated_at" in result
        assert result["updates"] == updates

    @pytest.mark.asyncio
    async def test_delete_template(self, service):
        """Test deleting a report template."""
        template_id = str(uuid.uuid4())

        result = await service.delete_template(template_id)

        assert result["template_id"] == template_id
        assert result["status"] == "deleted"
        assert "deleted_at" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, service, mock_db):
        """Test getting dashboard data with multiple queries."""
        from app.models import DataSource

        source_id = uuid.uuid4()
        queries = [
            {"id": "q1", "table_name": "users", "limit": 100},
            {"id": "q2", "table_name": "orders", "limit": 50},
        ]

        # Mock database response
        mock_source = DataSource(
            id=source_id,
            name="Test Source",
            type="postgresql",
            connection_config={"host": "localhost"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        # Mock connector
        with patch("app.services.report_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            mock_connector.read_data.return_value = pd.DataFrame({
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
            })
            mock_get_connector.return_value = mock_connector

            result = await service.get_dashboard_data(source_id, queries)

        assert result["source_id"] == str(source_id)
        assert "results" in result
        assert len(result["results"]) == 2
        assert "generated_at" in result

        # Check query results
        for query_result in result["results"]:
            assert "query_id" in query_result
            assert "table_name" in query_result
            assert "status" in query_result

    @pytest.mark.asyncio
    async def test_get_dashboard_data_source_not_found(self, service, mock_db):
        """Test dashboard data with non-existent source."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Data source not found"):
            await service.get_dashboard_data(uuid.uuid4(), [])

    @pytest.mark.asyncio
    async def test_get_dashboard_data_with_query_error(self, service, mock_db):
        """Test dashboard data when a query fails."""
        from app.models import DataSource

        source_id = uuid.uuid4()
        queries = [
            {"id": "q1", "table_name": "valid_table", "limit": 100},
            {"id": "q2", "table_name": "invalid_table", "limit": 50},
        ]

        mock_source = DataSource(
            id=source_id,
            name="Test Source",
            type="postgresql",
            connection_config={"host": "localhost"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.report_service.get_connector") as mock_get_connector:
            mock_connector = MagicMock()
            # First query succeeds, second fails
            mock_connector.read_data.side_effect = [
                pd.DataFrame({"id": [1, 2, 3]}),
                Exception("Table not found"),
            ]
            mock_get_connector.return_value = mock_connector

            result = await service.get_dashboard_data(source_id, queries)

        assert len(result["results"]) == 2
        assert result["results"][0]["status"] == "success"
        assert result["results"][1]["status"] == "error"


class TestCeleryReportTask:
    """Test CeleryReportTask class."""

    def test_generate_report_task(self):
        """Test the Celery task for generating reports."""
        template_id = str(uuid.uuid4())
        parameters = {"format": "pdf"}

        result = CeleryReportTask.generate_report_task(
            template_id=template_id,
            parameters=parameters,
        )

        assert "task_id" in result
        assert result["template_id"] == template_id
        assert result["status"] == "completed"
        assert "generated_at" in result

    def test_deliver_report_task(self):
        """Test the Celery task for delivering reports."""
        report_id = str(uuid.uuid4())
        recipients = ["user@example.com"]

        result = CeleryReportTask.deliver_report_task(
            report_id=report_id,
            recipients=recipients,
        )

        assert "task_id" in result
        assert result["report_id"] == report_id
        assert result["recipients"] == recipients
        assert result["status"] == "delivered"
        assert "delivered_at" in result
