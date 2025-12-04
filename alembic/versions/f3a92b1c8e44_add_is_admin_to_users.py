"""add_is_admin_to_users

Revision ID: f3a92b1c8e44
Revises: a01b6d6912e0
Create Date: 2025-11-18 18:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a92b1c8e44'
down_revision: Union[str, Sequence[str], None] = 'a01b6d6912e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_admin column to users table."""
    op.add_column('users', sa.Column('is_admin', sa.String(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove is_admin column from users table."""
    op.drop_column('users', 'is_admin')
