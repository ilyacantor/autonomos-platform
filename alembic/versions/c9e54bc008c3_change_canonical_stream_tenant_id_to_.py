"""change_canonical_stream_tenant_id_to_string

Revision ID: c9e54bc008c3
Revises: 302ee4c2f781
Create Date: 2025-11-17 03:17:19.915445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9e54bc008c3'
down_revision: Union[str, Sequence[str], None] = '302ee4c2f781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - change canonical_streams.tenant_id from UUID to String."""
    # Drop FK constraint first
    op.drop_constraint('canonical_streams_tenant_id_fkey', 'canonical_streams', type_='foreignkey')
    # Change column type from UUID to String
    op.alter_column('canonical_streams', 'tenant_id',
               existing_type=sa.UUID(),
               type_=sa.String(),
               existing_nullable=True)
    # Add index for performance
    op.create_index(op.f('ix_canonical_streams_tenant_id'), 'canonical_streams', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - revert canonical_streams.tenant_id back to UUID."""
    # Drop index
    op.drop_index(op.f('ix_canonical_streams_tenant_id'), table_name='canonical_streams')
    # Change column type from String back to UUID
    op.alter_column('canonical_streams', 'tenant_id',
               existing_type=sa.String(),
               type_=sa.UUID(),
               existing_nullable=True)
    # Restore FK constraint
    op.create_foreign_key('canonical_streams_tenant_id_fkey', 'canonical_streams', 'tenants', ['tenant_id'], ['id'])
