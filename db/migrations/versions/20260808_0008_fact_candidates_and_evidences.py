"""Add fact_candidates and evidences tables for storing candidate facts and evidence links.

Revision ID: 20260808_0008
Revises: 20260808_0007
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260808_0008"
down_revision: str = "20260808_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create fact_candidates and evidences tables."""
    op.create_table(
        "fact_candidates",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("company_id", sa.CHAR(36), nullable=False),
        sa.Column("research_job_id", sa.CHAR(36), nullable=True),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("context_key", sa.String(128), nullable=False, server_default=""),
        sa.Column("value_type", sa.String(32), nullable=False, server_default="string"),
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("normalized_value_json", sa.Text(), nullable=True),
        sa.Column("display_value", sa.Text(), nullable=True),
        sa.Column("fact_status", sa.String(32), nullable=False, server_default="candidate"),
        sa.Column("origin_type", sa.String(32), nullable=False, server_default="ai"),
        sa.Column("is_inferred", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_unknown", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_components", sa.Text(), nullable=True),
        sa.Column("confidence_explanation", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_status", sa.String(32), nullable=False, server_default="fresh"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_job_id"], ["research_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "fact_status IN ('candidate', 'validated', 'recommended', 'accepted', 'rejected', 'superseded', 'stale')",
            name="ck_fact_candidates_status",
        ),
        sa.CheckConstraint(
            "origin_type IN ('ai', 'deterministic', 'user', 'reviewer', 'import')",
            name="ck_fact_candidates_origin",
        ),
        sa.CheckConstraint(
            "freshness_status IN ('fresh', 'warning', 'stale')",
            name="ck_fact_candidates_freshness",
        ),
    )
    op.create_index(
        "ix_fact_candidates_company_field",
        "fact_candidates",
        ["workspace_id", "company_id", "field_key", "fact_status"],
    )

    op.create_table(
        "evidences",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("workspace_id", sa.CHAR(36), nullable=False),
        sa.Column("fact_candidate_id", sa.CHAR(36), nullable=False),
        sa.Column("source_snapshot_id", sa.CHAR(36), nullable=False),
        sa.Column("document_block_id", sa.CHAR(36), nullable=False),
        sa.Column("original_excerpt", sa.Text(), nullable=False),
        sa.Column("translated_excerpt", sa.Text(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("support_type", sa.String(32), nullable=False, server_default="direct"),
        sa.Column("evidence_quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("extraction_method", sa.String(64), nullable=False, server_default="ai"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fact_candidate_id"], ["fact_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["source_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_block_id"], ["document_blocks.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "support_type IN ('direct', 'structured', 'corroborating', 'contextual', 'contradicting', 'human_note')",
            name="ck_evidences_support_type",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'accepted', 'rejected')",
            name="ck_evidences_review_status",
        ),
        sa.UniqueConstraint("fact_candidate_id", "source_snapshot_id", "document_block_id", name="uq_evidences_candidate_block"),
    )
    op.create_index(
        "ix_evidences_fact_candidate",
        "evidences",
        ["workspace_id", "fact_candidate_id"],
    )


def downgrade() -> None:
    """Drop evidences and fact_candidates tables."""
    op.drop_index("ix_evidences_fact_candidate", table_name="evidences")
    op.drop_table("evidences")
    op.drop_index("ix_fact_candidates_company_field", table_name="fact_candidates")
    op.drop_table("fact_candidates")
