"""Initial research workflow schema migration.

Revision ID: 20260807_0003
Revises: 20260807_0002
Create Date: 2026-08-07 18:15:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260807_0003"
down_revision = "20260807_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. research_jobs
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False, server_default="initial"),
        sa.Column("scope", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("requested_locale", sa.String(10), nullable=False, server_default="vi"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "job_type IN ('initial', 'refresh', 'targeted')",
            name="ck_research_jobs_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_jobs_status",
        ),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_research_jobs_idempotency"),
    )

    op.create_index("ix_research_jobs_workspace_company", "research_jobs", ["workspace_id", "company_id"])
    op.create_index("ix_research_jobs_status", "research_jobs", ["workspace_id", "status"])

    # 2. research_tasks
    op.create_table(
        "research_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_job_id", sa.String(36), sa.ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_payload", sa.Text(), nullable=True),
        sa.Column("output_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_tasks_status",
        ),
    )

    op.create_index("ix_research_tasks_job_id", "research_tasks", ["research_job_id"])
    op.create_index("ix_research_tasks_claim", "research_tasks", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_table("research_tasks")
    op.drop_table("research_jobs")
