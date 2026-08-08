"""Add source discovery provenance, provider, and field authority metadata.

Revision ID: 20260808_0018
Revises: 20260808_0017
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0018"
down_revision: str = "20260808_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add explainable discovery metadata without rewriting existing source rows."""
    with op.batch_alter_table("sources") as batch_op:
        batch_op.add_column(
            sa.Column(
                "discovered_via",
                sa.String(64),
                nullable=False,
                server_default="manual_url",
            )
        )
        batch_op.add_column(sa.Column("provider", sa.String(128), nullable=True))
        batch_op.add_column(
            sa.Column(
                "authority_by_field",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "discovery_provenance",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(sa.Column("selection_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove only the metadata introduced by this migration."""
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("selection_reason")
        batch_op.drop_column("discovery_provenance")
        batch_op.drop_column("authority_by_field")
        batch_op.drop_column("provider")
        batch_op.drop_column("discovered_via")
