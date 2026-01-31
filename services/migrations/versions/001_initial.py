"""初始化数据库表结构

Revision ID: 001_initial
Revises:
Create Date: 2026-01-30

创建所有核心业务表：
- audit_events: 审计日志
- detection_rules: 敏感数据检测规则
- sensitive_fields: 敏感字段详情
- scan_reports: 扫描报告
- etl_mappings: ETL 映射规则
- mask_rules: 脱敏规则
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 审计事件表
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subsystem", sa.String(50), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("user", sa.String(100), nullable=False, index=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource", sa.String(255), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )
    op.create_index(
        "ix_audit_events_composite",
        "audit_events",
        ["subsystem", "event_type", "created_at"],
    )

    # 检测规则表
    op.create_table(
        "detection_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("pattern", sa.String(500), nullable=False),
        sa.Column("sensitivity_level", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 扫描报告表
    op.create_table(
        "scan_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("table_name", sa.String(100), nullable=False, index=True),
        sa.Column("database_name", sa.String(100), nullable=True),
        sa.Column("scan_time", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("total_columns", sa.Integer, nullable=False),
        sa.Column("sensitive_columns", sa.Integer, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("scanned_by", sa.String(100), nullable=True),
    )

    # 敏感字段表
    op.create_table(
        "sensitive_fields",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(36), nullable=False, index=True),
        sa.Column("column_name", sa.String(100), nullable=False),
        sa.Column("sensitivity_level", sa.String(20), nullable=False),
        sa.Column("detected_types", sa.JSON, nullable=False),
        sa.Column("detection_method", sa.String(50), nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
    )

    # ETL 映射规则表
    op.create_table(
        "etl_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_urn", sa.String(500), nullable=False, index=True),
        sa.Column("target_task_type", sa.String(50), nullable=False),
        sa.Column("target_task_id", sa.String(100), nullable=False),
        sa.Column("trigger_on", sa.JSON, nullable=False),
        sa.Column("auto_update_config", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(100), nullable=True),
    )

    # 脱敏规则表
    op.create_table(
        "mask_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False, index=True),
        sa.Column("column_name", sa.String(100), nullable=False),
        sa.Column("algorithm_type", sa.String(50), nullable=False),
        sa.Column("algorithm_props", sa.JSON, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("synced_to_proxy", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_mask_rules_table_column",
        "mask_rules",
        ["table_name", "column_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("mask_rules")
    op.drop_table("etl_mappings")
    op.drop_table("sensitive_fields")
    op.drop_table("scan_reports")
    op.drop_table("detection_rules")
    op.drop_index("ix_audit_events_composite", table_name="audit_events")
    op.drop_table("audit_events")
