"""Remove DCL v1 tables

DCL v1 (Data Connectivity Layer) has been removed from this repo.
This migration drops all DCL-related tables as the functionality
has been superseded by DCL v2 running as an external service.

Revision ID: 1afcfed1bbf5
Revises: f9ac1da2f4b9
Create Date: 2025-12-03

"""
from alembic import op
import sqlalchemy as sa
import re

revision = '1afcfed1bbf5'
down_revision = 'f9ac1da2f4b9'
branch_labels = None
depends_on = None

# Pattern to validate SQL identifiers (alphanumeric and underscores only)
VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str) -> str:
    """Validate that a name is a safe SQL identifier to prevent SQL injection."""
    if not VALID_IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def upgrade():
    """Drop all DCL v1 tables"""
    conn = op.get_bind()
    
    dcl_views = [
        'vw_mapping_review_queue',
    ]
    
    dcl_tables = [
        'approval_workflows',
        'confidence_scores',
        'dcl_unified_contact_link',
        'dcl_unified_contact',
        'canonical_streams',
        'drift_events',
        'hitl_repair_audit',
        'mapping_audit_log',
        'mapping_embeddings',
        'mapping_proposals',
        'mapping_validation_results',
        'mapping_validations',
        'field_concept_mappings',
        'field_mappings',
        'mapping_registry',
        'materialized_accounts',
        'materialized_contacts',
        'materialized_opportunities',
        'schema_changes',
    ]
    
    for view_name in dcl_views:
        # Validate identifier to prevent SQL injection
        safe_view_name = _validate_identifier(view_name)
        result = conn.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = :name)"
        ), {'name': view_name})
        exists = result.scalar()
        if exists:
            op.execute(sa.text(f'DROP VIEW IF EXISTS {safe_view_name} CASCADE'))
            print(f'Dropped view: {safe_view_name}')
    
    for table_name in dcl_tables:
        # Validate identifier to prevent SQL injection
        safe_table_name = _validate_identifier(table_name)
        result = conn.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :name)"
        ), {'name': table_name})
        exists = result.scalar()
        if exists:
            op.execute(sa.text(f'DROP TABLE IF EXISTS {safe_table_name} CASCADE'))
            print(f'Dropped table: {safe_table_name}')


def downgrade():
    """
    No-op downgrade. DCL v1 tables are not recreated.
    
    If you need to restore DCL v1 functionality, restore from a database backup
    or re-run the original migrations that created these tables.
    """
    pass
