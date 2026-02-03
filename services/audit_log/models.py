"""审计日志 - 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class EventType(str, Enum):
    API_CALL = "api_call"
    LOGIN = "login"
    LOGOUT = "logout"
    DATA_ACCESS = "data_access"
    DATA_MODIFY = "data_modify"
    CONFIG_CHANGE = "config_change"
    TASK_EXECUTE = "task_execute"
    EXPORT = "export"
    ADMIN = "admin"


class Subsystem(str, Enum):
    PORTAL = "portal"
    NL2SQL = "nl2sql"
    AI_CLEANING = "ai-cleaning"
    METADATA_SYNC = "metadata-sync"
    DATA_API = "data-api"
    SENSITIVE_DETECT = "sensitive-detect"
    AUDIT_LOG = "audit-log"
    CUBE_STUDIO = "cube-studio"
    SUPERSET = "superset"
    DATAHUB = "datahub"
    DOLPHINSCHEDULER = "dolphinscheduler"


class AuditEvent(BaseModel):
    """审计事件"""
    id: str | None = None
    subsystem: str
    event_type: str = "api_call"
    user: str = "anonymous"
    action: str
    resource: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime | None = None


class AuditQuery(BaseModel):
    """审计日志查询"""
    subsystem: str | None = None
    event_type: str | None = None
    user: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = 1
    page_size: int = 50


class AuditStats(BaseModel):
    """审计统计"""
    total_events: int
    events_by_subsystem: dict[str, int]
    events_by_type: dict[str, int]
    events_by_user: dict[str, int]
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None


class ExportRequest(BaseModel):
    """导出请求"""
    format: str = "csv"     # csv / json
    query: AuditQuery
