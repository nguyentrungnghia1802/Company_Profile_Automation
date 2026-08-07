"""Unit and API integration tests for workspace administration routes and audit events."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import (
    DEV_USER_ID,
    DEV_WORKSPACE_ID,
    get_dev_admin,
    get_dev_user,
    get_dev_workspace,
)

from company_profile.db.models.identity import WorkspaceMember
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_workspaces_endpoint(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify GET /api/v1/workspaces lists authorized user workspaces."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

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

    headers = {"Authorization": "Bearer mock-token-researcher"}
    response = await async_client.get("/api/v1/workspaces", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert len(res_data["data"]) == 1
    assert res_data["data"][0]["slug"] == "ai-riser-vn"


@pytest.mark.asyncio
async def test_get_workspace_endpoint(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Verify GET /api/v1/workspaces/:id returns details for authorized member."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

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

    headers = {"Authorization": "Bearer mock-token-researcher"}
    response = await async_client.get(f"/api/v1/workspaces/{DEV_WORKSPACE_ID}", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["name"] == "AI Riser Vietnam"


@pytest.mark.asyncio
async def test_workspace_members_crud(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Verify member listing, invite, role update, and deactivation for workspace admin."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

    admin = await user_repo.create(get_dev_admin())
    ws = await ws_repo.create(get_dev_workspace())
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=admin.id,
            role="workspace_admin",
            status="active",
        )
    )

    headers = {
        "Authorization": "Bearer mock-token-admin",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. List members
    res_list = await async_client.get(f"/api/v1/workspaces/{ws.id}/members", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1

    # 2. Add new member
    res_add = await async_client.post(
        f"/api/v1/workspaces/{ws.id}/members",
        headers=headers,
        json={
            "email": "newmember@example.com",
            "display_name": "New Member",
            "role": "reviewer",
        },
    )
    assert res_add.status_code == 200
    added_member = res_add.json()["data"]
    assert added_member["role"] == "reviewer"
    member_id = added_member["member_id"]

    # 3. Update member role
    res_patch = await async_client.patch(
        f"/api/v1/workspaces/{ws.id}/members/{member_id}",
        headers=headers,
        json={"role": "officer"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["data"]["role"] == "officer"

    # 4. Deactivate member
    res_delete = await async_client.delete(
        f"/api/v1/workspaces/{ws.id}/members/{member_id}", headers=headers
    )
    assert res_delete.status_code == 200
    assert res_delete.json()["data"]["status"] == "disabled"
