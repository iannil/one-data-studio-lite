from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid

import numpy as np
import pandas as pd

from app.models.alert import AlertRule, Alert, AlertSeverity, AlertStatus
from app.services.alert_service import AlertService


class TestAlertService:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def sample_rule(self):
        return AlertRule(
            id=uuid.uuid4(),
            name="Test Rule",
            metric_sql="SELECT COUNT(*) as count FROM errors",
            metric_name="count",
            condition="gt",
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            check_interval_minutes=5,
            cooldown_minutes=60,
            notification_channels=["email"],
            is_enabled=True,
        )

    def test_evaluate_condition_gt(self, mock_db):
        service = AlertService(mock_db)

        assert service._evaluate_condition(15, "gt", 10) is True
        assert service._evaluate_condition(10, "gt", 10) is False
        assert service._evaluate_condition(5, "gt", 10) is False

    def test_evaluate_condition_lt(self, mock_db):
        service = AlertService(mock_db)

        assert service._evaluate_condition(5, "lt", 10) is True
        assert service._evaluate_condition(10, "lt", 10) is False
        assert service._evaluate_condition(15, "lt", 10) is False

    def test_evaluate_condition_eq(self, mock_db):
        service = AlertService(mock_db)

        assert service._evaluate_condition(10, "eq", 10) is True
        assert service._evaluate_condition(5, "eq", 10) is False

    def test_evaluate_condition_gte(self, mock_db):
        service = AlertService(mock_db)

        assert service._evaluate_condition(15, "gte", 10) is True
        assert service._evaluate_condition(10, "gte", 10) is True
        assert service._evaluate_condition(5, "gte", 10) is False

    def test_evaluate_condition_lte(self, mock_db):
        service = AlertService(mock_db)

        assert service._evaluate_condition(5, "lte", 10) is True
        assert service._evaluate_condition(10, "lte", 10) is True
        assert service._evaluate_condition(15, "lte", 10) is False

    def test_build_alert_message(self, mock_db, sample_rule):
        service = AlertService(mock_db)
        message = service._build_alert_message(sample_rule, 15.0)

        assert "Test Rule" in message
        assert "count" in message
        assert "15" in message
        assert "10" in message

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, mock_db):
        alert_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_alert = MagicMock(spec=Alert)
        mock_alert.id = alert_id
        mock_alert.status = AlertStatus.ACTIVE

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alert
        mock_db.execute.return_value = mock_result

        service = AlertService(mock_db)
        result = await service.acknowledge_alert(alert_id, user_id)

        assert result.status == AlertStatus.ACKNOWLEDGED
        assert result.acknowledged_by == user_id
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_alert(self, mock_db):
        alert_id = uuid.uuid4()
        user_id = uuid.uuid4()
        note = "Issue fixed"

        mock_alert = MagicMock(spec=Alert)
        mock_alert.id = alert_id
        mock_alert.status = AlertStatus.ACKNOWLEDGED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alert
        mock_db.execute.return_value = mock_result

        service = AlertService(mock_db)
        result = await service.resolve_alert(alert_id, user_id, note)

        assert result.status == AlertStatus.RESOLVED
        assert result.resolved_by == user_id
        assert result.resolution_note == note
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AlertService(mock_db)
        result = await service.acknowledge_alert(uuid.uuid4(), uuid.uuid4())

        assert result is None


class TestAnomalyDetection:
    """Tests for anomaly detection methods."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def sample_values_with_outliers(self):
        """Sample data with clear outliers."""
        return np.array([10, 11, 10, 12, 11, 10, 100, 9, 11, 10])

    @pytest.fixture
    def normal_distribution_values(self):
        """Sample data following normal distribution."""
        np.random.seed(42)
        return np.random.normal(50, 5, 100)

    def test_zscore_anomaly_detection(self, mock_db, sample_values_with_outliers):
        """Test Z-score anomaly detection identifies outliers."""
        service = AlertService(mock_db)
        anomalies, stats = service._detect_zscore_anomalies(
            sample_values_with_outliers, threshold=2.0
        )

        assert len(anomalies) == 1
        assert anomalies[0]["value"] == 100
        assert anomalies[0]["index"] == 6
        assert "mean" in stats
        assert "std" in stats

    def test_zscore_no_anomalies(self, mock_db, normal_distribution_values):
        """Test Z-score returns empty when no anomalies."""
        service = AlertService(mock_db)
        anomalies, stats = service._detect_zscore_anomalies(
            normal_distribution_values, threshold=5.0
        )

        # With threshold=5, normal distribution should have very few anomalies
        assert len(anomalies) < 5

    def test_zscore_zero_std(self, mock_db):
        """Test Z-score handles zero standard deviation."""
        values = np.array([5, 5, 5, 5, 5])
        service = AlertService(mock_db)
        anomalies, stats = service._detect_zscore_anomalies(values)

        assert len(anomalies) == 0
        assert stats["std"] == 0.0

    def test_iqr_anomaly_detection(self, mock_db, sample_values_with_outliers):
        """Test IQR anomaly detection identifies outliers."""
        service = AlertService(mock_db)
        anomalies, stats = service._detect_iqr_anomalies(
            sample_values_with_outliers, threshold=1.5
        )

        assert len(anomalies) >= 1
        # 100 should be detected as an upper bound violation
        outlier_values = [a["value"] for a in anomalies]
        assert 100 in outlier_values
        assert "q1" in stats
        assert "q3" in stats
        assert "iqr" in stats
        assert "lower_bound" in stats
        assert "upper_bound" in stats

    def test_iqr_identifies_bound_type(self, mock_db):
        """Test IQR correctly identifies lower/upper bound violations."""
        values = np.array([1, 50, 51, 52, 53, 54, 55, 100])
        service = AlertService(mock_db)
        anomalies, stats = service._detect_iqr_anomalies(values, threshold=1.5)

        lower_violations = [a for a in anomalies if a["bound_violated"] == "lower"]
        upper_violations = [a for a in anomalies if a["bound_violated"] == "upper"]

        # 1 should be a lower bound violation, 100 should be upper
        assert any(a["value"] == 1 for a in lower_violations) or \
               any(a["value"] == 100 for a in upper_violations)

    @pytest.mark.asyncio
    async def test_detect_anomalies_zscore_method(self, mock_db):
        """Test full anomaly detection with Z-score method."""
        mock_source = MagicMock()
        mock_source.type = MagicMock()
        mock_source.connection_config = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        sample_df = pd.DataFrame({"value": [10, 11, 10, 12, 100, 9, 11, 10]})

        with patch("app.services.alert_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=sample_df)
            mock_connector.return_value = mock_conn

            service = AlertService(mock_db)
            result = await service.detect_anomalies(
                source_id=str(uuid.uuid4()),
                table_name="test_table",
                column_name="value",
                method="zscore",
                threshold=2.0,
            )

        assert result["method"] == "zscore"
        assert result["total_rows"] == 8
        assert result["anomaly_count"] >= 1
        assert "statistics" in result

    @pytest.mark.asyncio
    async def test_detect_anomalies_iqr_method(self, mock_db):
        """Test full anomaly detection with IQR method."""
        mock_source = MagicMock()
        mock_source.type = MagicMock()
        mock_source.connection_config = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        sample_df = pd.DataFrame({"value": [10, 11, 10, 12, 100, 9, 11, 10]})

        with patch("app.services.alert_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=sample_df)
            mock_connector.return_value = mock_conn

            service = AlertService(mock_db)
            result = await service.detect_anomalies(
                source_id=str(uuid.uuid4()),
                table_name="test_table",
                column_name="value",
                method="iqr",
                threshold=1.5,
            )

        assert result["method"] == "iqr"
        assert "anomaly_percentage" in result

    @pytest.mark.asyncio
    async def test_detect_anomalies_empty_data(self, mock_db):
        """Test anomaly detection with empty data."""
        mock_source = MagicMock()
        mock_source.type = MagicMock()
        mock_source.connection_config = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        with patch("app.services.alert_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=pd.DataFrame())
            mock_connector.return_value = mock_conn

            service = AlertService(mock_db)
            result = await service.detect_anomalies(
                source_id=str(uuid.uuid4()),
                table_name="test_table",
                column_name="value",
                method="zscore",
            )

        assert result["total_rows"] == 0
        assert result["anomaly_count"] == 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_invalid_method(self, mock_db):
        """Test anomaly detection with invalid method raises error."""
        mock_source = MagicMock()
        mock_source.type = MagicMock()
        mock_source.connection_config = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_source
        mock_db.execute.return_value = mock_result

        sample_df = pd.DataFrame({"value": [10, 11, 12]})

        with patch("app.services.alert_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=sample_df)
            mock_connector.return_value = mock_conn

            service = AlertService(mock_db)
            with pytest.raises(ValueError, match="Unsupported anomaly detection method"):
                await service.detect_anomalies(
                    source_id=str(uuid.uuid4()),
                    table_name="test_table",
                    column_name="value",
                    method="invalid_method",
                )

    @pytest.mark.asyncio
    async def test_detect_anomalies_source_not_found(self, mock_db):
        """Test anomaly detection with non-existent source."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AlertService(mock_db)
        with pytest.raises(ValueError, match="Data source not found"):
            await service.detect_anomalies(
                source_id=str(uuid.uuid4()),
                table_name="test_table",
                column_name="value",
            )


class TestEmailNotification:
    """Tests for email notification functionality."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def sample_rule_with_email(self):
        return AlertRule(
            id=uuid.uuid4(),
            name="Email Test Rule",
            metric_sql="SELECT COUNT(*) as count FROM errors",
            metric_name="count",
            condition="gt",
            threshold=10.0,
            severity=AlertSeverity.CRITICAL,
            check_interval_minutes=5,
            cooldown_minutes=60,
            notification_channels=["email"],
            notification_config={
                "email_recipients": ["admin@test.com", "ops@test.com"],
                "smtp_host": "smtp.test.com",
                "smtp_port": 587,
            },
            is_enabled=True,
        )

    @pytest.fixture
    def sample_alert(self):
        return Alert(
            id=uuid.uuid4(),
            rule_id=uuid.uuid4(),
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            message="Test alert message",
            current_value=15.0,
            threshold_value=10.0,
            triggered_at=datetime.now(timezone.utc),
        )

    def test_build_email_body(self, mock_db, sample_rule_with_email, sample_alert):
        """Test email body generation."""
        service = AlertService(mock_db)
        body = service._build_email_body(sample_rule_with_email, sample_alert)

        assert "Email Test Rule" in body
        assert "CRITICAL" in body
        assert "15.0" in body
        assert "10.0" in body
        assert "Smart Data Platform" in body

    def test_build_html_email_body(self, mock_db, sample_rule_with_email, sample_alert):
        """Test HTML email body generation."""
        service = AlertService(mock_db)
        html = service._build_html_email_body(sample_rule_with_email, sample_alert)

        assert "<html>" in html
        assert "Email Test Rule" in html
        assert "critical" in html.lower()
        assert "15.0" in html
        assert "#dc3545" in html  # Critical severity color

    @pytest.mark.asyncio
    async def test_send_email_no_recipients(self, mock_db, sample_alert):
        """Test email not sent when no recipients configured."""
        rule = AlertRule(
            id=uuid.uuid4(),
            name="No Email Rule",
            metric_sql="SELECT 1",
            metric_name="test",
            condition="gt",
            threshold=1.0,
            severity=AlertSeverity.WARNING,
            notification_channels=["email"],
            notification_config={},
            is_enabled=True,
        )

        service = AlertService(mock_db)

        with patch("smtplib.SMTP") as mock_smtp:
            await service._send_email_notification(rule, sample_alert)
            mock_smtp.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_email_with_recipients(self, mock_db, sample_rule_with_email, sample_alert):
        """Test email sent when recipients configured."""
        service = AlertService(mock_db)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server

            await service._send_email_notification(sample_rule_with_email, sample_alert)

            mock_smtp.assert_called_once_with("smtp.test.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_handles_failure(self, mock_db, sample_rule_with_email, sample_alert):
        """Test email failure is handled gracefully."""
        service = AlertService(mock_db)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            # Should not raise, just log error
            await service._send_email_notification(sample_rule_with_email, sample_alert)
