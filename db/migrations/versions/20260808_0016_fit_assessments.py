"""add program fit assessments table

Revision ID: 20260808_0016
Revises: 20260808_0015
Create Date: 2026-08-08 13:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0016"
down_revision: Union[str, None] = "20260808_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "program_fit_assessments",
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
        sa.Column("program_name", sa.String(100), nullable=False),
        sa.Column("overall_fit_status", sa.String(32), nullable=False, server_default="review_recommended"),
        sa.Column("fit_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("assessment_json", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("reviewer_override_status", sa.String(32), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_program_fit_assessments_ws_company",
        "program_fit_assessments",
        ["workspace_id", "company_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_program_fit_assessments_ws_company", table_name="program_fit_assessments")
    op.drop_table("program_fit_assessments")
