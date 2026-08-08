"""Add ai_runs table for tracking AI provider usage and extraction results.

Revision ID: 20260808_0007
Revises: 20260807_0006
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260808_0007"
down_revision: str = "20260807_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_runs table with provider metadata, cost, and validation outcome."""
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("company_id", sa.CHAR(36), nullable=True),
        sa.Column("research_job_id", sa.CHAR(36), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False, server_default="mock"),
        sa.Column("model", sa.String(128), nullable=False, server_default="mock"),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("input_token_count", sa.Integer(), nullable=True),
        sa.Column("output_token_count", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("validation_outcome", sa.String(32), nullable=False, server_default="passed"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["research_job_id"],
            ["research_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "operation IN ('extract_identity', 'extract_overview', 'extract_products', "
            "'extract_size', 'extract_markets', 'extract_leadership', 'extract_innovation', "
            "'translate')",
            name="ck_ai_runs_operation",
        ),
        sa.CheckConstraint(
            "validation_outcome IN ('passed', 'failed', 'skipped')",
            name="ck_ai_runs_validation_outcome",
        ),
    )
    op.create_index("ix_ai_runs_workspace_company", "ai_runs", ["workspace_id", "company_id"])
    op.create_index("ix_ai_runs_workspace_operation", "ai_runs", ["workspace_id", "operation"])
    op.create_index(
        "ix_ai_runs_research_job", "ai_runs", ["research_job_id"], postgresql_where=sa.text("research_job_id IS NOT NULL")
    )


def downgrade() -> None:
    """Drop ai_runs table and indexes."""
    op.drop_index("ix_ai_runs_research_job", table_name="ai_runs")
    op.drop_index("ix_ai_runs_workspace_operation", table_name="ai_runs")
    op.drop_index("ix_ai_runs_workspace_company", table_name="ai_runs")
    op.drop_table("ai_runs")
