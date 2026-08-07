"""Initial source acquisition schema migration.

Revision ID: 20260807_0004
Revises: 20260807_0003
Create Date: 2026-08-07 18:27:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260807_0004"
down_revision = "20260807_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. sources
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False, server_default="web_page"),
        sa.Column("authority_tier", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(32), nullable=False, server_default="discovered"),
        sa.Column("entity_match_score", sa.Float(), nullable=True),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('registry', 'official_site', 'news', 'directory', 'web_page')",
            name="ck_sources_type",
        ),
        sa.CheckConstraint(
            "status IN ('discovered', 'fetched', 'failed', 'rejected')",
            name="ck_sources_status",
        ),
        sa.UniqueConstraint("workspace_id", "company_id", "normalized_url", name="uq_sources_normalized_url"),
    )

    op.create_index("ix_sources_workspace_company", "sources", ["workspace_id", "company_id"])
    op.create_index("ix_sources_domain", "sources", ["workspace_id", "domain"])

    # 2. source_snapshots
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_provider", sa.String(32), nullable=False, server_default="local"),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False, server_default="text/html"),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("malware_scan_status", sa.String(32), nullable=False, server_default="clean"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "malware_scan_status IN ('clean', 'infected', 'pending')",
            name="ck_source_snapshots_malware_status",
        ),
        sa.UniqueConstraint("source_id", "content_hash", name="uq_source_snapshots_hash"),
    )

    op.create_index("ix_source_snapshots_source_id", "source_snapshots", ["source_id"])


def downgrade() -> None:
    op.drop_table("source_snapshots")
    op.drop_table("sources")
