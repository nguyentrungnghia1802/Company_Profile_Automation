"""Create profile_drafts and draft_field_selections tables.

Revision ID: 20260808_0011
Revises: 20260808_0010
Create Date: 2026-08-08 05:16:10
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0011"
down_revision: str | None = "20260808_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. profile_drafts table
    op.create_table(
        "profile_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="building"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("summary_draft", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('building', 'ready_for_review', 'changes_requested', 'approved', 'superseded', 'discarded')",
            name="ck_profile_drafts_status",
        ),
    )
    op.create_index(
        "ix_profile_drafts_company",
        "profile_drafts",
        ["workspace_id", "company_id", "status"],
    )

    # 2. draft_field_selections table
    op.create_table(
        "draft_field_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(length=128), nullable=False),
        sa.Column("context_key", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(
            "selected_fact_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fact_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("selection_state", sa.String(length=32), nullable=False, server_default="accepted"),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "selection_state IN ('accepted', 'overridden', 'rejected', 'unknown')",
            name="ck_draft_field_selections_state",
        ),
    )
    op.create_index(
        "ix_draft_field_selections_draft",
        "draft_field_selections",
        ["workspace_id", "profile_draft_id", "field_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_draft_field_selections_draft", table_name="draft_field_selections")
    op.drop_table("draft_field_selections")
    op.drop_index("ix_profile_drafts_company", table_name="profile_drafts")
    op.drop_table("profile_drafts")
