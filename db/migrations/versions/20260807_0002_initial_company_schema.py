"""initial company schema migration

Revision ID: 20260807_0002
Revises: 20260807_0001
Create Date: 2026-08-07 10:38:00.000000

"""

from __future__ import annotations

import alembic.op as op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260807_0002"
down_revision: str | None = "20260807_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. company_profiles
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.CHAR(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tax_id", sa.String(length=50), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("founding_date", sa.Date(), nullable=True),
        sa.Column("headquarters_address", sa.Text(), nullable=True),
        sa.Column("primary_phone", sa.String(length=50), nullable=True),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "merged_into_id",
            sa.CHAR(36),
            sa.ForeignKey("company_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'merged')",
            name="ck_company_profiles_status",
        ),
    )
    op.create_index(
        "ix_company_profiles_workspace_normalized",
        "company_profiles",
        ["workspace_id", "normalized_name"],
    )
    op.create_index(
        "ix_company_profiles_workspace_status",
        "company_profiles",
        ["workspace_id", "status"],
    )

    # 2. company_aliases
    op.create_table(
        "company_aliases",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.CHAR(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.CHAR(36),
            sa.ForeignKey("company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column(
            "alias_type",
            sa.String(length=50),
            nullable=False,
            server_default="trade_name",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "alias_type IN ('trade_name', 'former_name', 'abbreviation', 'misspelling')",
            name="ck_company_aliases_type",
        ),
        sa.UniqueConstraint("workspace_id", "normalized_alias", name="uq_company_aliases_workspace_alias"),
    )
    op.create_index(
        "ix_company_aliases_workspace_normalized",
        "company_aliases",
        ["workspace_id", "normalized_alias"],
    )

    # 3. company_relationships
    op.create_table(
        "company_relationships",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.CHAR(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_company_id",
            sa.CHAR(36),
            sa.ForeignKey("company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_company_id",
            sa.CHAR(36),
            sa.ForeignKey("company_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "source_company_id",
            "target_company_id",
            "relationship_type",
            name="uq_company_relationships",
        ),
    )


def downgrade() -> None:
    op.drop_table("company_relationships")
    op.drop_index("ix_company_aliases_workspace_normalized", table_name="company_aliases")
    op.drop_table("company_aliases")
    op.drop_index("ix_company_profiles_workspace_status", table_name="company_profiles")
    op.drop_index("ix_company_profiles_workspace_normalized", table_name="company_profiles")
    op.drop_table("company_profiles")
