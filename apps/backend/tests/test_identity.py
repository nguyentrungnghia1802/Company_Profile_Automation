"""Unit and integration tests for identity models, repositories, and workspace service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import (
    DEV_ADMIN_ID,
    DEV_USER_ID,
    DEV_WORKSPACE_ID,
    get_dev_admin,
    get_dev_memberships,
    get_dev_user,
    get_dev_workspace,
)

from company_profile.api.errors import NotFoundError
from company_profile.db.models.identity import WorkspaceMember
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from company_profile.modules.workspaces.service import WorkspaceService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_identity_fixtures() -> None:
    """Verify identity fixtures contain expected properties."""
    user = get_dev_user()
    admin = get_dev_admin()
    workspace = get_dev_workspace()
    memberships = get_dev_memberships()

    assert user.id == DEV_USER_ID
    assert admin.id == DEV_ADMIN_ID
    assert workspace.id == DEV_WORKSPACE_ID
    assert len(memberships) == 3


@pytest.mark.asyncio
async def test_user_repository(db_session: AsyncSession) -> None:
    """Verify UserRepository create and get methods."""
    user_repo = UserRepository(db_session)
    user = get_dev_user()

    created = await user_repo.create(user)
    assert created.id == DEV_USER_ID

    fetched = await user_repo.get_by_id(DEV_USER_ID)
    assert fetched is not None
    assert fetched.email == "researcher@example.com"

    auth_fetched = await user_repo.get_by_auth("mock", "sub_dev_researcher_001")
    assert auth_fetched is not None
    assert auth_fetched.id == DEV_USER_ID


@pytest.mark.asyncio
async def test_workspace_repository(db_session: AsyncSession) -> None:
    """Verify WorkspaceRepository create and get methods."""
    ws_repo = WorkspaceRepository(db_session)
    workspace = get_dev_workspace()

    created = await ws_repo.create(workspace)
    assert created.id == DEV_WORKSPACE_ID

    fetched_slug = await ws_repo.get_by_slug("ai-riser-vn")
    assert fetched_slug is not None
    assert fetched_slug.name == "AI Riser Vietnam"


@pytest.mark.asyncio
async def test_workspace_member_repository(db_session: AsyncSession) -> None:
    """Verify WorkspaceMemberRepository persistence and listing."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

    await user_repo.create(get_dev_user())
    await ws_repo.create(get_dev_workspace())

    member = WorkspaceMember(
        workspace_id=DEV_WORKSPACE_ID,
        user_id=DEV_USER_ID,
        role="researcher",
        status="active",
    )
    await member_repo.create_membership(member)

    fetched = await member_repo.get_membership(DEV_WORKSPACE_ID, DEV_USER_ID)
    assert fetched is not None
    assert fetched.role == "researcher"

    members = await member_repo.list_by_workspace(DEV_WORKSPACE_ID)
    assert len(members) == 1


@pytest.mark.asyncio
async def test_workspace_service(db_session: AsyncSession) -> None:
    """Verify WorkspaceService member status and role updates with audit events."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    service = WorkspaceService(db_session)

    await user_repo.create(get_dev_user())
    await ws_repo.create(get_dev_workspace())
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=DEV_WORKSPACE_ID,
            user_id=DEV_USER_ID,
            role="researcher",
            status="active",
        )
    )

    # Test role update
    updated = await service.update_member_role(
        DEV_WORKSPACE_ID, DEV_USER_ID, "reviewer", actor_id="admin_001"
    )
    assert updated.role == "reviewer"
    assert updated.version == 2

    # Test status update
    deactivated = await service.update_member_status(
        DEV_WORKSPACE_ID, DEV_USER_ID, "disabled", actor_id="admin_001"
    )
    assert deactivated.status == "disabled"

    # Test missing member
    with pytest.raises(NotFoundError):
        await service.update_member_role(
            DEV_WORKSPACE_ID, uuid.uuid4(), "reviewer", actor_id="admin_001"
        )
