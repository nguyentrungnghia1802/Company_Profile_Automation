"""Create profile_versions, profile_field_values, and profile_field_evidences tables.

Revision ID: 20260808_0012
Revises: 20260808_0011
Create Date: 2026-08-08 05:16:15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0012"
down_revision: str | None = "20260808_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. profile_versions table
    op.create_table(
        "profile_versions",
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
            "profile_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_drafts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("policy_set_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("publication_note", sa.Text(), nullable=True),
        sa.Column(
            "published_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawal_reason", sa.Text(), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status IN ('published', 'withdrawn', 'superseded')",
            name="ck_profile_versions_status",
        ),
        sa.UniqueConstraint("company_id", "version_number", name="uq_profile_versions_company_ver"),
    )
    op.create_index(
        "ix_profile_versions_company",
        "profile_versions",
        ["workspace_id", "company_id", "status"],
    )

    # Partial unique index: at most one published version per company
    op.create_index(
        "uq_profile_versions_current_published",
        "profile_versions",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    # 2. profile_field_values table
    op.create_table(
        "profile_field_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(length=128), nullable=False),
        sa.Column("context_key", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("value_type", sa.String(length=32), nullable=False, server_default="string"),
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("display_value", sa.Text(), nullable=True),
        sa.Column("display_status", sa.String(length=32), nullable=False, server_default="verified"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence_explanation", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origin_type", sa.String(length=32), nullable=False, server_default="ai"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "display_status IN ('verified', 'inferred', 'estimated', 'conflicting', 'unknown')",
            name="ck_profile_field_values_display_status",
        ),
    )
    op.create_index(
        "ix_profile_field_values_version",
        "profile_field_values",
        ["workspace_id", "profile_version_id", "field_key"],
    )

    # 3. profile_field_evidences table
    op.create_table(
        "profile_field_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_field_value_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_field_values.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidences.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("original_excerpt", sa.Text(), nullable=False),
        sa.Column("translated_excerpt", sa.Text(), nullable=True),
        sa.Column("source_canonical_url", sa.String(length=2048), nullable=True),
        sa.Column("source_authority_tier", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("support_type", sa.String(length=32), nullable=False, server_default="direct"),
        sa.Column("evidence_quality_score", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.create_index(
        "ix_profile_field_evidences_field_val",
        "profile_field_evidences",
        ["workspace_id", "profile_field_value_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profile_field_evidences_field_val", table_name="profile_field_evidences")
    op.drop_table("profile_field_evidences")
    op.drop_index("ix_profile_field_values_version", table_name="profile_field_values")
    op.drop_table("profile_field_values")
    op.drop_index("uq_profile_versions_current_published", table_name="profile_versions")
    op.drop_index("ix_profile_versions_company", table_name="profile_versions")
    op.drop_table("profile_versions")
