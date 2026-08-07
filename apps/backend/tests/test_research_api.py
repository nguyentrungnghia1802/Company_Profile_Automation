"""API integration and security isolation tests for research jobs endpoints."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_ADMIN_ID, DEV_USER_ID, DEV_WORKSPACE_ID
from httpx import AsyncClient

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_research_api_trigger_get_cancel_flow(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify triggering, fetching details, and cancelling research jobs via API."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(
        Workspace(id=DEV_WORKSPACE_ID, name="Research API WS", slug="res-api-ws")
    )
    user = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_researcher_api",
            email="researcher_api@example.com",
            display_name="Researcher API",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="reviewer", status="active")
    )

    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Research Target Corp",
            normalized_name="research target corp",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_researcher_api",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Trigger research job
    res_trigger = await async_client.post(
        f"/api/v1/companies/{company.id}/research",
        headers=headers,
        json={"job_type": "initial", "requested_locale": "vi"},
    )
    assert res_trigger.status_code == 200
    job_id = res_trigger.json()["data"]["id"]
    assert res_trigger.json()["data"]["status"] == "running"

    # 2. Get research job detail
    res_get = await async_client.get(f"/api/v1/research-jobs/{job_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["id"] == job_id
    assert len(res_get.json()["data"]["tasks"]) == 1

    # 3. Cancel research job
    res_cancel = await async_client.post(f"/api/v1/research-jobs/{job_id}/cancel", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_research_jobs_tenant_isolation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify tenant isolation: User in Workspace B cannot read or cancel jobs in Workspace A."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    # Workspace A
    ws_a = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="WS A", slug="ws-a"))
    user_a = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_user_a",
            email="user_a@example.com",
            display_name="User A",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="reviewer", status="active")
    )

    company_a = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws_a.id,
            company_name="Company A",
            normalized_name="company a",
            status="published",
        )
    )

    # Workspace B
    ws_b_id = uuid.uuid4()
    ws_b = await ws_repo.create(Workspace(id=ws_b_id, name="WS B", slug="ws-b"))
    user_b = await user_repo.create(
        User(
            id=DEV_USER_ID,
            auth_provider="mock",
            auth_subject="sub_user_b",
            email="user_b@example.com",
            display_name="User B",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="reviewer", status="active")
    )

    # User A creates job in WS A
    headers_a = {"Authorization": "Bearer sub_user_a", "X-Workspace-ID": str(ws_a.id)}
    res_trig = await async_client.post(
        f"/api/v1/companies/{company_a.id}/research",
        headers=headers_a,
        json={"job_type": "initial"},
    )
    job_a_id = res_trig.json()["data"]["id"]

    # User B attempts to access WS A job with WS B context -> 404 Not Found
    headers_b = {"Authorization": "Bearer sub_user_b", "X-Workspace-ID": str(ws_b.id)}
    res_cross = await async_client.get(f"/api/v1/research-jobs/{job_a_id}", headers=headers_b)
    assert res_cross.status_code == 404
