"""Initial schema with all base tables.

Revision ID: 20250101_initial
Revises:
Create Date: 2026-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250101_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(256), nullable=True),
        sa.Column('permissions', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_name', 'roles', ['name'])

    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scope', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    # Create sso_identities table
    op.create_table(
        'sso_identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_data', postgresql.JSONB(), nullable=False),
        sa.Column('email', sa.String(256), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_sso_identities_id', 'sso_identities', ['id'])

    # Create data_sources table (metadata)
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('connection_config', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_data_sources_id', 'data_sources', ['id'])
    op.create_index('ix_data_sources_source_id', 'data_sources', ['source_id'])

    # Create metadata_tables table
    op.create_table(
        'metadata_tables',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('table_name', sa.String(256), nullable=False),
        sa.Column('table_schema', postgresql.JSONB(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_metadata_tables_id', 'metadata_tables', ['id'])

    # Create data_assets table
    op.create_table(
        'data_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_data_assets_id', 'data_assets', ['id'])
    op.create_index('ix_data_assets_asset_id', 'data_assets', ['asset_id'])

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_reports_id', 'reports', ['id'])
    op.create_index('ix_reports_report_id', 'reports', ['report_id'])

    # Create etl_pipelines table
    op.create_table(
        'etl_pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_etl_pipelines_id', 'etl_pipelines', ['id'])
    op.create_index('ix_etl_pipelines_pipeline_id', 'etl_pipelines', ['pipeline_id'])

    # Create etl_steps table
    op.create_table(
        'etl_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('etl_pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_etl_steps_id', 'etl_steps', ['id'])

    # Create collect_tasks table
    op.create_table(
        'collect_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_collect_tasks_id', 'collect_tasks', ['id'])
    op.create_index('ix_collect_tasks_task_id', 'collect_tasks', ['task_id'])

    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('condition', postgresql.JSONB(), nullable=False),
        sa.Column('notification_config', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_alert_rules_id', 'alert_rules', ['id'])
    op.create_index('ix_alert_rules_rule_id', 'alert_rules', ['rule_id'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('alert_rules')
    op.drop_table('collect_tasks')
    op.drop_table('etl_steps')
    op.drop_table('etl_pipelines')
    op.drop_table('reports')
    op.drop_table('data_assets')
    op.drop_table('metadata_tables')
    op.drop_table('data_sources')
    op.drop_table('sso_identities')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
