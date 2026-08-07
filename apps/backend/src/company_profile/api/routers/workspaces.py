"""Workspace administration and membership management routes."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError, NotFoundError
from company_profile.db.models.identity import User, WorkspaceMember
from company_profile.db.session import get_db_session
from company_profile.db.transaction import transactional
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from company_profile.modules.workspaces.service import WorkspaceService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class WorkspaceResponseData(BaseModel):
    """Workspace detail item."""

    id: uuid.UUID
    name: str
    slug: str
    default_locale: str
    timezone: str
    status: str
    role: str | None = None


class WorkspaceListResponse(BaseModel):
    """Workspace list envelope."""

    success: bool = True
    data: list[WorkspaceResponseData]


class WorkspaceDetailResponse(BaseModel):
    """Workspace detail envelope."""

    success: bool = True
    data: WorkspaceResponseData


class WorkspaceMemberItem(BaseModel):
    """Workspace member detail item."""

    member_id: uuid.UUID
    user_id: uuid.UUID
    email: str | None
    display_name: str
    role: str
    status: str
    version: int


class WorkspaceMemberListResponse(BaseModel):
    """Workspace member list envelope."""

    success: bool = True
    data: list[WorkspaceMemberItem]


class AddMemberRequest(BaseModel):
    """Invite or add member request body."""

    email: EmailStr
    display_name: str | None = None
    role: str = "researcher"


class UpdateMemberRequest(BaseModel):
    """Update member role or status request body."""

    role: str | None = None
    status: str | None = None


class MemberMutationResponse(BaseModel):
    """Workspace member mutation envelope."""

    success: bool = True
    data: WorkspaceMemberItem


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceListResponse:
    """List all authorized workspaces for current actor."""
    ws_repo = WorkspaceRepository(session)
    items: list[WorkspaceResponseData] = []

    for ws_summary in actor.workspaces:
        ws = await ws_repo.get_by_id(ws_summary.id)
        if ws:
            items.append(
                WorkspaceResponseData(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    default_locale=ws.default_locale,
                    timezone=ws.timezone,
                    status=ws.status,
                    role=ws_summary.role,
                )
            )

    return WorkspaceListResponse(success=True, data=items)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceDetailResponse:
    """Get workspace details for authorized member."""
    # Verify membership
    authorized_summary = next((ws for ws in actor.workspaces if ws.id == workspace_id), None)
    if not authorized_summary:
        raise ForbiddenError(
            code="WORKSPACE_ACCESS_DENIED",
            message="Actor is not a member of the requested workspace.",
        )

    ws_repo = WorkspaceRepository(session)
    ws = await ws_repo.get_by_id(workspace_id)
    if not ws:
        raise NotFoundError(code="WORKSPACE_NOT_FOUND", message="Workspace not found.")

    return WorkspaceDetailResponse(
        success=True,
        data=WorkspaceResponseData(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            default_locale=ws.default_locale,
            timezone=ws.timezone,
            status=ws.status,
            role=authorized_summary.role,
        ),
    )


@router.get("/workspaces/{workspace_id}/members", response_model=WorkspaceMemberListResponse)
async def list_workspace_members(
    workspace_id: uuid.UUID,
    _actor: RequestActor = Depends(require_capability("member:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceMemberListResponse:
    """List all members of a workspace (requires member:manage capability)."""
    member_repo = WorkspaceMemberRepository(session)
    user_repo = UserRepository(session)

    members: Sequence[WorkspaceMember] = await member_repo.list_by_workspace(workspace_id)
    items: list[WorkspaceMemberItem] = []

    for m in members:
        user = await user_repo.get_by_id(m.user_id)
        if user:
            items.append(
                WorkspaceMemberItem(
                    member_id=m.id,
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    role=m.role,
                    status=m.status,
                    version=m.version,
                )
            )

    return WorkspaceMemberListResponse(success=True, data=items)


@router.post("/workspaces/{workspace_id}/members", response_model=MemberMutationResponse)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    payload: AddMemberRequest,
    _actor: RequestActor = Depends(require_capability("member:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> MemberMutationResponse:
    """Invite or add a user to the workspace."""
    user_repo = UserRepository(session)
    member_repo = WorkspaceMemberRepository(session)

    # Check if user exists by email or create
    stmt = select(User).where(User.email == payload.email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    async with transactional(session):
        if not user:
            user = User(
                auth_provider="invited",
                auth_subject=f"invited_{uuid.uuid4()}",
                email=payload.email,
                display_name=payload.display_name or payload.email.split("@")[0],
                status="invited",
            )
            await user_repo.create(user)

        existing_member = await member_repo.get_membership(workspace_id, user.id)
        if existing_member:
            existing_member.status = "active"
            existing_member.role = payload.role
            existing_member.version += 1
            member = existing_member
        else:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user.id,
                role=payload.role,
                status="active",
            )
            await member_repo.create_membership(member)

    return MemberMutationResponse(
        success=True,
        data=WorkspaceMemberItem(
            member_id=member.id,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=member.role,
            status=member.status,
            version=member.version,
        ),
    )


@router.patch(
    "/workspaces/{workspace_id}/members/{member_id}", response_model=MemberMutationResponse
)
async def update_workspace_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: UpdateMemberRequest,
    actor: RequestActor = Depends(require_capability("member:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> MemberMutationResponse:
    """Update role or status of a workspace member."""
    service = WorkspaceService(session)
    user_repo = UserRepository(session)

    stmt = select(WorkspaceMember).where(
        WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id
    )
    res = await session.execute(stmt)
    member = res.scalar_one_or_none()
    if not member:
        raise NotFoundError(code="MEMBER_NOT_FOUND", message="Workspace member not found.")

    if payload.role:
        member = await service.update_member_role(
            workspace_id, member.user_id, payload.role, actor_id=str(actor.user_id)
        )

    if payload.status:
        member = await service.update_member_status(
            workspace_id, member.user_id, payload.status, actor_id=str(actor.user_id)
        )

    user = await user_repo.get_by_id(member.user_id)
    if not user:
        raise NotFoundError(code="USER_NOT_FOUND", message="User not found.")

    return MemberMutationResponse(
        success=True,
        data=WorkspaceMemberItem(
            member_id=member.id,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=member.role,
            status=member.status,
            version=member.version,
        ),
    )


@router.delete(
    "/workspaces/{workspace_id}/members/{member_id}", response_model=MemberMutationResponse
)
async def deactivate_workspace_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("member:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> MemberMutationResponse:
    """Deactivate a member's workspace membership."""
    service = WorkspaceService(session)
    user_repo = UserRepository(session)

    stmt = select(WorkspaceMember).where(
        WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id
    )
    res = await session.execute(stmt)
    member = res.scalar_one_or_none()
    if not member:
        raise NotFoundError(code="MEMBER_NOT_FOUND", message="Workspace member not found.")

    deactivated = await service.update_member_status(
        workspace_id, member.user_id, "disabled", actor_id=str(actor.user_id)
    )

    user = await user_repo.get_by_id(deactivated.user_id)
    if not user:
        raise NotFoundError(code="USER_NOT_FOUND", message="User not found.")

    return MemberMutationResponse(
        success=True,
        data=WorkspaceMemberItem(
            member_id=deactivated.id,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=deactivated.role,
            status=deactivated.status,
            version=deactivated.version,
        ),
    )
