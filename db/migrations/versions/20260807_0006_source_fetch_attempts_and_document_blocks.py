"""Source fetch attempts and document blocks schema migration.

Revision ID: 20260807_0006
Revises: 20260807_0005
Create Date: 2026-08-07 18:40:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260807_0006"
down_revision = "20260807_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. source_fetch_attempts
    op.create_table(
        "source_fetch_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_job_id", sa.String(36), sa.ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("adapter", sa.String(64), nullable=False, server_default="httpx"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("byte_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outcome_code", sa.String(32), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "outcome_code IN ('success', 'http_error', 'timeout', 'malware_detected', 'size_exceeded')",
            name="ck_fetch_attempts_outcome",
        ),
    )

    op.create_index("ix_source_fetch_attempts_source", "source_fetch_attempts", ["workspace_id", "source_id"])

    # 2. document_blocks
    op.create_table(
        "document_blocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_key", sa.String(128), nullable=False),
        sa.Column("block_type", sa.String(32), nullable=False, server_default="paragraph"),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("block_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "block_type IN ('heading', 'paragraph', 'table', 'list')",
            name="ck_document_blocks_type",
        ),
        sa.UniqueConstraint("source_snapshot_id", "block_key", name="uq_document_blocks_key"),
    )

    op.create_index("ix_document_blocks_snapshot", "document_blocks", ["workspace_id", "source_snapshot_id"])


def downgrade() -> None:
    op.drop_table("document_blocks")
    op.drop_table("source_fetch_attempts")
