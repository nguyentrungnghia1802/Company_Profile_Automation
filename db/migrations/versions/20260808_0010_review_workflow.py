"""Create review_tasks and review_decisions tables for human review workflow.

Revision ID: 20260808_0010
Revises: 20260808_0009
Create Date: 2026-08-08 05:16:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0010"
down_revision: str | None = "20260808_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. review_tasks table
    op.create_table(
        "review_tasks",
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
        sa.Column(
            "conflict_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conflicts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fact_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fact_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_code", sa.String(length=64), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "task_type IN ('identity_ambiguity', 'high_impact_fact', 'field_conflict', 'publication_approval', 'source_verification')",
            name="ck_review_tasks_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'claimed', 'in_review', 'changes_requested', 'completed', 'cancelled', 'reopened')",
            name="ck_review_tasks_status",
        ),
        sa.CheckConstraint(
            "priority IN ('urgent', 'high', 'medium', 'low')",
            name="ck_review_tasks_priority",
        ),
    )
    op.create_index(
        "ix_review_tasks_ws_status",
        "review_tasks",
        ["workspace_id", "status", "priority", "created_at"],
    )
    op.create_index(
        "ix_review_tasks_company",
        "review_tasks",
        ["workspace_id", "company_id", "status"],
    )

    # 2. review_decisions table (append-only log)
    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "review_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("previous_state_json", sa.Text(), nullable=True),
        sa.Column("new_state_json", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_review_decisions_task",
        "review_decisions",
        ["workspace_id", "review_task_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_decisions_task", table_name="review_decisions")
    op.drop_table("review_decisions")
    op.drop_index("ix_review_tasks_company", table_name="review_tasks")
    op.drop_index("ix_review_tasks_ws_status", table_name="review_tasks")
    op.drop_table("review_tasks")
