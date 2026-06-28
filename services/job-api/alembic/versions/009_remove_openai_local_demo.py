"""Remove OpenAI local demo company and jobs

Revision ID: 009
"""
from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM saved_jobs
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM applications
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM job_locations
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM job_skills
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM job_salary
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM job_embeddings
        WHERE job_id IN (
            SELECT jobs.id
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE companies.slug = 'openai-local-demo'
        )
        """
    )
    op.execute(
        """
        DELETE FROM jobs
        WHERE company_id IN (
            SELECT id FROM companies WHERE slug = 'openai-local-demo'
        )
        """
    )
    op.execute("DELETE FROM companies WHERE slug = 'openai-local-demo'")


def downgrade() -> None:
    pass
