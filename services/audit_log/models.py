"""审计日志 - 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

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
    id: Optional[str] = None
    subsystem: str
    event_type: str = "api_call"
    user: str = "anonymous"
    action: str
    resource: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class AuditQuery(BaseModel):
    """审计日志查询"""
    subsystem: Optional[str] = None
    event_type: Optional[str] = None
    user: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


class AuditStats(BaseModel):
    """审计统计"""
    total_events: int
    events_by_subsystem: dict[str, int]
    events_by_type: dict[str, int]
    events_by_user: dict[str, int]
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


class ExportRequest(BaseModel):
    """导出请求"""
    format: str = "csv"     # csv / json
    query: AuditQuery
