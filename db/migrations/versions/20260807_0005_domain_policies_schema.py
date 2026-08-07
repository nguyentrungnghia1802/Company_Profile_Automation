"""Domain policies schema migration.

Revision ID: 20260807_0005
Revises: 20260807_0004
Create Date: 2026-08-07 18:35:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260807_0005"
down_revision = "20260807_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "domain_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("policy_type", sa.String(32), nullable=False, server_default="blocked"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "policy_type IN ('blocked', 'allowed', 'trusted')",
            name="ck_domain_policies_type",
        ),
        sa.UniqueConstraint("workspace_id", "domain", name="uq_domain_policies_domain"),
    )

    op.create_index("ix_domain_policies_workspace", "domain_policies", ["workspace_id", "domain"])


def downgrade() -> None:
    op.drop_table("domain_policies")
