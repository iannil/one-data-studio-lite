"""Add data collection models.

Revision ID: 20260315_serverless
Revises: 20260315_knowledge
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_serverless'
down_revision: Union[str, None] = '20260315_knowledge'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create collection_tasks table
    op.create_table(
        'collection_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('task_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('collection_type', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_config', postgresql.JSONB(), nullable=False),
        sa.Column('destination_type', sa.String(50), nullable=False, server_default='s3'),
        sa.Column('destination_config', postgresql.JSONB(), nullable=False),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('schedule_interval', sa.Integer(), nullable=True),
        sa.Column('preprocessing_pipeline', postgresql.JSONB(), nullable=True),
        sa.Column('postprocessing_pipeline', postgresql.JSONB(), nullable=True),
        sa.Column('batch_size', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('batch_timeout', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('quality_rules', postgresql.JSONB(), nullable=True),
        sa.Column('quality_threshold', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('stop_on_error', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_delay', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True),
        sa.Column('notify_on_success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notify_on_failure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_records_collected', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_bytes_collected', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_collection_tasks_task_id', 'collection_tasks', ['task_id'])
    op.create_index('ix_collection_tasks_owner_id', 'collection_tasks', ['owner_id'])

    # Create collection_executions table
    op.create_table(
        'collection_executions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('execution_id', sa.String(100), unique=True, nullable=False),
        sa.Column('task_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('trigger_type', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('trigger_source', sa.String(256), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('records_collected', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('bytes_collected', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('batches_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('batches_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_files', postgresql.JSONB(), nullable=True),
        sa.Column('output_location', sa.String(512), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('quality_level', sa.String(50), nullable=True),
        sa.Column('quality_details', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('peak_memory_mb', sa.Integer(), nullable=True),
        sa.Column('cpu_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_collection_executions_execution_id', 'collection_executions', ['execution_id'])
    op.create_index('ix_collection_executions_task_id', 'collection_executions', ['task_id'])

    # Create data_source_connectors table
    op.create_table(
        'data_source_connectors',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('connector_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('connection_config', postgresql.JSONB(), nullable=False),
        sa.Column('schema_mapping', postgresql.JSONB(), nullable=True),
        sa.Column('test_query', sa.Text(), nullable=True),
        sa.Column('last_test_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_test_result', sa.Boolean(), nullable=True),
        sa.Column('encrypted_credentials', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_data_source_connectors_connector_id', 'data_source_connectors', ['connector_id'])

    # Create quality_validation_results table
    op.create_table(
        'quality_validation_results',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('execution_id', sa.String(100), nullable=False),
        sa.Column('total_records', sa.BigInteger(), nullable=False),
        sa.Column('valid_records', sa.BigInteger(), nullable=False),
        sa.Column('invalid_records', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('quality_level', sa.String(50), nullable=False),
        sa.Column('validation_rules', postgresql.JSONB(), nullable=False),
        sa.Column('validation_results', postgresql.JSONB(), nullable=False),
        sa.Column('issues_summary', postgresql.JSONB(), nullable=True),
        sa.Column('sample_invalid_records', postgresql.JSONB(), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_quality_validation_results_execution_id', 'quality_validation_results', ['execution_id'])

    # Create data_streams table
    op.create_table(
        'data_streams',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('stream_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_config', postgresql.JSONB(), nullable=False),
        sa.Column('data_format', sa.String(50), nullable=False, server_default='json'),
        sa.Column('schema_definition', postgresql.JSONB(), nullable=True),
        sa.Column('destination_config', postgresql.JSONB(), nullable=False),
        sa.Column('realtime_processing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processing_pipeline', postgresql.JSONB(), nullable=True),
        sa.Column('buffer_size', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('buffer_timeout', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(50), nullable=False, server_default='stopped'),
        sa.Column('total_messages', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('messages_per_second', sa.Float(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_data_streams_stream_id', 'data_streams', ['stream_id'])

    # Create webhook_configs table
    op.create_table(
        'webhook_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('webhook_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('webhook_path', sa.String(256), nullable=False, unique=True),
        sa.Column('auth_type', sa.String(50), nullable=False, server_default='none'),
        sa.Column('auth_config', postgresql.JSONB(), nullable=True),
        sa.Column('expected_format', sa.String(50), nullable=False, server_default='json'),
        sa.Column('schema_validation', postgresql.JSONB(), nullable=True),
        sa.Column('target_task_id', sa.String(100), nullable=True),
        sa.Column('target_stream_id', sa.String(100), nullable=True),
        sa.Column('preprocessing', postgresql.JSONB(), nullable=True),
        sa.Column('rate_limit_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('total_calls', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('successful_calls', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('failed_calls', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_call_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_webhook_configs_webhook_id', 'webhook_configs', ['webhook_id'])


def downgrade() -> None:
    op.drop_table('webhook_configs')
    op.drop_table('data_streams')
    op.drop_table('quality_validation_results')
    op.drop_table('data_source_connectors')
    op.drop_table('collection_executions')
    op.drop_table('collection_tasks')
