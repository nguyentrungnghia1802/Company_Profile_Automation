"""Create export_jobs table for profile export tracking and private download links.

Revision ID: 20260808_0013
Revises: 20260808_0012
Create Date: 2026-08-08 05:22:15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0013"
down_revision: str | None = "20260808_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
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
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("export_format", sa.String(length=16), nullable=False, server_default="pdf"),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="vi"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("include_source_appendix", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("include_internal_notes", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("storage_provider", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("object_key", sa.String(length=512), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "export_format IN ('pdf', 'json')",
            name="ck_export_jobs_format",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'expired')",
            name="ck_export_jobs_status",
        ),
    )
    op.create_index(
        "ix_export_jobs_version",
        "export_jobs",
        ["workspace_id", "profile_version_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_version", table_name="export_jobs")
    op.drop_table("export_jobs")
