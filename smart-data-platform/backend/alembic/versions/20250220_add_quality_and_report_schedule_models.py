"""Add quality tracking and report schedule models.

Revision ID: 20250220_quality_schedule
Revises:
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250220_quality_schedule'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create report_schedules table
    op.create_table(
        'report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=False),
        sa.Column('recipients', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('format', sa.String(20), nullable=False, server_default='pdf'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_report_schedules_id'), 'report_schedules', ['id'])
    op.create_index(op.f('ix_report_schedules_report_id'), 'report_schedules', ['report_id'])
    op.create_index(op.f('ix_report_schedules_is_active'), 'report_schedules', ['is_active'])
    op.create_index(op.f('ix_report_schedules_next_run_at'), 'report_schedules', ['next_run_at'])

    # Create data_quality_issues table
    op.create_table(
        'data_quality_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column('column_name', sa.String(255), nullable=True),
        sa.Column('severity', sa.Enum('critical', 'warning', 'info', name='qualityissueseverity'), nullable=False, server_default='info'),
        sa.Column('issue_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_data_quality_issues_id'), 'data_quality_issues', ['id'])
    op.create_index(op.f('ix_data_quality_issues_asset_id'), 'data_quality_issues', ['asset_id'])
    op.create_index(op.f('ix_data_quality_issues_source_id'), 'data_quality_issues', ['source_id'])
    op.create_index(op.f('ix_data_quality_issues_table_name'), 'data_quality_issues', ['table_name'])
    op.create_index(op.f('ix_data_quality_issues_severity'), 'data_quality_issues', ['severity'])
    op.create_index(op.f('ix_data_quality_issues_issue_type'), 'data_quality_issues', ['issue_type'])
    op.create_index(op.f('ix_data_quality_issues_resolved'), 'data_quality_issues', ['resolved'])
    op.create_index(op.f('ix_data_quality_issues_detected_at'), 'data_quality_issues', ['detected_at'])

    # Create quality_assessment_history table
    op.create_table(
        'quality_assessment_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('completeness_score', sa.Float(), nullable=False),
        sa.Column('uniqueness_score', sa.Float(), nullable=False),
        sa.Column('validity_score', sa.Float(), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=False),
        sa.Column('timeliness_score', sa.Float(), nullable=False),
        sa.Column('row_count', sa.Float(), nullable=True),
        sa.Column('column_count', sa.Float(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('assessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_quality_assessment_history_id'), 'quality_assessment_history', ['id'])
    op.create_index(op.f('ix_quality_assessment_history_asset_id'), 'quality_assessment_history', ['asset_id'])
    op.create_index(op.f('ix_quality_assessment_history_overall_score'), 'quality_assessment_history', ['overall_score'])
    op.create_index(op.f('ix_quality_assessment_history_assessed_at'), 'quality_assessment_history', ['assessed_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_quality_assessment_history_assessed_at'), table_name='quality_assessment_history')
    op.drop_index(op.f('ix_quality_assessment_history_overall_score'), table_name='quality_assessment_history')
    op.drop_index(op.f('ix_quality_assessment_history_asset_id'), table_name='quality_assessment_history')
    op.drop_index(op.f('ix_quality_assessment_history_id'), table_name='quality_assessment_history')
    op.drop_table('quality_assessment_history')

    op.drop_index(op.f('ix_data_quality_issues_detected_at'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_resolved'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_issue_type'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_severity'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_table_name'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_source_id'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_asset_id'), table_name='data_quality_issues')
    op.drop_index(op.f('ix_data_quality_issues_id'), table_name='data_quality_issues')
    op.drop_table('data_quality_issues')

    op.drop_index(op.f('ix_report_schedules_next_run_at'), table_name='report_schedules')
    op.drop_index(op.f('ix_report_schedules_is_active'), table_name='report_schedules')
    op.drop_index(op.f('ix_report_schedules_report_id'), table_name='report_schedules')
    op.drop_index(op.f('ix_report_schedules_id'), table_name='report_schedules')
    op.drop_table('report_schedules')

    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS qualityissueseverity')
