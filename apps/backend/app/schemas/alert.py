from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertSeverity, AlertStatus


class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    metric_sql: str
    metric_name: str
    condition: str  # gt, lt, eq, ne, gte, lte
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    check_interval_minutes: int = 5
    cooldown_minutes: int = 60
    notification_channels: list[str] = []
    notification_config: dict[str, Any] | None = None


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    metric_sql: str | None = None
    condition: str | None = None
    threshold: float | None = None
    severity: AlertSeverity | None = None
    check_interval_minutes: int | None = None
    cooldown_minutes: int | None = None
    is_enabled: bool | None = None
    notification_channels: list[str] | None = None
    notification_config: dict[str, Any] | None = None


class AlertRuleResponse(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_enabled: bool
    created_at: datetime
    created_by: UUID | None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    severity: AlertSeverity
    status: AlertStatus
    message: str
    current_value: float
    threshold_value: float
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    resolved_at: datetime | None
    resolved_by: UUID | None
    resolution_note: str | None


class AlertAcknowledgeRequest(BaseModel):
    pass


class AlertResolveRequest(BaseModel):
    resolution_note: str | None = None
