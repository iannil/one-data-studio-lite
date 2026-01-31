"""ORM 模型定义 - 数据持久化层

本模块定义所有需要持久化的实体的 ORM 模型。
与 Pydantic 模型分离，ORM 模型专门用于数据库操作。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.sql import func

from services.common.database import Base


# ============================================================
# 审计日志模型
# ============================================================

class AuditEventORM(Base):
    """审计事件 ORM 模型

    记录系统中的所有审计事件，包括 API 调用、登录登出、数据访问等。
    """
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True)
    subsystem = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, default="api_call", index=True)
    user = Column(String(100), nullable=False, default="anonymous", index=True)
    action = Column(String(255), nullable=False)
    resource = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    ip_address = Column(String(45), nullable=True)  # 支持 IPv6
    user_agent = Column(String(512), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    __table_args__ = (
        Index("ix_audit_events_composite", "subsystem", "event_type", "created_at"),
    )


# ============================================================
# 敏感数据检测模型
# ============================================================

class DetectionRuleORM(Base):
    """自定义检测规则 ORM 模型

    用户可以添加自定义的正则表达式规则来检测敏感数据。
    """
    __tablename__ = "detection_rules"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    pattern = Column(String(500), nullable=False)
    sensitivity_level = Column(String(20), nullable=False)  # low/medium/high/critical
    description = Column(Text, nullable=True, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class SensitiveFieldORM(Base):
    """敏感字段 ORM 模型

    扫描报告中发现的敏感字段详情。
    """
    __tablename__ = "sensitive_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(36), nullable=False, index=True)
    column_name = Column(String(100), nullable=False)
    sensitivity_level = Column(String(20), nullable=False)
    detected_types = Column(JSON, nullable=False)  # list[str]
    detection_method = Column(String(50), nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.0)


class ScanReportORM(Base):
    """扫描报告 ORM 模型

    记录每次敏感数据扫描的结果摘要。
    """
    __tablename__ = "scan_reports"

    id = Column(String(36), primary_key=True)
    table_name = Column(String(100), nullable=False, index=True)
    database_name = Column(String(100), nullable=True)
    scan_time = Column(DateTime, nullable=False, default=func.now(), index=True)
    total_columns = Column(Integer, nullable=False)
    sensitive_columns = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low/medium/high/critical
    scanned_by = Column(String(100), nullable=True)


# ============================================================
# 元数据同步模型
# ============================================================

class ETLMappingORM(Base):
    """ETL 映射规则 ORM 模型

    定义 DataHub 元数据变更与 ETL 任务之间的映射关系。
    """
    __tablename__ = "etl_mappings"

    id = Column(String(36), primary_key=True)
    source_urn = Column(String(500), nullable=False, index=True)
    target_task_type = Column(String(50), nullable=False)  # seatunnel/hop/dolphinscheduler
    target_task_id = Column(String(100), nullable=False)
    trigger_on = Column(JSON, nullable=False)  # list[str]: CREATE/UPDATE/DELETE
    auto_update_config = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)


# ============================================================
# ShardingSphere 脱敏规则模型
# ============================================================

class MaskRuleORM(Base):
    """脱敏规则 ORM 模型

    记录 ShardingSphere 脱敏规则配置，用于同步和审计。
    """
    __tablename__ = "mask_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False, index=True)
    column_name = Column(String(100), nullable=False)
    algorithm_type = Column(String(50), nullable=False)
    algorithm_props = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    synced_to_proxy = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_mask_rules_table_column", "table_name", "column_name", unique=True),
    )
