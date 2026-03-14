"""
Monitoring Alert Rule Service

Manages alert rules for monitoring and notifications.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.services.monitoring.metrics_exporter import get_metrics_exporter

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert states"""
    FIRING = "firing"
    RESOLVED = "resolved"
    PENDING = "pending"
    SILENCED = "silenced"


class MetricOperator(str, Enum):
    """Metric comparison operators"""
    GREATER_THAN = "gt"
    GREATER_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"


class NotificationChannel(str, Enum):
    """Notification channel types"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertCondition:
    """Alert condition definition"""
    metric_name: str  # e.g., "cpu_usage_percent"
    operator: MetricOperator
    threshold: float
    labels: Dict[str, str] = field(default_factory=dict)  # e.g., {"service": "api", "instance": "1"}
    duration_seconds: int = 60  # How long condition must be true

    def evaluate(self, current_value: float) -> bool:
        """Evaluate condition against current value"""
        ops = {
            MetricOperator.GREATER_THAN: current_value > self.threshold,
            MetricOperator.GREATER_OR_EQUAL: current_value >= self.threshold,
            MetricOperator.LESS_THAN: current_value < self.threshold,
            MetricOperator.LESS_OR_EQUAL: current_value <= self.threshold,
            MetricOperator.EQUAL: current_value == self.threshold,
            MetricOperator.NOT_EQUAL: current_value != self.threshold,
        }
        return ops.get(self.operator, False)


@dataclass
class AlertRule:
    """Alert rule definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    enabled: bool
    conditions: List[AlertCondition]
    # All conditions must be true (AND) or any condition (OR)
    condition_operator: str = "AND"

    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    notification_recipients: List[str] = field(default_factory=list)
    notification_template: Optional[str] = None

    # Timing
    evaluation_interval_seconds: int = 60
    resolve_timeout_seconds: Optional[int] = None

    # State
    state: AlertState = AlertState.PENDING
    firing_since: Optional[datetime] = None
    alert_count: int = 0
    last_evaluated: Optional[datetime] = None
    last_notification: Optional[datetime] = None

    # Silencing
    silenced_until: Optional[datetime] = None
    silence_tags: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """Active alert instance"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    labels: Dict[str, str]
    firing: bool
    started_at: datetime
    resolved_at: Optional[datetime] = None
    notified: bool = False


class NotificationSender:
    """Base class for sending notifications"""

    async def send(self, alert: Alert) -> bool:
        """Send notification"""
        raise NotImplementedError


class EmailNotificationSender(NotificationSender):
    """Email notification sender"""

    def __init__(self):
        # Initialize email client
        pass

    async def send(self, alert: Alert) -> bool:
        """Send email notification"""
        try:
            # Send email via configured SMTP server
            logger.info(f"Sending email notification for alert {alert.id}")
            # Implementation would use app.services.email.EmailService
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class SlackNotificationSender(NotificationSender):
    """Slack notification sender"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send Slack notification"""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            import httpx

            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.ERROR: "danger",
                AlertSeverity.CRITICAL: "danger",
            }[alert.severity]

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.upper()}] {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Severity", "value": alert.severity.value, "short": True},
                            {"title": "Status", "value": "Firing" if alert.firing else "Resolved", "short": True},
                            {"title": "Started", "value": alert.started_at.isoformat(), "short": True},
                        ],
                        "footer": "OneData Studio Alerts",
                        "ts": int(alert.started_at.timestamp()),
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info(f"Slack notification sent for alert {alert.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class WebhookNotificationSender(NotificationSender):
    """Webhook notification sender"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send webhook notification"""
        if not self.webhook_url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            import httpx

            payload = {
                "id": alert.id,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "firing": alert.firing,
                "labels": alert.labels,
                "started_at": alert.started_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info(f"Webhook notification sent for alert {alert.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class AlertRuleEngine:
    """
    Alert Rule Engine

    Evaluates alert conditions and triggers notifications.
    """

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.senders: Dict[NotificationChannel, NotificationSender] = {
            NotificationChannel.EMAIL: EmailNotificationSender(),
            NotificationChannel.SLACK: SlackNotificationSender(),
            NotificationChannel.WEBHOOK: WebhookNotificationSender(),
        }
        self._metric_callbacks: Dict[str, Callable[[], float]] = {}

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule"""
        self.rules[rule.id] = rule
        logger.info(f"Registered alert rule: {rule.id} ({rule.name})")

    def unregister_rule(self, rule_id: str) -> None:
        """Unregister an alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            # Clear associated alerts
            if rule_id in self.active_alerts:
                del self.active_alerts[rule_id]
            logger.info(f"Unregistered alert rule: {rule_id}")

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get rule by ID"""
        return self.rules.get(rule_id)

    def list_rules(self, severity: Optional[AlertSeverity] = None, enabled_only: bool = False) -> List[AlertRule]:
        """List rules with optional filters"""
        rules = list(self.rules.values())

        if severity:
            rules = [r for r in rules if r.severity == severity]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def register_metric_callback(self, metric_name: str, callback: Callable[[], float]) -> None:
        """Register a callback to get metric value"""
        self._metric_callbacks[metric_name] = callback

    def get_metric_value(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value of a metric"""
        # Try registered callback first
        if metric_name in self._metric_callbacks:
            return self._metric_callbacks[metric_name]()

        # Try to get from Prometheus
        # In production, this would query Prometheus API
        return None

    def evaluate_rule(self, rule: AlertRule) -> bool:
        """Evaluate all conditions for a rule"""
        if not rule.enabled or rule.silenced_until and rule.silenced_until > datetime.utcnow():
            return False

        condition_results = []

        for condition in rule.conditions:
            value = self.get_metric_value(condition.metric_name, condition.labels)

            if value is None:
                logger.warning(f"Could not get value for metric {condition.metric_name}")
                condition_results.append(False)
                continue

            condition_results.append(condition.evaluate(value))

        # Apply operator
        if rule.condition_operator == "AND":
            return all(condition_results)
        else:  # OR
            return any(condition_results)

    def evaluate_all_rules(self) -> List[Alert]:
        """Evaluate all rules and return triggered alerts"""
        triggered_alerts = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            is_firing = self.evaluate_rule(rule)
            now = datetime.utcnow()
            rule.last_evaluated = now

            if is_firing:
                if rule.state != AlertState.FIRING:
                    rule.state = AlertState.FIRING
                    rule.firing_since = now

                    # Check if duration threshold met
                    if not rule.firing_since or (now - rule.firing_since).total_seconds() >= rule.conditions[0].duration_seconds:
                        # Create or update alert
                        alert_id = f"{rule.id}-{now.strftime('%Y%m%d%H%M%S')}"

                        alert = Alert(
                            id=alert_id,
                            rule_id=rule.id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            message=self._generate_alert_message(rule),
                            labels=rule.conditions[0].labels or {},
                            firing=True,
                            started_at=now,
                        )

                        self.active_alerts[alert_id] = alert
                        triggered_alerts.append(alert)
                        rule.alert_count += 1

            else:
                if rule.state == AlertState.FIRING:
                    # Check for resolve timeout
                    if rule.resolve_timeout and rule.firing_since:
                        if (now - rule.firing_since).total_seconds() >= rule.resolve_timeout:
                            rule.state = AlertState.RESOLVED

                            # Resolve active alerts
                            for alert in self.active_alerts.values():
                                if alert.rule_id == rule.id:
                                    alert.firing = False
                                    alert.resolved_at = now
                                    triggered_alerts.append(alert)

        return triggered_alerts

    def send_notifications(self, alerts: List[Alert]) -> None:
        """Send notifications for alerts"""
        for alert in alerts:
            if alert.notified:
                continue

            for channel in self.active_alerts.values():
                if alert.rule_id in self.rules:
                    rule = self.rules[alert.rule_id]
                    for notification_channel in rule.notification_channels:
                        sender = self.senders.get(notification_channel)
                        if sender:
                            sender.send(alert)

            alert.notified = True

    def _generate_alert_message(self, rule: AlertRule) -> str:
        """Generate alert message"""
        conditions = []
        for cond in rule.conditions:
            op_symbol = {
                MetricOperator.GREATER_THAN: ">",
                MetricOperator.GREATER_OR_EQUAL: ">=",
                MetricOperator.LESS_THAN: "<",
                MetricOperator.LESS_OR_EQUAL: "<=",
                MetricOperator.EQUAL: "==",
                MetricOperator.NOT_EQUAL: "!=",
            }.get(cond.operator, "?")

            label_str = ""
            if cond.labels:
                label_str = "{" + ", ".join(f"{k}={v}" for k, v in cond.labels.items()) + "} "

            conditions.append(f"{cond.metric_name}{label_str}{op_symbol}{cond.threshold}")

        if rule.condition_operator == "AND":
            return f"All conditions met: {' AND '.join(conditions)}"
        else:
            return f"Any condition met: {' OR '.join(conditions)}"

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [a for a in alerts if a.firing]

    def silence_alert(self, alert_id: str, duration_minutes: Optional[int] = None) -> bool:
        """Silence an alert"""
        if alert_id not in self.active_alerts:
            return False

        if duration_minutes:
            until = datetime.utcnow() + timedelta(minutes=duration_minutes)
            rule = self.rules.get(self.active_alerts[alert_id].rule_id)
            if rule:
                rule.silenced_until = until

        # Delete active alert
        del self.active_alerts[alert_id]
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.firing = False
        alert.resolved_at = datetime.utcnow()

        return True


# Global alert rule engine instance
_alert_engine: Optional[AlertRuleEngine] = None


def get_alert_engine() -> AlertRuleEngine:
    """Get the global alert rule engine instance"""
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertRuleEngine()

        # Register some default rules
        _alert_engine.register_rule(AlertRule(
            id="high-cpu-usage",
            name="High CPU Usage",
            description="Alert when CPU usage is above 90% for 5 minutes",
            severity=AlertSeverity.WARNING,
            enabled=True,
            conditions=[
                AlertCondition(
                    metric_name="cpu_usage_percent",
                    operator=MetricOperator.GREATER_THAN,
                    threshold=90,
                    duration_seconds=300,
                ),
            ],
            notification_channels=[NotificationChannel.EMAIL],
            evaluation_interval_seconds=60,
        ))

        _alert_engine.register_rule(AlertRule(
            id="high-memory-usage",
            name="High Memory Usage",
            description="Alert when memory usage is above 90% for 5 minutes",
            severity=AlertSeverity.WARNING,
            enabled=True,
            conditions=[
                AlertCondition(
                    metric_name="memory_usage_bytes",
                    operator=MetricOperator.GREATER_THAN,
                    threshold=0.9,  # Will be multiplied by total
                    duration_seconds=300,
                ),
            ],
            notification_channels=[NotificationChannel.EMAIL],
            evaluation_interval_seconds=60,
        ))

        _alert_engine.register_rule(AlertRule(
            id="gpu-overheating",
            name="GPU Overheating",
            description="Alert when GPU temperature exceeds 85°C",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            conditions=[
                AlertCondition(
                    metric_name="gpu_temperature_celsius",
                    operator=MetricOperator.GREATER_THAN,
                    threshold=85,
                    duration_seconds=60,
                ),
            ],
            notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            evaluation_interval_seconds=30,
        ))

    return _alert_engine
