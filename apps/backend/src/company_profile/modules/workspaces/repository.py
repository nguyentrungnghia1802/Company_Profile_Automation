"""Scoped repositories for User, Workspace, and WorkspaceMember entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from company_profile.db.models.identity import User, Workspace, WorkspaceMember

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    """Repository for User persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by UUID primary key."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_auth(self, provider: str, subject: str) -> User | None:
        """Get user by authentication provider and subject claim."""
        stmt = select(User).where(User.auth_provider == provider, User.auth_subject == subject)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create and persist a new user."""
        self.session.add(user)
        await self.session.flush()
        return user


class WorkspaceRepository:
    """Repository for Workspace persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Get workspace by UUID primary key."""
        result = await self.session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Workspace | None:
        """Get workspace by slug identifier."""
        result = await self.session.execute(select(Workspace).where(Workspace.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, workspace: Workspace) -> Workspace:
        """Create and persist a new workspace."""
        self.session.add(workspace)
        await self.session.flush()
        return workspace


class WorkspaceMemberRepository:
    """Repository for WorkspaceMember persistence operations with workspace scoping."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """Get user membership record in a specific workspace."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> Sequence[WorkspaceMember]:
        """List all active members for a workspace."""
        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_membership(self, member: WorkspaceMember) -> WorkspaceMember:
        """Create and persist a new workspace membership."""
        self.session.add(member)
        await self.session.flush()
        return member
