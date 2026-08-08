"""Add conflicts and conflict_candidates tables.

Revision ID: 20260808_0009
Revises: 20260808_0008
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260808_0009"
down_revision: str = "20260808_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create conflicts and conflict_candidates tables."""
    op.create_table(
        "conflicts",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("company_id", sa.CHAR(36), nullable=False),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("context_key", sa.String(128), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("materiality", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("detected_policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolution_type", sa.String(64), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.CHAR(36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('open', 'needs_research', 'resolved', 'accepted_multiple', 'dismissed', 'reopened')",
            name="ck_conflicts_status",
        ),
        sa.CheckConstraint(
            "materiality IN ('critical', 'high', 'medium', 'low')",
            name="ck_conflicts_materiality",
        ),
    )
    op.create_index(
        "ix_conflicts_company_field",
        "conflicts",
        ["workspace_id", "company_id", "field_key", "status"],
    )

    op.create_table(
        "conflict_candidates",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("conflict_id", sa.CHAR(36), nullable=False),
        sa.Column("fact_candidate_id", sa.CHAR(36), nullable=False),
        sa.Column("candidate_role", sa.String(32), nullable=False, server_default="competing"),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conflict_id"], ["conflicts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fact_candidate_id"], ["fact_candidates.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "candidate_role IN ('primary', 'competing')",
            name="ck_conflict_candidates_role",
        ),
        sa.UniqueConstraint("conflict_id", "fact_candidate_id", name="uq_conflict_candidates_pair"),
    )
    op.create_index(
        "ix_conflict_candidates_conflict",
        "conflict_candidates",
        ["workspace_id", "conflict_id"],
    )


def downgrade() -> None:
    """Drop conflict_candidates and conflicts tables."""
    op.drop_index("ix_conflict_candidates_conflict", table_name="conflict_candidates")
    op.drop_table("conflict_candidates")
    op.drop_index("ix_conflicts_company_field", table_name="conflicts")
    op.drop_table("conflicts")
