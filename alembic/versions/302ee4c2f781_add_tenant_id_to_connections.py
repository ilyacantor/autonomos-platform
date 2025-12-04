"""add_tenant_id_to_connections

Revision ID: 302ee4c2f781
Revises: e58808620faa
Create Date: 2025-11-12 21:47:39.923339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '302ee4c2f781'
down_revision: Union[str, Sequence[str], None] = 'e58808620faa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id to connections table for multi-tenant isolation"""
    import os
    from sqlalchemy.dialects.postgresql import UUID
    import uuid
    
    # Get or generate DEMO_TENANT_UUID for backfilling existing connections
    demo_tenant_uuid = os.getenv('DEMO_TENANT_UUID', 'f8ab4417-86a1-4dd2-a049-ea423063850e')
    
    # 1. Add tenant_id column (nullable for migration)
    op.add_column('connections', 
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True)
    )
    
    # 2. Backfill existing connections with demo tenant UUID
    op.execute(f"UPDATE connections SET tenant_id = '{demo_tenant_uuid}' WHERE tenant_id IS NULL")
    
    # 3. Add index for performance
    op.create_index('ix_connections_tenant_id', 'connections', ['tenant_id'])


def downgrade() -> None:
    """Remove tenant_id from connections table"""
    op.drop_index('ix_connections_tenant_id', table_name='connections')
    op.drop_column('connections', 'tenant_id')
