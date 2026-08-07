"""SQLAlchemy models for identity and membership: User, Workspace, WorkspaceMember."""

from __future__ import annotations

import uuid  # noqa: TC003
from datetime import datetime  # noqa: TC003

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity linked to authentication subject."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_provider", "auth_subject", name="uq_users_auth_provider_subject"),
        CheckConstraint("status IN ('active', 'invited', 'disabled')", name="ck_users_status"),
    )

    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="vi")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    memberships: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace entity representing tenant boundary."""

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'archived')", name="ck_workspaces_status"
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    default_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="vi")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    active_policy_set_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # Relationships
    members: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace membership linking user to workspace with specific role."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
        CheckConstraint(
            "role IN ('researcher', 'reviewer', 'officer', 'workspace_admin')",
            name="ck_workspace_members_role",
        ),
        CheckConstraint(
            "status IN ('active', 'invited', 'disabled')",
            name="ck_workspace_members_status",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="researcher")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="memberships")
    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="members")
