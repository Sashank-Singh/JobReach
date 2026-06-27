"""Initial schema for Dev 2 Referral Service

Revision ID: referral_001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "referral_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_campaigns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(512), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("job_context", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_referral_campaign_user_job"),
    )
    op.create_index("ix_referral_campaigns_user_id", "referral_campaigns", ["user_id"])
    op.create_index("ix_referral_campaigns_job_id", "referral_campaigns", ["job_id"])

    op.create_table(
        "referral_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("headline", sa.String(512)),
        sa.Column("summary", sa.Text()),
        sa.Column("skills", postgresql.JSONB(), nullable=False),
        sa.Column("schools", postgresql.JSONB(), nullable=False),
        sa.Column("target_roles", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_referral_profiles_user_id", "referral_profiles", ["user_id"])

    op.create_table(
        "referral_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512)),
        sa.Column("company", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("profile_url", sa.String(1024)),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["referral_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "profile_url", name="uq_candidate_campaign_profile"),
    )
    op.create_index("ix_referral_candidates_user_id", "referral_candidates", ["user_id"])
    op.create_index("ix_referral_candidates_campaign_id", "referral_candidates", ["campaign_id"])
    op.create_index("ix_referral_candidates_profile_url", "referral_candidates", ["profile_url"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID()),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["referral_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outreach_messages_user_id", "outreach_messages", ["user_id"])
    op.create_index("ix_outreach_messages_campaign_id", "outreach_messages", ["campaign_id"])
    op.create_index("ix_outreach_messages_status", "outreach_messages", ["status"])

    op.create_table(
        "conversation_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID()),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["referral_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_events_user_id", "conversation_events", ["user_id"])
    op.create_index("ix_conversation_events_campaign_id", "conversation_events", ["campaign_id"])

    op.create_table(
        "followups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID()),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["referral_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_followups_user_id", "followups", ["user_id"])
    op.create_index("ix_followups_due_at", "followups", ["due_at"])

    op.create_table(
        "extension_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    for table in [
        "extension_sessions",
        "followups",
        "conversation_events",
        "outreach_messages",
        "referral_candidates",
        "referral_profiles",
        "referral_campaigns",
    ]:
        op.drop_table(table)
