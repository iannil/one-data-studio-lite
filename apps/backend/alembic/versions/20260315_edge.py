"""Add edge computing models.

Revision ID: 20260315_edge
Revises: 20260315_serverless
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_edge'
down_revision: Union[str, None] = '20260315_serverless'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create edge_nodes table
    op.create_table(
        'edge_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('node_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(256), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('geo_fence', postgresql.JSONB(), nullable=True),
        sa.Column('hardware_model', sa.String(100), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('memory_mb', sa.Integer(), nullable=True),
        sa.Column('storage_gb', sa.Integer(), nullable=True),
        sa.Column('gpu_model', sa.String(100), nullable=True),
        sa.Column('gpu_memory_mb', sa.Integer(), nullable=True),
        sa.Column('npu_model', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('mac_address', sa.String(50), nullable=True),
        sa.Column('network_type', sa.String(50), nullable=True),
        sa.Column('os_version', sa.String(100), nullable=True),
        sa.Column('agent_version', sa.String(50), nullable=True),
        sa.Column('runtime_version', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='offline'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('group', sa.String(100), nullable=True),
        sa.Column('labels', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('deployment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('job_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_inference_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_edge_nodes_node_id', 'edge_nodes', ['node_id'])
    op.create_index('ix_edge_nodes_owner_id', 'edge_nodes', ['owner_id'])

    # Create edge_models table
    op.create_table(
        'edge_models',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('model_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('framework', sa.String(50), nullable=False),
        sa.Column('model_path', sa.String(512), nullable=False),
        sa.Column('model_size_mb', sa.Integer(), nullable=False),
        sa.Column('config_path', sa.String(512), nullable=True),
        sa.Column('input_shape', postgresql.JSONB(), nullable=True),
        sa.Column('input_type', sa.String(50), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(), nullable=True),
        sa.Column('inference_latency_ms', sa.Integer(), nullable=True),
        sa.Column('throughput_fps', sa.Integer(), nullable=True),
        sa.Column('min_memory_mb', sa.Integer(), nullable=True),
        sa.Column('required_gpu', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source_model_id', sa.String(100), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('deployment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_inference_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_edge_models_model_id', 'edge_models', ['model_id'])

    # Create edge_deployments table
    op.create_table(
        'edge_deployments',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('deployment_id', sa.String(100), unique=True, nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('allocated_memory_mb', sa.Integer(), nullable=True),
        sa.Column('allocated_gpu_memory_mb', sa.Integer(), nullable=True),
        sa.Column('update_strategy', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('rollback_on_failure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inference_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_latency_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('health_status', sa.String(50), nullable=True),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_edge_deployments_deployment_id', 'edge_deployments', ['deployment_id'])
    op.create_index('ix_edge_deployments_model_id', 'edge_deployments', ['model_id'])
    op.create_index('ix_edge_deployments_node_id', 'edge_deployments', ['node_id'])

    # Create edge_jobs table
    op.create_table(
        'edge_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('job_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('deployment_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_step', sa.String(256), nullable=True),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('output_files', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_edge_jobs_job_id', 'edge_jobs', ['job_id'])
    op.create_index('ix_edge_jobs_node_id', 'edge_jobs', ['node_id'])

    # Create edge_devices table
    op.create_table(
        'edge_devices',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('device_id', sa.String(100), unique=True, nullable=False),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('manufacturer', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('connection_type', sa.String(50), nullable=True),
        sa.Column('connection_params', postgresql.JSONB(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='offline'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_stream_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_stream_config', postgresql.JSONB(), nullable=True),
        sa.Column('location', sa.String(256), nullable=True),
        sa.Column('position', postgresql.JSONB(), nullable=True),
        sa.Column('calibration_data', postgresql.JSONB(), nullable=True),
        sa.Column('last_calibration', sa.DateTime(timezone=True), nullable=True),
        sa.Column('install_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_maintenance', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_maintenance', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_edge_devices_device_id', 'edge_devices', ['device_id'])
    op.create_index('ix_edge_devices_node_id', 'edge_devices', ['node_id'])

    # Create edge_metrics table
    op.create_table(
        'edge_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('deployment_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cpu_percent', sa.Float(), nullable=True),
        sa.Column('memory_percent', sa.Float(), nullable=True),
        sa.Column('memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('disk_percent', sa.Float(), nullable=True),
        sa.Column('disk_used_gb', sa.Float(), nullable=True),
        sa.Column('gpu_percent', sa.Float(), nullable=True),
        sa.Column('gpu_memory_percent', sa.Float(), nullable=True),
        sa.Column('gpu_memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('gpu_temperature', sa.Integer(), nullable=True),
        sa.Column('gpu_power_draw_w', sa.Float(), nullable=True),
        sa.Column('network_rx_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_tx_bytes', sa.BigInteger(), nullable=True),
        sa.Column('inference_count', sa.Integer(), nullable=True),
        sa.Column('inference_latency_ms', sa.Integer(), nullable=True),
        sa.Column('inference_error_count', sa.Integer(), nullable=True),
        sa.Column('custom_metrics', postgresql.JSONB(), nullable=True),
    )
    op.create_index('ix_edge_metrics_node_id', 'edge_metrics', ['node_id'])
    op.create_index('ix_edge_metrics_timestamp', 'edge_metrics', ['timestamp'])

    # Create edge_inference_results table
    op.create_table(
        'edge_inference_results',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('deployment_id', sa.String(100), nullable=False),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('input_id', sa.String(100), nullable=True),
        sa.Column('input_type', sa.String(50), nullable=True),
        sa.Column('input_data', postgresql.JSONB(), nullable=True),
        sa.Column('output', postgresql.JSONB(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('pre_processing_ms', sa.Integer(), nullable=True),
        sa.Column('inference_ms', sa.Integer(), nullable=True),
        sa.Column('post_processing_ms', sa.Integer(), nullable=True),
        sa.Column('memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('gpu_utilization', sa.Float(), nullable=True),
    )
    op.create_index('ix_edge_inference_results_deployment_id', 'edge_inference_results', ['deployment_id'])
    op.create_index('ix_edge_inference_results_node_id', 'edge_inference_results', ['node_id'])
    op.create_index('ix_edge_inference_results_timestamp', 'edge_inference_results', ['timestamp'])


def downgrade() -> None:
    op.drop_table('edge_inference_results')
    op.drop_table('edge_metrics')
    op.drop_table('edge_devices')
    op.drop_table('edge_jobs')
    op.drop_table('edge_deployments')
    op.drop_table('edge_models')
    op.drop_table('edge_nodes')
