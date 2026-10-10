"""add phone and farmer id to audit logs

Revision ID: 597d344597fc
Revises: 1f6c79e39c5b
Create Date: 2026-10-09 20:05:17.815080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '597d344597fc'
down_revision: Union[str, Sequence[str], None] = '1f6c79e39c5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
