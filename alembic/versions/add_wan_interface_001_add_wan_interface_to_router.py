"""add wan_interface to router

Revision ID: add_wan_interface_001
Revises: 3fced6a48079
Create Date: 2025-12-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_wan_interface_001'
down_revision: Union[str, None] = '3fced6a48079'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('router', sa.Column('wan_interface', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('router', 'wan_interface')
