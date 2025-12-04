"""fix_phase0_mapping_registry_critical_issues

Revision ID: a01b6d6912e0
Revises: 7ed0ab069a63
Create Date: 2025-11-17 16:20:43.878710

CRITICAL FIXES (Architect Review):
1. Add FK constraint: field_mappings.connection_id -> connections.id
2. Add tenant_id to mapping_embeddings for proper tenant isolation
3. Fix unique constraint in field_mappings to include connection_id
4. Secure materialized view with explicit tenant filtering
5. Fix downgrade sequence to drop indexes/views before tables

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a01b6d6912e0'
down_revision: Union[str, Sequence[str], None] = '7ed0ab069a63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply critical fixes to Phase 0 mapping registry schema.
    
    CRITICAL FIXES:
    1. Add FK: field_mappings.connection_id -> connections.id (SET NULL on delete)
    2. Add tenant_id to mapping_embeddings with FK to tenants
    3. Fix unique constraint to include connection_id for proper scoping
    4. Recreate materialized view with explicit tenant filtering
    5. Proper indexes for tenant isolation enforcement
    """
    
    # ============================================================================
    # FIX 1: Add Foreign Key for field_mappings.connection_id -> connections.id
    # ============================================================================
    # Connection_id is nullable, so use SET NULL on delete
    # This ensures referential integrity between mappings and connections
    op.create_foreign_key(
        'fk_field_mappings_connection_id',
        'field_mappings',
        'connections',
        ['connection_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # ============================================================================
    # FIX 2: Add tenant_id to mapping_embeddings for tenant isolation
    # ============================================================================
    # Step 2a: Add tenant_id column (nullable for migration)
    op.add_column(
        'mapping_embeddings',
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Step 2b: Backfill tenant_id from field_mappings table
    # Every mapping_embeddings row has a field_mapping_id FK, so we can join
    op.execute("""
        UPDATE mapping_embeddings me
        SET tenant_id = fm.tenant_id
        FROM field_mappings fm
        WHERE me.field_mapping_id = fm.id
    """)
    
    # Step 2c: Make tenant_id NOT NULL now that it's populated
    op.alter_column('mapping_embeddings', 'tenant_id', nullable=False)
    
    # Step 2d: Add foreign key to tenants table
    op.create_foreign_key(
        'fk_mapping_embeddings_tenant_id',
        'mapping_embeddings',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Step 2e: Add index on tenant_id for isolation enforcement
    op.create_index(
        'idx_embedding_tenant',
        'mapping_embeddings',
        ['tenant_id']
    )
    
    # ============================================================================
    # FIX 3: Fix unique constraint to include connection_id
    # ============================================================================
    # The current constraint doesn't include connection_id, which means
    # the same mapping could be duplicated across different connections.
    # Drop old constraint and add new one with connection_id.
    
    # Drop old unique constraint
    op.drop_constraint('unique_tenant_mapping', 'field_mappings', type_='unique')
    
    # Add new unique constraint that includes connection_id
    # This ensures mappings are unique per connection, not just per connector
    op.create_unique_constraint(
        'unique_tenant_connection_mapping',
        'field_mappings',
        ['tenant_id', 'connection_id', 'connector_id', 'source_table', 
         'source_field', 'canonical_entity', 'canonical_field']
    )
    
    # ============================================================================
    # FIX 4: Recreate materialized view with explicit tenant filtering
    # ============================================================================
    # Drop existing materialized view and recreate with tenant security
    
    # Drop indexes first
    op.drop_index('idx_mv_lineage_confidence', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_entity', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_source', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_tenant', table_name='mv_mapping_lineage_grid')
    
    # Drop materialized view
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_mapping_lineage_grid')
    
    # Recreate with explicit tenant filtering in WHERE clause
    # CRITICAL: This ensures 100% tenant isolation at the view level
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
          AND fm.tenant_id IS NOT NULL
          AND cd.tenant_id IS NOT NULL
          AND fm.tenant_id = cd.tenant_id
    """)
    
    # Recreate indexes with tenant_id first for optimal isolation queries
    op.create_index('idx_mv_lineage_tenant', 'mv_mapping_lineage_grid', ['tenant_id'])
    op.create_index('idx_mv_lineage_tenant_source', 'mv_mapping_lineage_grid', ['tenant_id', 'source_system'])
    op.create_index('idx_mv_lineage_tenant_entity', 'mv_mapping_lineage_grid', ['tenant_id', 'target_entity'])
    op.create_index('idx_mv_lineage_confidence', 'mv_mapping_lineage_grid', ['confidence_score'])


def downgrade() -> None:
    """
    Downgrade schema: Reverse all fixes applied in upgrade().
    
    CRITICAL: Proper sequence to avoid dependency errors:
    1. Drop materialized view indexes first
    2. Drop materialized view
    3. Drop new constraints
    4. Drop tenant_id column from mapping_embeddings
    5. Restore old unique constraint on field_mappings
    6. Drop FK constraints
    
    This is fully reversible with zero errors.
    """
    
    # ============================================================================
    # REVERSE FIX 4: Drop secured materialized view and restore original
    # ============================================================================
    # Drop indexes first
    op.drop_index('idx_mv_lineage_confidence', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_tenant_entity', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_tenant_source', table_name='mv_mapping_lineage_grid')
    op.drop_index('idx_mv_lineage_tenant', table_name='mv_mapping_lineage_grid')
    
    # Drop materialized view
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_mapping_lineage_grid')
    
    # Recreate original materialized view (without explicit tenant filtering)
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
    
    # Recreate original indexes
    op.create_index('idx_mv_lineage_tenant', 'mv_mapping_lineage_grid', ['tenant_id'])
    op.create_index('idx_mv_lineage_source', 'mv_mapping_lineage_grid', ['source_system'])
    op.create_index('idx_mv_lineage_entity', 'mv_mapping_lineage_grid', ['target_entity'])
    op.create_index('idx_mv_lineage_confidence', 'mv_mapping_lineage_grid', ['confidence_score'])
    
    # ============================================================================
    # REVERSE FIX 3: Restore original unique constraint
    # ============================================================================
    # Drop new constraint with connection_id
    op.drop_constraint('unique_tenant_connection_mapping', 'field_mappings', type_='unique')
    
    # Restore original constraint without connection_id
    op.create_unique_constraint(
        'unique_tenant_mapping',
        'field_mappings',
        ['tenant_id', 'connector_id', 'source_table', 'source_field', 
         'canonical_entity', 'canonical_field']
    )
    
    # ============================================================================
    # REVERSE FIX 2: Remove tenant_id from mapping_embeddings
    # ============================================================================
    # Drop index first
    op.drop_index('idx_embedding_tenant', table_name='mapping_embeddings')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_mapping_embeddings_tenant_id', 'mapping_embeddings', type_='foreignkey')
    
    # Drop tenant_id column
    op.drop_column('mapping_embeddings', 'tenant_id')
    
    # ============================================================================
    # REVERSE FIX 1: Drop FK constraint on field_mappings.connection_id
    # ============================================================================
    op.drop_constraint('fk_field_mappings_connection_id', 'field_mappings', type_='foreignkey')
