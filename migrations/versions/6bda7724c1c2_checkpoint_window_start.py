"""checkpoint window_start_at

Revision ID: 6bda7724c1c2
Revises: 384e3e669e83
Create Date: 2026-10-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bda7724c1c2'
down_revision: Union[str, Sequence[str], None] = '384e3e669e83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('checkpoints', sa.Column('window_start_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('checkpoints', 'window_start_at')
