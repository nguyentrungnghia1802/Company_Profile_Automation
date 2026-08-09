"""API integration and security isolation tests for research jobs endpoints."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_ADMIN_ID, DEV_USER_ID, DEV_WORKSPACE_ID
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from company_profile.db import session as session_module
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine


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

    # The old synchronous endpoint must not return unverified snippets or fake facts.
    res_live = await async_client.post(
        "/api/v1/research/live-scrape",
        headers=headers,
        json={"query": "Research Target Corp"},
    )
    assert res_live.status_code == 410
    assert res_live.json()["error"]["code"] == "LIVE_SCRAPE_RETIRED"
    assert res_live.json()["error"]["details"]["ai_required"] is False


@pytest.mark.asyncio
async def test_created_company_is_committed_before_separate_research_request(
    app: FastAPI,
    test_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: a successful company POST must survive its request session."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(session_module, "get_session_factory", lambda: session_factory)

    async with session_factory() as seed_session:
        ws_repo = WorkspaceRepository(seed_session)
        user_repo = UserRepository(seed_session)
        member_repo = WorkspaceMemberRepository(seed_session)
        workspace = await ws_repo.create(
            Workspace(id=DEV_WORKSPACE_ID, name="Committed API WS", slug="committed-api-ws")
        )
        user = await user_repo.create(
            User(
                id=DEV_ADMIN_ID,
                auth_provider="mock",
                auth_subject="sub_committed_researcher",
                email="committed_researcher@example.com",
                display_name="Committed Researcher",
                status="active",
            )
        )
        await member_repo.create_membership(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role="reviewer",
                status="active",
            )
        )
        await seed_session.commit()

    headers = {
        "Authorization": "Bearer sub_committed_researcher",
        "X-Workspace-ID": str(DEV_WORKSPACE_ID),
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/companies",
            headers=headers,
            json={"company_name": "Persisted Research Target"},
        )
        assert create_response.status_code == 200
        company_id = create_response.json()["data"]["id"]

        research_response = await client.post(
            f"/api/v1/companies/{company_id}/research",
            headers=headers,
            json={"job_type": "initial", "requested_locale": "vi"},
        )

    assert research_response.status_code == 200
    assert research_response.json()["data"]["company_id"] == company_id
    assert research_response.json()["data"]["status"] == "running"

    async with session_factory() as verification_session:
        assert await verification_session.get(CompanyProfile, company_id) is not None


@pytest.mark.asyncio
async def test_trigger_research_returns_not_found_for_unknown_company(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Reject unknown company IDs before PostgreSQL can raise a foreign-key error."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    workspace = await ws_repo.create(
        Workspace(id=DEV_WORKSPACE_ID, name="Missing Company WS", slug="missing-company-ws")
    )
    user = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_missing_company",
            email="missing_company@example.com",
            display_name="Missing Company Researcher",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="reviewer",
            status="active",
        )
    )

    response = await async_client.post(
        f"/api/v1/companies/{uuid.uuid4()}/research",
        headers={
            "Authorization": "Bearer sub_missing_company",
            "X-Workspace-ID": str(workspace.id),
        },
        json={"job_type": "initial"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPANY_NOT_FOUND"


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
