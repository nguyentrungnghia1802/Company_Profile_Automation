"""Create policy_sets table for versioned immutable configuration.

Revision ID: 20260808_0014
Revises: 20260808_0013
Create Date: 2026-08-08 05:57:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0014"
down_revision: str | None = "20260808_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, server_default="Default Workspace Policy"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_policy_sets_version",
        "policy_sets",
        ["workspace_id", "version_number"],
        unique=True,
    )
    # Partial index enforcing at most one active policy per workspace
    op.create_index(
        "uq_policy_sets_active",
        "policy_sets",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_policy_sets_active", table_name="policy_sets")
    op.drop_index("ix_policy_sets_version", table_name="policy_sets")
    op.drop_table("policy_sets")
