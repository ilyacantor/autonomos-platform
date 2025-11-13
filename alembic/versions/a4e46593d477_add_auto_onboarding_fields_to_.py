"""Add auto-onboarding fields to Connection model

Revision ID: a4e46593d477
Revises: b15b4a5021b3
Create Date: 2025-11-08 18:13:47.288964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a4e46593d477'
down_revision: Union[str, Sequence[str], None] = 'b15b4a5021b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add auto-onboarding fields to connections table."""
    op.add_column('connections', sa.Column('namespace', sa.String(), nullable=False, server_default='demo'))
    op.add_column('connections', sa.Column('first_sync_rows', sa.Integer(), nullable=True))
    op.add_column('connections', sa.Column('latency_ms', sa.Float(), nullable=True))
    op.add_column('connections', sa.Column('credential_locator', sa.String(), nullable=True))
    op.add_column('connections', sa.Column('risk_level', sa.String(), nullable=True))
    op.add_column('connections', sa.Column('evidence', sa.JSON(), nullable=True))
    op.add_column('connections', sa.Column('owner', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove auto-onboarding fields from connections table."""
    op.drop_column('connections', 'owner')
    op.drop_column('connections', 'evidence')
    op.drop_column('connections', 'risk_level')
    op.drop_column('connections', 'credential_locator')
    op.drop_column('connections', 'latency_ms')
    op.drop_column('connections', 'first_sync_rows')
    op.drop_column('connections', 'namespace')
