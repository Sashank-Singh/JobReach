"""Switch embeddings from OpenAI 1536-dim to Gemini 768-dim

Revision ID: 004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM job_embeddings")
    op.execute("UPDATE resumes SET embedding = NULL")

    op.drop_column("job_embeddings", "embedding")
    op.add_column("job_embeddings", sa.Column("embedding", Vector(768), nullable=True))

    op.drop_column("resumes", "embedding")
    op.add_column("resumes", sa.Column("embedding", Vector(768), nullable=True))


def downgrade() -> None:
    op.execute("DELETE FROM job_embeddings")
    op.execute("UPDATE resumes SET embedding = NULL")

    op.drop_column("job_embeddings", "embedding")
    op.add_column("job_embeddings", sa.Column("embedding", Vector(1536), nullable=True))

    op.drop_column("resumes", "embedding")
    op.add_column("resumes", sa.Column("embedding", Vector(1536), nullable=True))
