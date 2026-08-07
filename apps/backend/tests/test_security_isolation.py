"""Security and cross-workspace tenant isolation verification tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_cross_workspace_isolation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify that a user cannot access or view members of another workspace."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

    # User 1 in Workspace 1
    user1 = await user_repo.create(
        User(
            auth_provider="mock",
            auth_subject="sub_user_1",
            email="user1@example.com",
            display_name="User One",
            status="active",
        )
    )
    ws1 = await ws_repo.create(Workspace(name="Workspace One", slug="ws-one", status="active"))
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws1.id, user_id=user1.id, role="workspace_admin", status="active"
        )
    )

    # Workspace 2 (user1 is NOT a member)
    ws2 = await ws_repo.create(Workspace(name="Workspace Two", slug="ws-two", status="active"))

    headers = {"Authorization": "Bearer sub_user_1"}

    # Attempt to fetch details of Workspace 2 -> expect 403 Forbidden
    res_ws2 = await async_client.get(f"/api/v1/workspaces/{ws2.id}", headers=headers)
    assert res_ws2.status_code == 403
    assert res_ws2.json()["error"]["code"] == "WORKSPACE_ACCESS_DENIED"

    # Attempt to list members of Workspace 2 -> expect 403 Forbidden
    res_members = await async_client.get(f"/api/v1/workspaces/{ws2.id}/members", headers=headers)
    assert res_members.status_code == 403


@pytest.mark.asyncio
async def test_disabled_user_access_denied(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify disabled user is rejected with 403 Forbidden on authenticated endpoints."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        User(
            auth_provider="mock",
            auth_subject="sub_disabled_user",
            email="disabled@example.com",
            display_name="Disabled User",
            status="disabled",
        )
    )

    headers = {"Authorization": f"Bearer {user.auth_subject}"}
    response = await async_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_token_rejected(async_client: AsyncClient) -> None:
    """Verify invalid token is rejected with 401 Unauthorized."""
    headers = {"Authorization": "Bearer mock-token-invalid"}
    response = await async_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_role_capability_matrix_enforcement(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify researcher role lacks member:manage capability while workspace_admin has it."""
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

    researcher = await user_repo.create(
        User(
            auth_provider="mock",
            auth_subject="sub_researcher_only",
            email="researcher_only@example.com",
            display_name="Researcher Only",
            status="active",
        )
    )
    ws = await ws_repo.create(
        Workspace(name="Capability Test WS", slug="cap-test-ws", status="active")
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws.id, user_id=researcher.id, role="researcher", status="active"
        )
    )

    headers = {
        "Authorization": "Bearer sub_researcher_only",
        "X-Workspace-ID": str(ws.id),
    }

    # Researcher attempts to list members -> 403 Forbidden
    response = await async_client.get(f"/api/v1/workspaces/{ws.id}/members", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_CAPABILITY"
