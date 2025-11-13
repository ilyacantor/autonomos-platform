"""Add DRIFTED status to connectionstatus enum

Revision ID: e58808620faa
Revises: 0cf63f8c98ed
Create Date: 2025-11-12 18:46:26.847709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e58808620faa'
down_revision: Union[str, Sequence[str], None] = '0cf63f8c98ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add DRIFTED to connectionstatus enum
    op.execute("ALTER TYPE connectionstatus ADD VALUE IF NOT EXISTS 'DRIFTED'")


def downgrade() -> None:
    """Downgrade schema."""
    # Cannot remove enum values in PostgreSQL without recreating the enum
    pass
