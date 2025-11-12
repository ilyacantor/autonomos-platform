"""enforce_tenant_id_not_null_constraint

Revision ID: 196dab551f10
Revises: 302ee4c2f781
Create Date: 2025-11-12 22:56:49.856103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '196dab551f10'
down_revision: Union[str, Sequence[str], None] = '302ee4c2f781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Demo tenant UUID for default and backfill
DEMO_TENANT_UUID = 'f8ab4417-86a1-4dd2-a049-ea423063850e'


def upgrade() -> None:
    """
    Enforce NOT NULL constraint on tenant_id column.
    
    Steps:
    1. Backfill any remaining NULL tenant_id values with demo UUID
    2. Set DEFAULT to demo UUID (for safety, though code should always provide it)
    3. Add NOT NULL constraint to prevent future NULL values
    """
    # Step 1: Backfill any remaining NULL tenant_id values
    # This is a safety measure in case backfill script wasn't run
    op.execute(
        f"UPDATE connections SET tenant_id = '{DEMO_TENANT_UUID}' WHERE tenant_id IS NULL"
    )
    
    # Step 2: Set DEFAULT value for tenant_id column
    # This provides a safety net if code fails to pass tenant_id (shouldn't happen)
    op.alter_column(
        'connections',
        'tenant_id',
        server_default=sa.text(f"'{DEMO_TENANT_UUID}'::uuid"),
        existing_type=UUID(as_uuid=True),
        existing_nullable=True
    )
    
    # Step 3: Add NOT NULL constraint
    # Now that all existing rows have values and there's a default, we can safely add the constraint
    op.alter_column(
        'connections',
        'tenant_id',
        nullable=False,
        existing_type=UUID(as_uuid=True),
        existing_server_default=sa.text(f"'{DEMO_TENANT_UUID}'::uuid")
    )


def downgrade() -> None:
    """
    Remove NOT NULL constraint and DEFAULT from tenant_id column.
    
    This reverts the column to its state after the 302ee4c2f781 migration
    (nullable with index, but no default or NOT NULL constraint).
    """
    # Step 1: Remove NOT NULL constraint
    op.alter_column(
        'connections',
        'tenant_id',
        nullable=True,
        existing_type=UUID(as_uuid=True),
        existing_server_default=sa.text(f"'{DEMO_TENANT_UUID}'::uuid")
    )
    
    # Step 2: Remove DEFAULT value
    op.alter_column(
        'connections',
        'tenant_id',
        server_default=None,
        existing_type=UUID(as_uuid=True),
        existing_nullable=True
    )
