"""Persist deterministic discovery queries and provider result metadata.

Revision ID: 20260808_0019
Revises: 20260808_0018
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0019"
down_revision: str = "20260808_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workspace-scoped query and search-result audit tables."""
    op.create_table(
        "research_queries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_job_id",
            sa.String(36),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False, server_default="source_discovery"),
        sa.Column("requested_section", sa.String(64), nullable=False, server_default="official"),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column(
            "generated_by",
            sa.String(64),
            nullable=False,
            server_default="deterministic_template",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_research_queries_workspace_job",
        "research_queries",
        ["workspace_id", "research_job_id"],
    )

    op.create_table(
        "search_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_query_id",
            sa.String(36),
            sa.ForeignKey("research_queries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("provider_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "selection_status",
            sa.String(32),
            nullable=False,
            server_default="candidate",
        ),
        sa.Column("selection_reason", sa.Text(), nullable=False),
        sa.Column("entity_match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_type", sa.String(64), nullable=False, server_default="web_page"),
        sa.Column(
            "result_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "selection_status IN ('candidate', 'review', 'selected', 'rejected')",
            name="ck_search_results_selection_status",
        ),
    )
    op.create_index(
        "ix_search_results_workspace_query",
        "search_results",
        ["workspace_id", "research_query_id"],
    )
    op.create_index(
        "ix_search_results_normalized_url",
        "search_results",
        ["workspace_id", "normalized_url"],
    )


def downgrade() -> None:
    """Drop search results before their parent query table."""
    op.drop_index("ix_search_results_normalized_url", table_name="search_results")
    op.drop_index("ix_search_results_workspace_query", table_name="search_results")
    op.drop_table("search_results")
    op.drop_index("ix_research_queries_workspace_job", table_name="research_queries")
    op.drop_table("research_queries")
