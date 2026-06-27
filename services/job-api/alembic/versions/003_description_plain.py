"""Add description_plain for search

Revision ID: 003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("description_plain", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "description_plain")
