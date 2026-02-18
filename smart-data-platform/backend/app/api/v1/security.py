from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models import AlertRule, Alert, AlertStatus, AuditLog, AuditAction
from app.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    AlertResponse,
    AlertResolveRequest,
)
from app.services import AlertService

router = APIRouter(prefix="/security", tags=["Security"])

# Sensitive data patterns
SENSITIVE_PATTERNS = {
    "phone": r"^1[3-9]\d{9}$",
    "id_card": r"^\d{17}[\dXx]$",
    "bank_card": r"^\d{16,19}$",
    "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
    "credit_card": r"^\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$",
}


@router.post("/detect-sensitive")
async def detect_sensitive_data(
    source_id: UUID,
    table_name: str,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Detect sensitive data in a table."""
    from sqlalchemy import select
    from app.models import DataSource
    from app.connectors import get_connector

    source_result = await db.execute(
        select(DataSource).where(DataSource.id == source_id)
    )
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    connector = get_connector(source.type, source.connection_config)
    df = await connector.read_data(table_name=table_name, limit=1000)

    sensitive_columns = []

    for col in df.columns:
        sample_values = df[col].dropna().astype(str).head(100).tolist()

        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            matches = sum(1 for v in sample_values if re.match(pattern, str(v)))

            if matches / max(len(sample_values), 1) > 0.5:
                sensitive_columns.append({
                    "column": col,
                    "pattern": pattern_name,
                    "match_rate": round(matches / len(sample_values) * 100, 2),
                    "sample_count": len(sample_values),
                })
                break

    return {
        "source_id": str(source_id),
        "table_name": table_name,
        "sensitive_columns": sensitive_columns,
        "total_columns": len(df.columns),
    }


# Alert management
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts_router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    request: AlertRuleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> AlertRule:
    """Create a new alert rule."""
    rule = AlertRule(
        name=request.name,
        description=request.description,
        metric_sql=request.metric_sql,
        metric_name=request.metric_name,
        condition=request.condition,
        threshold=request.threshold,
        severity=request.severity,
        check_interval_minutes=request.check_interval_minutes,
        cooldown_minutes=request.cooldown_minutes,
        notification_channels=request.notification_channels,
        notification_config=request.notification_config,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return rule


@alerts_router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[AlertRule]:
    """List alert rules."""
    result = await db.execute(select(AlertRule).offset(skip).limit(limit))
    return list(result.scalars())


@alerts_router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    request: AlertRuleUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AlertRule:
    """Update an alert rule."""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)

    return rule


@alerts_router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_alert_rule(
    rule_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete an alert rule."""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()


@alerts_router.get("", response_model=list[AlertResponse])
async def list_alerts(
    db: DBSession,
    current_user: CurrentUser,
    status: AlertStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Alert]:
    """List alerts."""
    query = select(Alert).order_by(Alert.triggered_at.desc())

    if status:
        query = query.where(Alert.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars())


@alerts_router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Alert:
    """Acknowledge an alert."""
    alert_service = AlertService(db)
    alert = await alert_service.acknowledge_alert(alert_id, current_user.id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@alerts_router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    request: AlertResolveRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Alert:
    """Resolve an alert."""
    alert_service = AlertService(db)
    alert = await alert_service.resolve_alert(
        alert_id,
        current_user.id,
        request.resolution_note,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@alerts_router.post("/detect-anomalies")
async def detect_anomalies(
    source_id: UUID,
    table_name: str,
    column_name: str,
    db: DBSession,
    current_user: CurrentUser,
    method: str = "zscore",
    threshold: float = 3.0,
) -> dict:
    """Detect anomalies in numeric data using statistical methods.

    Args:
        source_id: UUID of the data source.
        table_name: Name of the table to analyze.
        column_name: Name of the numeric column to check.
        method: Detection method - 'zscore' or 'iqr'.
        threshold: Threshold for detection (3.0 for zscore, 1.5 for iqr recommended).
    """
    alert_service = AlertService(db)

    try:
        result = await alert_service.detect_anomalies(
            source_id=str(source_id),
            table_name=table_name,
            column_name=column_name,
            method=method,
            threshold=threshold,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Audit logs
audit_router = APIRouter(prefix="/audit", tags=["Audit"])


@audit_router.get("/logs")
async def list_audit_logs(
    db: DBSession,
    current_user: CurrentUser,
    user_id: UUID | None = None,
    action: AuditAction | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List audit logs."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    logs = result.scalars()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": log.user_email,
            "action": log.action.value,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "timestamp": log.timestamp.isoformat(),
            "ip_address": log.ip_address,
        }
        for log in logs
    ]
