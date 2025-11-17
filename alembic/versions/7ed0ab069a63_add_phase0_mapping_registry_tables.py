"""add_phase0_mapping_registry_tables

Revision ID: 7ed0ab069a63
Revises: c9e54bc008c3
Create Date: 2025-11-17 16:14:17.935982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '7ed0ab069a63'
down_revision: Union[str, Sequence[str], None] = 'c9e54bc008c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Create Phase 0 Enterprise Mapping Registry tables.
    
    This migration adds 6 new tables for the enterprise-grade mapping registry:
    1. connector_definitions - registered data sources (Salesforce, HubSpot, etc.)
    2. entity_schemas - canonical entity schemas (account, opportunity, contact)
    3. field_mappings - core mapping table with RAG support
    4. mapping_embeddings - vector embeddings for semantic search
    5. mapping_audit_log - complete audit trail for compliance
    6. mapping_validation_results - validation tracking
    
    Also creates materialized view mv_mapping_lineage_grid for reporting.
    
    CRITICAL: Does NOT modify existing mapping_registry table.
    """
    
    # Table 1: connector_definitions
    # Defines registered data sources (Salesforce, HubSpot, etc.)
    op.create_table(
        'connector_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('connector_name', sa.String(255), nullable=False),
        sa.Column('connector_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'connector_name', name='unique_tenant_connector'),
    )
    op.create_index('idx_connector_tenant_status', 'connector_definitions', ['tenant_id', 'status'])
    
    # Table 2: entity_schemas
    # Defines canonical entities (account, opportunity, contact, etc.)
    op.create_table(
        'entity_schemas',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_name', sa.String(255), nullable=False),
        sa.Column('entity_version', sa.String(50), nullable=False, server_default='1.0.0'),
        sa.Column('schema_definition', JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('entity_name', 'entity_version', name='unique_entity_version'),
    )
    op.create_index('idx_entity_name', 'entity_schemas', ['entity_name'])
    
    # Table 3: field_mappings
    # Core mapping table - maps source fields to canonical fields with RAG support
    op.create_table(
        'field_mappings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('connection_id', UUID(as_uuid=True), nullable=True),
        sa.Column('connector_id', UUID(as_uuid=True), sa.ForeignKey('connector_definitions.id'), nullable=False),
        sa.Column('entity_schema_id', UUID(as_uuid=True), sa.ForeignKey('entity_schemas.id'), nullable=False),
        
        # Source field information
        sa.Column('source_table', sa.String(255), nullable=False),
        sa.Column('source_field', sa.String(255), nullable=False),
        sa.Column('source_data_type', sa.String(100), nullable=True),
        
        # Target canonical field
        sa.Column('canonical_entity', sa.String(255), nullable=False),
        sa.Column('canonical_field', sa.String(255), nullable=False),
        sa.Column('canonical_data_type', sa.String(100), nullable=True),
        
        # Transformation logic
        sa.Column('mapping_type', sa.String(50), nullable=False, server_default='direct'),
        sa.Column('transformation_rule', JSONB, nullable=True),
        sa.Column('coercion_function', sa.String(255), nullable=True),
        
        # Quality metrics
        sa.Column('confidence_score', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('validation_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('success_rate', sa.Float, nullable=True),
        sa.Column('avg_processing_time_ms', sa.Integer, nullable=True),
        sa.Column('error_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('mapping_source', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text, nullable=True),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        
        sa.UniqueConstraint(
            'tenant_id', 'connector_id', 'source_table', 'source_field', 
            'canonical_entity', 'canonical_field',
            name='unique_tenant_mapping'
        ),
    )
    
    # Performance indexes for field_mappings
    op.create_index('idx_mapping_tenant_connector', 'field_mappings', ['tenant_id', 'connector_id'])
    op.create_index('idx_mapping_entity', 'field_mappings', ['canonical_entity'])
    op.create_index('idx_mapping_status', 'field_mappings', ['status'])
    op.create_index('idx_mapping_confidence', 'field_mappings', ['confidence_score'])
    op.create_index('idx_mapping_source', 'field_mappings', ['mapping_source'])
    
    # Table 4: mapping_embeddings
    # RAG support - vector embeddings for semantic search
    op.create_table(
        'mapping_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('field_mapping_id', UUID(as_uuid=True), sa.ForeignKey('field_mappings.id', ondelete='CASCADE'), nullable=False),
        
        # Embedding data
        sa.Column('embedding_text', sa.Text, nullable=False),
        sa.Column('embedding_vector', Vector(1536), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False, server_default='text-embedding-ada-002'),
        
        # Metadata for similarity matching
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        sa.UniqueConstraint('field_mapping_id', name='unique_embedding_mapping'),
    )
    
    # Vector similarity search index (requires pgvector extension already enabled)
    op.create_index(
        'idx_embedding_vector', 
        'mapping_embeddings', 
        ['embedding_vector'],
        postgresql_using='ivfflat',
        postgresql_ops={'embedding_vector': 'vector_cosine_ops'}
    )
    op.create_index('idx_embedding_mapping', 'mapping_embeddings', ['field_mapping_id'])
    
    # Table 5: mapping_audit_log
    # Complete audit trail for compliance (GDPR, SOC2)
    op.create_table(
        'mapping_audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('field_mapping_id', UUID(as_uuid=True), sa.ForeignKey('field_mappings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        
        # Change tracking
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('field_changed', sa.String(255), nullable=True),
        sa.Column('old_value', JSONB, nullable=True),
        sa.Column('new_value', JSONB, nullable=True),
        
        # Context
        sa.Column('changed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('change_reason', sa.Text, nullable=True),
        sa.Column('confidence_delta', sa.Float, nullable=True),
        
        # Audit metadata
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('trace_id', sa.String(255), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    op.create_index('idx_audit_mapping', 'mapping_audit_log', ['field_mapping_id'])
    op.create_index('idx_audit_tenant_created', 'mapping_audit_log', ['tenant_id', sa.text('created_at DESC')])
    
    # Table 6: mapping_validation_results
    # Track validation outcomes for quality assurance
    op.create_table(
        'mapping_validation_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('field_mapping_id', UUID(as_uuid=True), sa.ForeignKey('field_mappings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        
        # Validation details
        sa.Column('validation_type', sa.String(50), nullable=False),
        sa.Column('validation_status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('sample_input', JSONB, nullable=True),
        sa.Column('sample_output', JSONB, nullable=True),
        
        # Metrics
        sa.Column('test_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('pass_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('fail_count', sa.Integer, nullable=False, server_default='0'),
        
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('validated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    
    op.create_index('idx_validation_mapping', 'mapping_validation_results', ['field_mapping_id'])
    op.create_index('idx_validation_status', 'mapping_validation_results', ['validation_status', sa.text('validated_at DESC')])
    
    # Materialized View: mv_mapping_lineage_grid
    # Optimized view for Tabular Lineage Grid reporting
    op.execute("""
        CREATE MATERIALIZED VIEW mv_mapping_lineage_grid AS
        SELECT 
            fm.id,
            fm.tenant_id,
            cd.connector_name AS source_system,
            fm.source_table,
            fm.source_field,
            fm.canonical_entity AS target_entity,
            fm.canonical_field AS target_field,
            fm.mapping_type,
            fm.confidence_score,
            fm.transformation_rule,
            fm.validation_status,
            fm.success_rate,
            fm.avg_processing_time_ms,
            fm.error_count,
            fm.mapping_source,
            fm.status,
            fm.created_at,
            fm.updated_at,
            u_created.email AS created_by_email,
            u_updated.email AS updated_by_email
        FROM field_mappings fm
        JOIN connector_definitions cd ON fm.connector_id = cd.id
        LEFT JOIN users u_created ON fm.created_by = u_created.id
        LEFT JOIN users u_updated ON fm.updated_by = u_updated.id
        WHERE fm.status = 'active'
    """)
    
    # Indexes for materialized view
    op.create_index('idx_mv_lineage_tenant', 'mv_mapping_lineage_grid', ['tenant_id'])
    op.create_index('idx_mv_lineage_source', 'mv_mapping_lineage_grid', ['source_system'])
    op.create_index('idx_mv_lineage_entity', 'mv_mapping_lineage_grid', ['target_entity'])
    op.create_index('idx_mv_lineage_confidence', 'mv_mapping_lineage_grid', ['confidence_score'])


def downgrade() -> None:
    """
    Downgrade schema: Drop Phase 0 Enterprise Mapping Registry tables.
    
    This is fully reversible - drops all tables, indexes, and views created in upgrade().
    DOES NOT touch existing mapping_registry table.
    """
    
    # Drop materialized view first
    op.drop_index('idx_mv_lineage_confidence', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_entity', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_source', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_tenant', table_name='mv_mapping_lineage_grid')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_mapping_lineage_grid')
    
    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table('mapping_validation_results')
    op.drop_table('mapping_audit_log')
    op.drop_table('mapping_embeddings')
    op.drop_table('field_mappings')
    op.drop_table('entity_schemas')
    op.drop_table('connector_definitions')
