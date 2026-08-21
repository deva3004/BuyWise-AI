"""add users, wire watchlists.user_id to a real FK

Revision ID: b41d9a7f2c53
Revises: 7e66305f2196
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b41d9a7f2c53'
down_revision: Union[str, Sequence[str], None] = '7e66305f2196'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=60), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('username')
    )

    # watchlists.user_id was a bare, client-supplied string with no real
    # identity behind it - existing rows aren't tied to an actual user
    # account, so they're cleared rather than migrated.
    op.execute('DELETE FROM watchlists')

    op.drop_constraint('watchlists_user_id_variant_id_key', 'watchlists', type_='unique')
    op.drop_column('watchlists', 'user_id')
    op.add_column('watchlists', sa.Column('user_id', sa.BigInteger(), nullable=False))
    op.create_foreign_key(
        'watchlists_user_id_fkey', 'watchlists', 'users',
        ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    op.create_unique_constraint('watchlists_user_id_variant_id_key', 'watchlists', ['user_id', 'variant_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('watchlists_user_id_variant_id_key', 'watchlists', type_='unique')
    op.drop_constraint('watchlists_user_id_fkey', 'watchlists', type_='foreignkey')
    op.drop_column('watchlists', 'user_id')
    op.add_column('watchlists', sa.Column('user_id', sa.String(length=100), nullable=False))
    op.create_unique_constraint('watchlists_user_id_variant_id_key', 'watchlists', ['user_id', 'variant_id'])

    op.drop_table('users')
