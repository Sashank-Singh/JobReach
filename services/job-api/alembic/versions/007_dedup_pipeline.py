"""Add deduplication and pipeline tracking fields

Revision ID: 007
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedup columns on jobs
    op.add_column("jobs", sa.Column("duplicate_group_id", sa.UUID(), nullable=True))
    op.add_column("jobs", sa.Column("is_primary_duplicate", sa.Boolean(), server_default=sa.text("true")))
    op.create_index("ix_jobs_duplicate_group", "jobs", ["duplicate_group_id"])

    # Pipeline tracking on applications
    op.add_column("applications", sa.Column("interview_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("applications", sa.Column("pipeline_order", sa.Integer(), server_default="0"))
    op.add_column("applications", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))


def downgrade() -> None:
    op.drop_index("ix_jobs_duplicate_group", table_name="jobs")
    op.drop_column("jobs", "is_primary_duplicate")
    op.drop_column("jobs", "duplicate_group_id")
    op.drop_column("applications", "interview_date")
    op.drop_column("applications", "pipeline_order")
    op.drop_column("applications", "updated_at")
