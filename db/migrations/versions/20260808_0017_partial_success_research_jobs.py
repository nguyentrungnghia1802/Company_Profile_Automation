"""Allow durable research jobs to expose a limited successful result.

Revision ID: 20260808_0017
Revises: 20260808_0016
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0017"
down_revision: str = "20260808_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace the research-job status check with the forward-compatible set."""
    with op.batch_alter_table("research_jobs") as batch_op:
        batch_op.drop_constraint("ck_research_jobs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_research_jobs_status",
            "status IN ("
            "'pending', 'running', 'partial_success', 'completed', 'failed', 'cancelled'"
            ")",
        )


def downgrade() -> None:
    """Reject partial-success rows before restoring the original constraint."""
    connection = op.get_bind()
    partial_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM research_jobs WHERE status = 'partial_success'")
    ).scalar_one()
    if partial_count:
        raise RuntimeError("Cannot downgrade while research_jobs contains partial_success rows.")

    with op.batch_alter_table("research_jobs") as batch_op:
        batch_op.drop_constraint("ck_research_jobs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_research_jobs_status",
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
        )
