"""add_kb_tables_with_pgvector

Revision ID: b15b4a5021b3
Revises: 5a9d6371e18c
Create Date: 2025-11-08 00:14:16.774072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


revision: str = 'b15b4a5021b3'
down_revision: Union[str, Sequence[str], None] = '5a9d6371e18c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Enable pgvector and create KB tables."""
    
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    op.create_table(
        'kb_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('env', sa.String(20), nullable=False, index=True),
        sa.Column('doc_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_location', sa.Text, nullable=False),
        sa.Column('tags', JSONB, nullable=False, server_default='[]'),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_kb_documents_tenant_env', 'kb_documents', ['tenant_id', 'env'])
    
    op.create_table(
        'kb_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('env', sa.String(20), nullable=False, index=True),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('section', sa.String(500), nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('text_redacted', sa.Text, nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_kb_chunks_tenant_env', 'kb_chunks', ['tenant_id', 'env'])
    op.create_index('idx_kb_chunks_document', 'kb_chunks', ['document_id', 'chunk_index'])
    op.execute(
        'CREATE INDEX idx_kb_chunks_embedding ON kb_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)'
    )
    op.execute(
        'CREATE INDEX idx_kb_chunks_text_search ON kb_chunks USING gin (to_tsvector(\'english\', text))'
    )
    op.execute(
        'CREATE INDEX idx_kb_chunks_text_trigram ON kb_chunks USING gin (text gin_trgm_ops)'
    )
    
    op.create_table(
        'kb_metadata',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('env', sa.String(20), nullable=False, index=True),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_kb_metadata_tenant_env_key', 'kb_metadata', ['tenant_id', 'env', 'key'], unique=True)
    
    op.create_table(
        'kb_ingest_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('env', sa.String(20), nullable=False, index=True),
        sa.Column('job_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('items_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('items_processed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('policy', JSONB, nullable=False),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('idx_kb_ingest_jobs_tenant_env', 'kb_ingest_jobs', ['tenant_id', 'env'])
    op.create_index('idx_kb_ingest_jobs_status', 'kb_ingest_jobs', ['status', 'created_at'])
    
    op.create_table(
        'kb_feedback',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('env', sa.String(20), nullable=False, index=True),
        sa.Column('turn_id', sa.String(255), nullable=False, index=True),
        sa.Column('trace_id', sa.String(255), nullable=False, index=True),
        sa.Column('rating', sa.String(10), nullable=False),
        sa.Column('notes', sa.Text, nullable=False, server_default=''),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_kb_feedback_tenant_env', 'kb_feedback', ['tenant_id', 'env'])
    op.create_index('idx_kb_feedback_rating', 'kb_feedback', ['rating', 'created_at'])


def downgrade() -> None:
    """Downgrade schema: Drop KB tables and disable pgvector."""
    
    op.drop_table('kb_feedback')
    op.drop_table('kb_ingest_jobs')
    op.drop_table('kb_metadata')
    op.drop_table('kb_chunks')
    op.drop_table('kb_documents')
    
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS vector')
