"""add unique index on mapping_registry connection_id vendor_field

Revision ID: 0cf63f8c98ed
Revises: 789c8385e9b1
Create Date: 2025-11-12 00:06:28.137702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cf63f8c98ed'
down_revision: Union[str, Sequence[str], None] = '789c8385e9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Clean up duplicates: keep most recent (highest version) per (connection_id, vendor_field)
    op.execute("""
        DELETE FROM mapping_registry
        WHERE id IN (
            SELECT id FROM (
                SELECT id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY connection_id, vendor_field 
                           ORDER BY version DESC, created_at DESC
                       ) as rn
                FROM mapping_registry
            ) t
            WHERE t.rn > 1
        )
    """)
    
    # Add unique constraint on (connection_id, vendor_field)
    op.create_index(
        'ux_mapping_registry_conn_field',
        'mapping_registry',
        ['connection_id', 'vendor_field'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ux_mapping_registry_conn_field', 'mapping_registry')
