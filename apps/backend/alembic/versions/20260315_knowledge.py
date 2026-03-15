"""Add knowledge base and RAG models.

Revision ID: 20260315_knowledge
Revises: 20260315_monitoring
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260315_knowledge'
down_revision: Union[str, None] = '20260315_monitoring'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create knowledge_bases table
    op.create_table(
        'knowledge_bases',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('kb_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar', sa.String(512), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False, server_default='bge-large-zh'),
        sa.Column('embedding_provider', sa.String(50), nullable=False, server_default='bge'),
        sa.Column('embedding_dim', sa.Integer(), nullable=False, server_default='1024'),
        sa.Column('chunk_strategy', sa.String(50), nullable=False, server_default='fixed_size'),
        sa.Column('chunk_size', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('chunk_overlap', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('retrieval_top_k', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('retrieval_score_threshold', sa.Float(), nullable=True),
        sa.Column('rerank_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rerank_model', sa.String(100), nullable=True),
        sa.Column('vector_backend', sa.String(50), nullable=False, server_default='memory'),
        sa.Column('vector_collection', sa.String(256), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allowed_roles', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('allowed_users', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_size', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_knowledge_bases_kb_id', 'knowledge_bases', ['kb_id'])
    op.create_index('ix_knowledge_bases_owner_id', 'knowledge_bases', ['owner_id'])

    # Create knowledge_documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('doc_id', sa.String(100), unique=True, nullable=False),
        sa.Column('kb_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('source_uri', sa.String(1024), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(1024), nullable=True),
        sa.Column('storage_backend', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('indexed_chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chunk_strategy', sa.String(50), nullable=True),
        sa.Column('chunk_size', sa.Integer(), nullable=True),
        sa.Column('chunk_overlap', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('uploader_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_knowledge_documents_doc_id', 'knowledge_documents', ['doc_id'])
    op.create_index('ix_knowledge_documents_kb_id', 'knowledge_documents', ['kb_id'])

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('chunk_id', sa.String(100), unique=True, nullable=False),
        sa.Column('doc_id', sa.String(100), nullable=False),
        sa.Column('kb_id', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_length', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('start_pos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('end_pos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('vector_id', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_document_chunks_chunk_id', 'document_chunks', ['chunk_id'])
    op.create_index('ix_document_chunks_doc_id', 'document_chunks', ['doc_id'])
    op.create_index('ix_document_chunks_kb_id', 'document_chunks', ['kb_id'])

    # Create vector_indices table
    op.create_table(
        'vector_indices',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('index_id', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('backend', sa.String(50), nullable=False),
        sa.Column('collection_name', sa.String(256), nullable=False),
        sa.Column('embedding_model', sa.String(100), nullable=False),
        sa.Column('embedding_dim', sa.Integer(), nullable=False),
        sa.Column('index_type', sa.String(50), nullable=True),
        sa.Column('metric', sa.String(20), nullable=False, server_default='cosine'),
        sa.Column('params', postgresql.JSONB(), nullable=True),
        sa.Column('endpoint', sa.String(512), nullable=True),
        sa.Column('api_key', sa.String(256), nullable=True),
        sa.Column('vector_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('index_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_vector_indices_index_id', 'vector_indices', ['index_id'])

    # Create retrieval_results table
    op.create_table(
        'retrieval_results',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('kb_id', sa.String(100), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('query_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('top_k', sa.Integer(), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chunk_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('scores', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('retrieval_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('helpful', sa.Boolean(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_retrieval_results_kb_id', 'retrieval_results', ['kb_id'])

    # Create rag_sessions table
    op.create_table(
        'rag_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('session_id', sa.String(100), unique=True, nullable=False),
        sa.Column('kb_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(256), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('model', sa.String(100), nullable=False, server_default='gpt-4'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='2000'),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_rag_sessions_session_id', 'rag_sessions', ['session_id'])
    op.create_index('ix_rag_sessions_kb_id', 'rag_sessions', ['kb_id'])

    # Create rag_messages table
    op.create_table(
        'rag_messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('retrieved_chunks', postgresql.JSONB(), nullable=True),
        sa.Column('retrieval_scores', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_rag_messages_session_id', 'rag_messages', ['session_id'])


def downgrade() -> None:
    op.drop_table('rag_messages')
    op.drop_table('rag_sessions')
    op.drop_table('retrieval_results')
    op.drop_table('vector_indices')
    op.drop_table('document_chunks')
    op.drop_table('knowledge_documents')
    op.drop_table('knowledge_bases')
