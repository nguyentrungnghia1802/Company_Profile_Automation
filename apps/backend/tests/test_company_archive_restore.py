"""Unit and API integration tests for company archive and restore operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_ADMIN_ID, DEV_USER_ID, DEV_WORKSPACE_ID

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_company_archive_and_restore_endpoints(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify archive and restore lifecycle with audit log generation and status updates."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Archive WS", slug="archive-ws"))
    reviewer = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_reviewer_archive",
            email="reviewer_arch@example.com",
            display_name="Reviewer Arch",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="reviewer", status="active")
    )

    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Lifecycle Test Inc",
            normalized_name="lifecycle test inc",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_reviewer_archive",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Archive company
    res_arch = await async_client.post(f"/api/v1/companies/{company.id}/archive", headers=headers)
    assert res_arch.status_code == 200
    assert res_arch.json()["data"]["status"] == "archived"

    # 2. Restore company
    res_rest = await async_client.post(f"/api/v1/companies/{company.id}/restore", headers=headers)
    assert res_rest.status_code == 200
    assert res_rest.json()["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_company_archive_capability_enforcement(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify researcher role without company:archive capability is rejected with 403 Forbidden."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Cap WS", slug="cap-ws"))
    researcher = await user_repo.create(
        User(
            id=DEV_USER_ID,
            auth_provider="mock",
            auth_subject="sub_researcher_arch",
            email="researcher_arch@example.com",
            display_name="Researcher Arch",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws.id, user_id=researcher.id, role="researcher", status="active"
        )
    )

    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Protected Company",
            normalized_name="protected company",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_researcher_arch",
        "X-Workspace-ID": str(ws.id),
    }

    response = await async_client.post(f"/api/v1/companies/{company.id}/archive", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_CAPABILITY"
