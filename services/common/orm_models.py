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
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
# RBAC 模型 - 用户、角色、权限管理
# ============================================================

class PermissionORM(Base):
    """权限 ORM 模型

    定义系统中的所有权限。
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # data, pipeline, system, metadata, etc.
    created_at = Column(DateTime, nullable=False, default=func.now())


class RoleORM(Base):
    """角色 ORM 模型

    定义用户角色及其关联的权限。
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_code = Column(String(50), nullable=False, unique=True, index=True)
    role_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True, default="")
    is_system = Column(Boolean, nullable=False, default=False)  # 是否为系统内置角色
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)

    # 关联权限
    permissions = relationship("RolePermissionORM", back_populates="role", cascade="all, delete-orphan")


class RolePermissionORM(Base):
    """角色权限关联 ORM 模型

    定义角色与权限的多对多关系。
    """
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    permission_code = Column(String(100), ForeignKey("permissions.code"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # 关联角色
    role = relationship("RoleORM", back_populates="permissions")

    __table_args__ = (
        Index("ix_role_permissions_unique", "role_id", "permission_code", unique=True),
    )


class UserORM(Base):
    """用户 ORM 模型

    定义系统用户及其基本信息。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)  # 哈希后的密码
    role_code = Column(String(50), ForeignKey("roles.role_code"), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_locked = Column(Boolean, nullable=False, default=False)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # 支持 IPv6
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    disabled_by = Column(String(100), nullable=True)
    disable_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_active", "is_active"),
    )


class ServiceAccountORM(Base):
    """服务账户 ORM 模型

    用于服务间通信的特殊账户。
    """
    __tablename__ = "service_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True, default="")
    secret_hash = Column(String(255), nullable=False)  # 哈希后的密钥
    role_code = Column(String(50), ForeignKey("roles.role_code"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_service_accounts_active", "is_active"),
    )


class SystemConfigORM(Base):
    """系统配置 ORM 模型

    存储系统级配置项。
    """
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True, default="")
    category = Column(String(50), nullable=False)  # auth, security, ui, etc.
    is_sensitive = Column(Boolean, nullable=False, default=False)  # 是否为敏感配置
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)


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
