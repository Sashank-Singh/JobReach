"""Remove OpenAI referral campaigns

Revision ID: referral_002
"""
from typing import Sequence, Union

from alembic import op

revision: str = "referral_002"
down_revision: Union[str, None] = "referral_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM referral_campaigns
        WHERE lower(company_name) = 'openai'
           OR lower(coalesce(job_context #>> '{company,name}', '')) = 'openai'
           OR lower(coalesce(job_context ->> 'company_name', '')) = 'openai'
        """
    )


def downgrade() -> None:
    pass
