"""Add monitoring integration models.

Revision ID: 20260315_monitoring
Revises: 20260315_build
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_monitoring'
down_revision: Union[str, None] = '20260315_build'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prometheus_metrics table
    op.create_table(
        'prometheus_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False, unique=True),
        sa.Column('metric_type', sa.String(20), nullable=False),
        sa.Column('help_text', sa.Text(), nullable=False),
        sa.Column('labels', postgresql.JSONB(), nullable=True),
        sa.Column('default_labels', postgresql.JSONB(), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('buckets', postgresql.JSONB(), nullable=True),
        sa.Column('object_type', sa.String(50), nullable=True),
        sa.Column('object_id', sa.String(100), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_prometheus_metrics_metric_id', 'prometheus_metrics', ['metric_id'])
    op.create_index('ix_prometheus_metrics_name', 'prometheus_metrics', ['name'])

    # Create prometheus_rules table
    op.create_table(
        'prometheus_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('duration', sa.String(50), nullable=False, server_default='1m'),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('annotations', postgresql.JSONB(), nullable=True),
        sa.Column('labels', postgresql.JSONB(), nullable=True),
        sa.Column('alert_type', sa.String(50), nullable=False, server_default='prometheus'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_prometheus_rules_rule_id', 'prometheus_rules', ['rule_id'])

    # Create log_indices table
    op.create_table(
        'log_indices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('index_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('index_pattern', sa.String(256), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('shard_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('replica_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('field_mappings', postgresql.JSONB(), nullable=True),
        sa.Column('object_type', sa.String(50), nullable=True),
        sa.Column('object_filter', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_log_indices_index_id', 'log_indices', ['index_id'])

    # Create trace_configs table
    op.create_table(
        'trace_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trace_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('service_name', sa.String(256), nullable=False),
        sa.Column('sample_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('max_traces_per_second', sa.Integer(), nullable=True),
        sa.Column('jaeger_endpoint', sa.String(512), nullable=False),
        sa.Column('jaeger_user', sa.String(256), nullable=True),
        sa.Column('jaeger_password', sa.String(256), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('default_tags', postgresql.JSONB(), nullable=True),
        sa.Column('batch_size', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('batch_timeout', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_trace_configs_trace_id', 'trace_configs', ['trace_id'])

    # Create dashboards table
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dashboard_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dashboard_type', sa.String(50), nullable=False),
        sa.Column('panel_config', postgresql.JSONB(), nullable=False),
        sa.Column('layout', postgresql.JSONB(), nullable=True),
        sa.Column('data_sources', postgresql.JSONB(), nullable=True),
        sa.Column('refresh_interval', sa.String(20), nullable=True),
        sa.Column('default_filters', postgresql.JSONB(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_dashboards_dashboard_id', 'dashboards', ['dashboard_id'])
    op.create_index('ix_dashboards_owner_id', 'dashboards', ['owner_id'])


def downgrade() -> None:
    op.drop_table('dashboards')
    op.drop_table('trace_configs')
    op.drop_table('log_indices')
    op.drop_table('prometheus_rules')
    op.drop_table('prometheus_metrics')
