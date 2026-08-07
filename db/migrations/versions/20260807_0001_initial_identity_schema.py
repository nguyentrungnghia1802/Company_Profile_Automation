"""Initial identity schema: users, workspaces, workspace_members.

Revision ID: 20260807_0001
Revises:
Create Date: 2026-08-07 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260807_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("auth_provider", sa.String(length=50), nullable=False, server_default="mock"),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("preferred_locale", sa.String(length=10), nullable=False, server_default="vi"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("auth_provider", "auth_subject", name="uq_users_auth_provider_subject"),
        sa.CheckConstraint("status IN ('active', 'invited', 'disabled')", name="ck_users_status"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 2. workspaces
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("default_locale", sa.String(length=10), nullable=False, server_default="vi"),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("active_policy_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'suspended', 'archived')", name="ck_workspaces_status"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    # 3. workspace_members
    op.create_table(
        "workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="researcher"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
        sa.CheckConstraint("role IN ('researcher', 'reviewer', 'officer', 'workspace_admin')", name="ck_workspace_members_role"),
        sa.CheckConstraint("status IN ('active', 'invited', 'disabled')", name="ck_workspace_members_status"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")
