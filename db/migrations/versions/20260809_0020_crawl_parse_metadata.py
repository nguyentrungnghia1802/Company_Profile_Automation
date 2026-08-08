"""Add bounded crawl audit and parser evidence metadata.

Revision ID: 20260809_0020
Revises: 20260808_0019
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0020"
down_revision: str = "20260808_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Persist fetch policy, retry, parser, language, and evidence locations."""
    with op.batch_alter_table("source_snapshots", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=16), nullable=False, server_default="und")
        )
        batch_op.add_column(
            sa.Column(
                "parser_version", sa.String(length=64), nullable=False, server_default="unknown"
            )
        )
        batch_op.add_column(
            sa.Column(
                "parser_status", sa.String(length=32), nullable=False, server_default="pending"
            )
        )
        batch_op.add_column(sa.Column("parser_error", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "ck_source_snapshots_parser_status",
            "parser_status IN ('pending', 'success', 'failed', 'skipped')",
        )

    with op.batch_alter_table("source_fetch_attempts", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("redirect_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "policy_result",
                sa.String(length=64),
                nullable=False,
                server_default="not_evaluated",
            )
        )
        batch_op.add_column(
            sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.drop_constraint("ck_fetch_attempts_outcome", type_="check")
        batch_op.create_check_constraint(
            "ck_fetch_attempts_outcome",
            "outcome_code IN ('success', 'http_error', 'timeout', 'malware_detected', "
            "'size_exceeded', 'decompression_exceeded', 'mime_rejected', "
            "'redirect_blocked', 'max_redirects', 'policy_blocked', "
            "'retry_exhausted', 'parse_error')",
        )

    with op.batch_alter_table("document_blocks", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=16), nullable=False, server_default="und")
        )
        batch_op.add_column(
            sa.Column(
                "parser_version", sa.String(length=64), nullable=False, server_default="unknown"
            )
        )
        batch_op.add_column(sa.Column("page_number", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("section_path", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(
            sa.Column("location", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(
            sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(sa.Column("start_offset", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("end_offset", sa.Integer(), nullable=True))
        batch_op.drop_constraint("ck_document_blocks_type", type_="check")
        batch_op.create_check_constraint(
            "ck_document_blocks_type",
            "block_type IN ('title', 'heading', 'paragraph', 'list', 'table', "
            "'link', 'metadata', 'structured')",
        )


def downgrade() -> None:
    """Remove the crawl/parser metadata while preserving prior task tables."""
    with op.batch_alter_table("document_blocks", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_document_blocks_type", type_="check")
        batch_op.create_check_constraint(
            "ck_document_blocks_type",
            "block_type IN ('heading', 'paragraph', 'table', 'list')",
        )
        for column_name in (
            "end_offset",
            "start_offset",
            "metadata",
            "location",
            "section_path",
            "page_number",
            "parser_version",
            "language",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("source_fetch_attempts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_fetch_attempts_outcome", type_="check")
        batch_op.create_check_constraint(
            "ck_fetch_attempts_outcome",
            "outcome_code IN ('success', 'http_error', 'timeout', "
            "'malware_detected', 'size_exceeded')",
        )
        for column_name in ("retryable", "policy_result", "retry_count", "redirect_count"):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("source_snapshots", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_source_snapshots_parser_status", type_="check")
        for column_name in ("parser_error", "parser_status", "parser_version", "language"):
            batch_op.drop_column(column_name)
