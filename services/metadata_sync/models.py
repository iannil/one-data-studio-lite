"""元数据联动ETL - 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ChangeType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class MetadataChangeEvent(BaseModel):
    """DataHub 元数据变更事件"""
    event_id: Optional[str] = None
    entity_type: str        # dataset, dataFlow, dashboard 等
    entity_urn: str         # DataHub URN
    change_type: ChangeType
    aspect_name: str        # schemaMetadata, ownership 等
    changed_fields: list[str] = []
    timestamp: Optional[datetime] = None


class ETLMapping(BaseModel):
    """元数据到 ETL 任务的映射规则"""
    id: str
    source_urn: str                 # DataHub 数据源 URN
    target_task_type: str           # seatunnel / hop / dolphinscheduler
    target_task_id: str             # 对应的任务ID
    trigger_on: list[ChangeType]    # 触发条件
    auto_update_config: bool = True # 是否自动更新ETL配置
    description: str = ""
    enabled: bool = True


class SyncResult(BaseModel):
    """同步结果"""
    success: bool
    message: str
    affected_tasks: list[str] = []
    details: Optional[dict[str, Any]] = None
