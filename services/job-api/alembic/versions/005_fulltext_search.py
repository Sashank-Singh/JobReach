"""Add full-text search vector and GIN index

Revision ID: 005
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tsvector column
    op.add_column(
        "jobs",
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            nullable=True,
        ),
    )

    # Create trigger function to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION jobs_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.description_plain, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER trg_jobs_search_vector
        BEFORE INSERT OR UPDATE OF title, description_plain ON jobs
        FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_update();
    """)

    # Create GIN index
    op.execute("CREATE INDEX ix_jobs_search_vector ON jobs USING GIN (search_vector)")

    # Backfill existing rows
    op.execute("UPDATE jobs SET search_vector = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description_plain, ''))")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_jobs_search_vector ON jobs")
    op.execute("DROP FUNCTION IF EXISTS jobs_search_vector_update()")
    op.drop_index("ix_jobs_search_vector", table_name="jobs")
    op.drop_column("jobs", "search_vector")
