"""Add storage abstraction models.

Revision ID: 20260315_storage
Revises: 20250220_quality_schedule
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_storage'
down_revision: Union[str, None] = '20250220_quality_schedule'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create storage_configs table
    op.create_table(
        'storage_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('backend_type', sa.String(50), nullable=False),
        sa.Column('endpoint', sa.String(512), nullable=True),
        sa.Column('access_key', sa.String(256), nullable=True),
        sa.Column('secret_key', sa.String(256), nullable=True),
        sa.Column('bucket', sa.String(256), nullable=True),
        sa.Column('prefix', sa.String(512), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_storage_configs_config_id', 'storage_configs', ['config_id'])
    op.create_index('ix_storage_configs_backend_type', 'storage_configs', ['backend_type'])
    op.create_index('ix_storage_configs_is_default', 'storage_configs', ['is_default'])
    op.create_index('ix_storage_configs_tenant_id', 'storage_configs', ['tenant_id'])

    # Create storage_files table
    op.create_table(
        'storage_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('file_id', sa.String(100), unique=True, nullable=False),
        sa.Column('config_id', sa.String(100), sa.ForeignKey('storage_configs.config_id'), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('storage_class', sa.String(50), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('uploader_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_storage_files_file_id', 'storage_files', ['file_id'])
    op.create_index('ix_storage_files_config_id', 'storage_files', ['config_id'])
    op.create_index('ix_storage_files_filename', 'storage_files', ['filename'])
    op.create_index('ix_storage_files_tenant_id', 'storage_files', ['tenant_id'])
    op.create_index('ix_storage_files_uploader_id', 'storage_files', ['uploader_id'])

    # Create storage_signed_urls table
    op.create_table(
        'storage_signed_urls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('url_id', sa.String(100), unique=True, nullable=False),
        sa.Column('file_id', sa.String(100), sa.ForeignKey('storage_files.file_id'), nullable=False),
        sa.Column('signed_url', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_access_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_storage_signed_urls_url_id', 'storage_signed_urls', ['url_id'])
    op.create_index('ix_storage_signed_urls_file_id', 'storage_signed_urls', ['file_id'])
    op.create_index('ix_storage_signed_urls_expires_at', 'storage_signed_urls', ['expires_at'])

    # Create storage_transfers table
    op.create_table(
        'storage_transfers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transfer_id', sa.String(100), unique=True, nullable=False),
        sa.Column('source_config_id', sa.String(100), nullable=False),
        sa.Column('destination_config_id', sa.String(100), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('transferred_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_storage_transfers_transfer_id', 'storage_transfers', ['transfer_id'])
    op.create_index('ix_storage_transfers_status', 'storage_transfers', ['status'])

    # Create storage_quotas table
    op.create_table(
        'storage_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('quota_id', sa.String(100), unique=True, nullable=False),
        sa.Column('config_id', sa.String(100), sa.ForeignKey('storage_configs.config_id'), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('max_size_gb', sa.Integer(), nullable=False),
        sa.Column('max_file_count', sa.Integer(), nullable=True),
        sa.Column('current_size_gb', sa.Float(), nullable=False, server_default='0'),
        sa.Column('current_file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_storage_quotas_quota_id', 'storage_quotas', ['quota_id'])
    op.create_index('ix_storage_quotas_config_id', 'storage_quotas', ['config_id'])
    op.create_index('ix_storage_quotas_tenant_id', 'storage_quotas', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('storage_quotas')
    op.drop_table('storage_transfers')
    op.drop_table('storage_signed_urls')
    op.drop_table('storage_files')
    op.drop_table('storage_configs')
