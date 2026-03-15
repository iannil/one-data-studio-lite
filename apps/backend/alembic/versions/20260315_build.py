"""Add build cache and enhancement models.

Revision ID: 20260315_build
Revises: 20260315_storage
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_build'
down_revision: Union[str, None] = '20260315_storage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create build_cache_records table
    op.create_table(
        'build_cache_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cache_id', sa.String(100), nullable=False),
        sa.Column('cache_key', sa.String(100), nullable=False),
        sa.Column('dockerfile_hash', sa.String(64), nullable=False),
        sa.Column('layer_hash', sa.String(64), nullable=False),
        sa.Column('image_name', sa.String(256), nullable=False),
        sa.Column('layer_blob', sa.LargeBinary(), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_build_cache_records_cache_id', 'build_cache_records', ['cache_id'], unique=True)
    op.create_index('ix_build_cache_records_cache_key', 'build_cache_records', ['cache_key'])
    op.create_index('ix_build_cache_records_dockerfile_hash', 'build_cache_records', ['dockerfile_hash'])
    op.create_index('ix_build_cache_records_layer_hash', 'build_cache_records', ['layer_hash'])

    # Create build_templates table
    op.create_table(
        'build_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dockerfile_template', sa.Text(), nullable=False),
        sa.Column('build_args', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('base_image', sa.String(256), nullable=False),
        sa.Column('supported_runtimes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_build_templates_template_id', 'build_templates', ['template_id'])
    op.create_index('ix_build_templates_owner_id', 'build_templates', ['owner_id'])


def downgrade() -> None:
    op.drop_table('build_templates')
    op.drop_table('build_cache_records')
