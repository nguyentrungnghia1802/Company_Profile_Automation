"""Workspace management application service with immutable audit event logging."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from company_profile.api.errors import NotFoundError
from company_profile.db.transaction import transactional
from company_profile.modules.workspaces.repository import WorkspaceMemberRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.db.models.identity import WorkspaceMember

logger = structlog.get_logger(__name__)


class WorkspaceService:
    """Service for managing workspace membership and role assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.member_repo = WorkspaceMemberRepository(session)

    async def update_member_status(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, new_status: str, actor_id: str
    ) -> WorkspaceMember:
        """Update workspace member status (active/disabled) and emit audit log event."""
        async with transactional(self.session):
            member = await self.member_repo.get_membership(workspace_id, target_user_id)
            if not member:
                raise NotFoundError(code="MEMBER_NOT_FOUND", message="Workspace member not found")

            old_status = member.status
            member.status = new_status
            member.version += 1

            logger.info(
                "membership.status_changed",
                workspace_id=str(workspace_id),
                target_user_id=str(target_user_id),
                old_status=old_status,
                new_status=new_status,
                actor_id=actor_id,
            )
            return member

    async def update_member_role(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, new_role: str, actor_id: str
    ) -> WorkspaceMember:
        """Update workspace member role and emit audit log event."""
        async with transactional(self.session):
            member = await self.member_repo.get_membership(workspace_id, target_user_id)
            if not member:
                raise NotFoundError(code="MEMBER_NOT_FOUND", message="Workspace member not found")

            old_role = member.role
            member.role = new_role
            member.version += 1

            logger.info(
                "membership.role_changed",
                workspace_id=str(workspace_id),
                target_user_id=str(target_user_id),
                old_role=old_role,
                new_role=new_role,
                actor_id=actor_id,
            )
            return member
