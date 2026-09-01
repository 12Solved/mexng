"""drop mailbox_state table

Revision ID: 2bb9e6b0bb89
Revises: 49903a578ea9
Create Date: 2026-09-01 11:17:07.209311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bb9e6b0bb89'
down_revision: Union[str, Sequence[str], None] = '49903a578ea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('mailbox_state')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('mailbox_state',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email_account', sa.Text(), nullable=False),
    sa.Column('mailbox', sa.Text(), nullable=False),
    sa.Column('uidvalidity', sa.Text(), nullable=True),
    sa.Column('last_seen_uid', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email_account', 'mailbox', name='_mailbox_account_uc')
    )
