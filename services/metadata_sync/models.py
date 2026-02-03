"""元数据联动ETL - 数据模型

适配 OpenMetadata 事件格式。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """变更类型"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


# ============================================================
# OpenMetadata 事件格式
# ============================================================

class OpenMetadataEntity(BaseModel):
    """OpenMetadata 实体信息"""
    id: str | None = None
    type: str | None = None
    name: str | None = None
    fullyQualifiedName: str | None = Field(default=None, alias="fqn")
    description: str | None = None
    serviceType: str | None = None


class ChangeDescription(BaseModel):
    """变更描述"""
    fieldsAdded: list[dict] = Field(default_factory=list)
    fieldsUpdated: list[dict] = Field(default_factory=list)
    fieldsDeleted: list[dict] = Field(default_factory=list)
    previousVersion: float | None = None


class MetadataChangeEvent(BaseModel):
    """元数据变更事件

    支持两种格式：
    1. OpenMetadata Webhook 格式（推荐）
    2. DataHub 格式（向后兼容）
    """
    # 通用字段
    event_id: str | None = Field(default=None, alias="eventId")
    change_type: ChangeType = Field(default=ChangeType.UPDATE, alias="changeType")
    timestamp: datetime | None = None

    # OpenMetadata 格式字段
    eventType: str | None = None  # entityCreated, entityUpdated, entityDeleted
    entityType: str | None = None  # table, topic, pipeline, etc.
    entityId: str | None = None
    entityFullyQualifiedName: str | None = Field(default=None, alias="entityFQN")
    changeDescription: ChangeDescription | None = None
    entity: OpenMetadataEntity | None = None

    # DataHub 兼容字段
    entity_type: str | None = None  # dataset, dataFlow, dashboard 等
    entity_urn: str | None = None  # DataHub URN
    aspect_name: str | None = None  # schemaMetadata, ownership 等
    changed_fields: list[str] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        self._normalize()

    def _normalize(self):
        """规范化事件数据，兼容不同格式"""
        # 从 OpenMetadata eventType 推断 change_type
        if self.eventType:
            event_type_map = {
                "entityCreated": ChangeType.CREATE,
                "entityUpdated": ChangeType.UPDATE,
                "entityDeleted": ChangeType.DELETE,
            }
            if self.eventType in event_type_map:
                self.change_type = event_type_map[self.eventType]

        # 同步 entityType 和 entity_type
        if self.entityType and not self.entity_type:
            type_map = {
                "table": "dataset",
                "topic": "dataset",
                "pipeline": "dataFlow",
                "dashboard": "dashboard",
                "chart": "chart",
            }
            self.entity_type = type_map.get(self.entityType, self.entityType)
        elif self.entity_type and not self.entityType:
            self.entityType = self.entity_type

        # 从 entityFQN 生成兼容的 entity_urn
        if self.entityFullyQualifiedName and not self.entity_urn:
            service_type = "unknown"
            if self.entity and self.entity.serviceType:
                service_type = self.entity.serviceType.lower()
            self.entity_urn = f"urn:li:dataset:(urn:li:dataPlatform:{service_type},{self.entityFullyQualifiedName},PROD)"
        elif self.entity_urn and not self.entityFullyQualifiedName:
            # 从 URN 解析 FQN
            self.entityFullyQualifiedName = self._parse_fqn_from_urn(self.entity_urn)

        # 从 changeDescription 提取 changed_fields
        if self.changeDescription and not self.changed_fields:
            fields = []
            for f in self.changeDescription.fieldsAdded:
                fields.append(f.get("name", str(f)))
            for f in self.changeDescription.fieldsUpdated:
                fields.append(f.get("name", str(f)))
            for f in self.changeDescription.fieldsDeleted:
                fields.append(f.get("name", str(f)))
            self.changed_fields = fields

    @staticmethod
    def _parse_fqn_from_urn(urn: str) -> str | None:
        """从 DataHub URN 解析 FQN"""
        if not urn or not urn.startswith("urn:li:"):
            return None
        try:
            if "dataset:" in urn:
                inner = urn.split("(")[1].rstrip(")")
                parts = inner.split(",")
                if len(parts) >= 2:
                    return parts[1]
        except (IndexError, ValueError):
            pass
        return None

    class Config:
        populate_by_name = True


class ETLMapping(BaseModel):
    """元数据到 ETL 任务的映射规则"""
    id: str
    source_urn: str  # DataHub 格式 URN 或 OpenMetadata FQN
    target_task_type: str  # seatunnel / hop / dolphinscheduler
    target_task_id: str  # 对应的任务ID
    trigger_on: list[ChangeType]  # 触发条件
    auto_update_config: bool = True  # 是否自动更新ETL配置
    description: str = ""
    enabled: bool = True

    # OpenMetadata 扩展字段
    source_fqn: str | None = None  # OpenMetadata FQN（可选）

    def matches_event(self, event: MetadataChangeEvent) -> bool:
        """检查事件是否匹配此映射规则"""
        if not self.enabled:
            return False

        if event.change_type not in self.trigger_on:
            return False

        # 匹配 URN 或 FQN
        if self.source_urn:
            if event.entity_urn and event.entity_urn == self.source_urn:
                return True
            # 支持通配符匹配
            if self.source_urn.endswith("*"):
                prefix = self.source_urn[:-1]
                if event.entity_urn and event.entity_urn.startswith(prefix):
                    return True

        if self.source_fqn:
            if event.entityFullyQualifiedName == self.source_fqn:
                return True
            # FQN 通配符匹配
            if self.source_fqn.endswith("*"):
                prefix = self.source_fqn[:-1]
                if event.entityFullyQualifiedName and event.entityFullyQualifiedName.startswith(prefix):
                    return True

        return False


class SyncResult(BaseModel):
    """同步结果"""
    success: bool
    message: str
    affected_tasks: list[str] = Field(default_factory=list)
    details: dict[str, Any] | None = None
