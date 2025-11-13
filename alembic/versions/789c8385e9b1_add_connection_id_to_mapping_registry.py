"""add_connection_id_to_mapping_registry

Revision ID: 789c8385e9b1
Revises: a4e46593d477
Create Date: 2025-11-11 23:48:15.474032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '789c8385e9b1'
down_revision: Union[str, Sequence[str], None] = 'a4e46593d477'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add connection_id to mapping_registry for connection-scoped mapping counts."""
    
    op.add_column('mapping_registry', sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    op.create_index(
        'ix_mapping_registry_connection_id', 
        'mapping_registry', 
        ['connection_id']
    )
    
    op.execute("""
        WITH conn_map AS (
            SELECT 
                c.id, 
                c.source_type, 
                ROW_NUMBER() OVER (PARTITION BY c.source_type ORDER BY c.created_at DESC) AS rn
            FROM connections c
            WHERE c.source_type IS NOT NULL
        )
        UPDATE mapping_registry mr
        SET connection_id = conn_map.id
        FROM conn_map
        WHERE mr.connection_id IS NULL
          AND mr.vendor = conn_map.source_type
          AND conn_map.rn = 1
    """)


def downgrade() -> None:
    """Downgrade schema - Remove connection_id from mapping_registry."""
    
    op.drop_index('ix_mapping_registry_connection_id', table_name='mapping_registry')
    op.drop_column('mapping_registry', 'connection_id')
