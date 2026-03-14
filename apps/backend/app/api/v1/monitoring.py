"""
Monitoring and Metrics API Endpoints

Provides REST API for monitoring metrics, alert rules, and notifications.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.monitoring import (
    get_metrics_exporter,
    get_alert_engine,
    AlertSeverity,
    AlertState,
    MetricOperator,
    NotificationChannel,
    AlertCondition,
    AlertRule,
    Alert,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class AlertConditionSchema(BaseModel):
    """Alert condition schema"""
    metric_name: str
    operator: MetricOperator
    threshold: float
    labels: Dict[str, str] = Field(default_factory=dict)
    duration_seconds: int = Field(60, ge=0)


class AlertRuleCreateSchema(BaseModel):
    """Create alert rule request"""
    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    severity: AlertSeverity
    enabled: bool = True
    conditions: List[AlertConditionSchema]
    condition_operator: str = Field("AND", regex="^(AND|OR)$")
    notification_channels: List[NotificationChannel] = Field(default_factory=list)
    notification_recipients: List[str] = Field(default_factory=list)
    evaluation_interval_seconds: int = Field(60, ge=10, le=3600)
    resolve_timeout_seconds: Optional[int] = Field(None, ge=60)


class AlertRuleUpdateSchema(BaseModel):
    """Update alert rule request"""
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[List[NotificationChannel]] = None
    notification_recipients: Optional[List[str]] = None
    evaluation_interval_seconds: Optional[int] = None
    resolve_timeout_seconds: Optional[int] = None


class SilenceAlertSchema(BaseModel):
    """Silence alert request"""
    duration_minutes: Optional[int] = Field(None, ge=1, le=10080)


# ============================================================================
# Metrics Endpoints
# ============================================================================


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Prometheus metrics endpoint.

    This endpoint is called by Prometheus to scrape metrics.
    """
    try:
        exporter = get_metrics_exporter()

        # Update metrics before scraping
        await exporter.update_all_metrics()

        # Get metrics in Prometheus text format
        metrics_text = exporter.get_metrics_text()

        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/metrics/summary")
async def get_metrics_summary(
    current_user: User = Depends(get_current_user),
):
    """Get metrics summary for dashboard"""
    try:
        exporter = get_metrics_exporter()

        # Update metrics
        await exporter.update_all_metrics()

        # Gather summary
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "http_requests_total": http_requests_total._value._get(),
            "notebooks": {
                "running": notebook_total.labels(state="running")._value.get(),
                "stopped": notebook_total.labels(state="stopped")._value.get(),
                "error": notebook_total.labels(state="error")._value.get(),
            },
            "training_jobs": {
                "running": training_job_total.labels(state="running")._value.get(),
                "completed": training_job_total.labels(state="completed")._value.get(),
                "failed": training_job_total.labels(state="failed")._value.get(),
            },
            "inference_services": {
                "running": inference_service_total.labels(state="running")._value.get(),
                "stopped": inference_service_total.labels(state="stopped")._value.get(),
                "error": inference_service_total.labels(state="error")._value.get(),
            },
            "workflow_runs": {
                "running": workflow_run_total.labels(state="running")._value.get(),
                "success": workflow_run_total.labels(state="success")._value.get(),
                "failed": workflow_run_total.labels(state="failed")._value.get(),
            },
            "users": {
                "active": user_total.labels(status="active")._value.get(),
                "inactive": user_total.labels(status="inactive")._value.get(),
            },
            "tenants": {
                "active": tenant_total.labels(status="active", tier="all")._value.get(),
            },
        }

        return summary

    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/metrics/targets")
async def list_metric_targets(
    current_user: User = Depends(get_current_user),
):
    """List available metric targets for querying"""
    metrics = {
        "http": [
            {
                "name": "http_requests_total",
                "type": "counter",
                "description": "Total HTTP requests",
                "labels": ["method", "endpoint", "status"],
            },
            {
                "name": "http_request_duration_seconds",
                "type": "histogram",
                "description": "HTTP request latency",
                "labels": ["method", "endpoint"],
            },
        ],
        "database": [
            {
                "name": "db_query_duration_seconds",
                "type": "histogram",
                "description": "Database query duration",
                "labels": ["operation", "table"],
            },
            {
                "name": "db_connections_total",
                "type": "gauge",
                "description": "Database connections",
                "labels": ["state"],
            },
        ],
        "resources": [
            {
                "name": "notebook_total",
                "type": "gauge",
                "description": "Total notebooks",
                "labels": ["state"],
            },
            {
                "name": "training_job_total",
                "type": "gauge",
                "description": "Total training jobs",
                "labels": ["state"],
            },
            {
                "name": "inference_service_total",
                "type": "gauge",
                "description": "Total inference services",
                "labels": ["state"],
            },
            {
                "name": "cpu_usage_percent",
                "type": "gauge",
                "description": "CPU usage percentage",
                "labels": ["service", "instance"],
            },
            {
                "name": "gpu_usage_percent",
                "type": "gauge",
                "description": "GPU usage percentage",
                "labels": ["gpu_id"],
            },
            {
                "name": "gpu_temperature_celsius",
                "type": "gauge",
                "description": "GPU temperature",
                "labels": ["gpu_id"],
            },
        ],
        "queue": [
            {
                "name": "etl_queue_size",
                "type": "gauge",
                "description": "ETL queue size",
                "labels": ["queue_name"],
            },
            {
                "name": "celery_queue_length",
                "type": "gauge",
                "description": "Celery queue length",
                "labels": ["queue_name"],
            },
        ],
    }

    return metrics


# ============================================================================
# Alert Rule Endpoints
# ============================================================================


@router.get("/alerts/rules", response_model=List[Dict[str, Any]])
async def list_alert_rules(
    severity: Optional[AlertSeverity] = None,
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List alert rules"""
    try:
        engine = get_alert_engine()
        rules = engine.list_rules(severity=severity, enabled_only=enabled_only)

        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "conditions": [
                    {
                        "metric_name": c.metric_name,
                        "operator": c.operator.value,
                        "threshold": c.threshold,
                        "labels": c.labels,
                        "duration_seconds": c.duration_seconds,
                    }
                    for c in rule.conditions
                ],
                "condition_operator": rule.condition_operator,
                "notification_channels": [c.value for c in rule.notification_channels],
                "evaluation_interval_seconds": rule.evaluation_interval_seconds,
                "state": rule.state.value,
                "firing_since": rule.firing_since.isoformat() if rule.firing_since else None,
                "alert_count": rule.alert_count,
                "last_evaluated": rule.last_evaluated.isoformat() if rule.last_evaluated else None,
            }
            for rule in rules
        ]
    except Exception as e:
        logger.error(f"Failed to list alert rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/rules", response_model=Dict[str, Any])
async def create_alert_rule(
    request: AlertRuleCreateSchema,
    current_user: User = Depends(get_current_user),
):
    """Create alert rule"""
    try:
        engine = get_alert_engine()

        # Check if rule ID already exists
        if engine.get_rule(request.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alert rule {request.id} already exists",
            )

        # Convert conditions
        conditions = [
            AlertCondition(
                metric_name=c.metric_name,
                operator=c.operator,
                threshold=c.threshold,
                labels=c.labels,
                duration_seconds=c.duration_seconds,
            )
            for c in request.conditions
        ]

        rule = AlertRule(
            id=request.id,
            name=request.name,
            description=request.description,
            severity=request.severity,
            enabled=request.enabled,
            conditions=conditions,
            condition_operator=request.condition_operator,
            notification_channels=request.notification_channels,
            notification_recipients=request.notification_recipients,
            evaluation_interval_seconds=request.evaluation_interval_seconds,
            resolve_timeout_seconds=request.resolve_timeout_seconds,
        )

        engine.register_rule(rule)

        return {
            "id": rule.id,
            "name": rule.name,
            "message": "Alert rule created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/alerts/rules/{rule_id}", response_model=Dict[str, Any])
async def get_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get alert rule details"""
    try:
        engine = get_alert_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found",
            )

        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "conditions": [
                {
                    "metric_name": c.metric_name,
                    "operator": c.operator.value,
                    "threshold": c.threshold,
                    "labels": c.labels,
                    "duration_seconds": c.duration_seconds,
                }
                for c in rule.conditions
            ],
            "condition_operator": rule.condition_operator,
            "notification_channels": [c.value for c in rule.notification_channels],
            "notification_recipients": rule.notification_recipients,
            "evaluation_interval_seconds": rule.evaluation_interval_seconds,
            "resolve_timeout_seconds": rule.resolve_timeout_seconds,
            "state": rule.state.value,
            "firing_since": rule.firing_since.isoformat() if rule.firing_since else None,
            "alert_count": rule.alert_count,
            "last_evaluated": rule.last_evaluated.isoformat() if rule.last_evaluated else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/alerts/rules/{rule_id}", response_model=Dict[str, Any])
async def update_alert_rule(
    rule_id: str,
    request: AlertRuleUpdateSchema,
    current_user: User = Depends(get_current_user),
):
    """Update alert rule"""
    try:
        engine = get_alert_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found",
            )

        # Update fields
        if request.name is not None:
            rule.name = request.name
        if request.description is not None:
            rule.description = request.description
        if request.severity is not None:
            rule.severity = request.severity
        if request.enabled is not None:
            rule.enabled = request.enabled
        if request.notification_channels is not None:
            rule.notification_channels = request.notification_channels
        if request.notification_recipients is not None:
            rule.notification_recipients = request.notification_recipients
        if request.evaluation_interval_seconds is not None:
            rule.evaluation_interval_seconds = request.evaluation_interval_seconds
        if request.resolve_timeout_seconds is not None:
            rule.resolve_timeout_seconds = request.resolve_timeout_seconds

        return {
            "id": rule.id,
            "name": rule.name,
            "message": "Alert rule updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/alerts/rules/{rule_id}", response_model=Dict[str, Any])
async def delete_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete alert rule"""
    try:
        engine = get_alert_engine()
        engine.unregister_rule(rule_id)

        return {"message": f"Alert rule {rule_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Failed to delete alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/rules/{rule_id}/enable", response_model=Dict[str, Any])
async def enable_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Enable alert rule"""
    try:
        engine = get_alert_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found",
            )

        rule.enabled = True

        return {"message": f"Alert rule {rule_id} enabled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/rules/{rule_id}/disable", response_model=Dict[str, Any])
async def disable_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Disable alert rule"""
    try:
        engine = get_alert_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found",
            )

        rule.enabled = False

        return {"message": f"Alert rule {rule_id} disabled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/rules/{rule_id}/test", response_model=Dict[str, Any])
async def test_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    """Test alert rule by evaluating conditions"""
    try:
        engine = get_alert_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert rule {rule_id} not found",
            )

        is_firing = engine.evaluate_rule(rule)

        condition_states = []
        for cond in rule.conditions:
            value = engine.get_metric_value(cond.metric_name, cond.labels)
            condition_states.append({
                "metric_name": cond.metric_name,
                "operator": cond.operator.value,
                "threshold": cond.threshold,
                "current_value": value,
                "firing": value is not None and cond.evaluate(value) if value is not None else False,
            })

        return {
            "rule_id": rule_id,
            "rule_name": rule.name,
            "is_firing": is_firing,
            "condition_states": condition_states,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Alert Endpoints
# ============================================================================


@router.get("/alerts/active", response_model=List[Dict[str, Any]])
async def get_active_alerts(
    severity: Optional[AlertSeverity] = None,
    current_user: User = Depends(get_current_user),
):
    """Get active (firing) alerts"""
    try:
        engine = get_alert_engine()

        # Evaluate rules to update alert states
        engine.evaluate_all_rules()

        alerts = engine.get_active_alerts(severity=severity)

        return [
            {
                "id": alert.id,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "labels": alert.labels,
                "firing": alert.firing,
                "started_at": alert.started_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "notified": alert.notified,
            }
            for alert in alerts
        ]

    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """Manually resolve an alert"""
    try:
        engine = get_alert_engine()
        success = engine.resolve_alert(alert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        return {"message": f"Alert {alert_id} resolved"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/{alert_id}/silence", response_model=Dict[str, Any])
async def silence_alert(
    alert_id: str,
    request: SilenceAlertSchema,
    current_user: User = Depends(get_current_user),
):
    """Silence an alert for a duration"""
    try:
        engine = get_alert_engine()
        success = engine.silence_alert(alert_id, request.duration_minutes)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        duration_msg = f"for {request.duration_minutes} minutes" if request.duration_minutes else "indefinitely"
        return {"message": f"Alert {alert_id} silenced {duration_msg}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to silence alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/alerts/evaluate", response_model=Dict[str, Any])
async def evaluate_all_rules(
    current_user: User = Depends(get_current_user),
):
    """Evaluate all alert rules and send notifications"""
    try:
        engine = get_alert_engine()

        # Evaluate all rules
        triggered_alerts = engine.evaluate_all_rules()

        # Send notifications for new alerts
        engine.send_notifications(triggered_alerts)

        return {
            "evaluated_at": datetime.utcnow().isoformat(),
            "rules_evaluated": len(engine.rules),
            "alerts_triggered": len(triggered_alerts),
            "alerts": [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                }
                for alert in triggered_alerts
            ],
        }

    except Exception as e:
        logger.error(f"Failed to evaluate alert rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Notification Configuration Endpoints
# ============================================================================


@router.get("/notifications/channels", response_model=List[Dict[str, Any]])
async def list_notification_channels(
    current_user: User = Depends(get_current_user),
):
    """List configured notification channels"""
    channels = [
        {
            "type": "email",
            "enabled": True,
            "description": "Email notifications",
            "config_required": True,
        },
        {
            "type": "slack",
            "enabled": False,
            "description": "Slack notifications",
            "config_required": True,
        },
        {
            "type": "webhook",
            "enabled": False,
            "description": "Webhook notifications",
            "config_required": True,
        },
        {
            "type": "pagerduty",
            "enabled": False,
            "description": "PagerDuty notifications",
            "config_required": True,
        },
    ]

    return channels


@router.get("/notifications/status", response_model=Dict[str, Any])
async def get_notification_status(
    current_user: User = Depends(get_current_user),
):
    """Get notification system status"""
    engine = get_alert_engine()

    active_alerts = engine.get_active_alerts()

    return {
        "active_alerts": len(active_alerts),
        "active_alerts_by_severity": {
            "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            "error": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR]),
            "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
            "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO]),
        },
        "last_evaluation": datetime.utcnow().isoformat(),
    }
