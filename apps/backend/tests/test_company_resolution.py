"""Unit and API integration tests for duplicate candidate resolution and company merging."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_ADMIN_ID, DEV_WORKSPACE_ID

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
async def test_duplicate_candidate_resolution_endpoint(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify POST /api/v1/companies/resolve scores strong and weak identity signals."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    # Setup admin user & workspace
    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Resolution WS", slug="res-ws"))
    user = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_res_admin",
            email="resadmin@example.com",
            display_name="Res Admin",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="reviewer", status="active")
    )

    # Existing company in DB with tax_id
    await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Công ty TNHH AI Riser Việt Nam",
            normalized_name="ai riser viet nam",
            tax_id="0101234567",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_res_admin",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Resolve with matching Tax ID -> expect match_score 1.0
    res_tax = await async_client.post(
        "/api/v1/companies/resolve",
        headers=headers,
        json={"company_name": "AI Riser VN", "tax_id": "0101234567"},
    )
    assert res_tax.status_code == 200
    candidates_tax = res_tax.json()["data"]
    assert len(candidates_tax) == 1
    assert candidates_tax[0]["match_score"] == 1.0
    assert candidates_tax[0]["match_reason"] == "EXACT_TAX_ID_MATCH"

    # 2. Resolve with exact normalized name -> expect match_score 0.85
    res_name = await async_client.post(
        "/api/v1/companies/resolve",
        headers=headers,
        json={"company_name": "AI Riser Viet Nam"},
    )
    assert res_name.status_code == 200
    candidates_name = res_name.json()["data"]
    assert len(candidates_name) == 1
    assert candidates_name[0]["match_score"] == 0.85
    assert candidates_name[0]["match_reason"] == "EXACT_NORMALIZED_NAME_MATCH"


@pytest.mark.asyncio
async def test_company_merge_service_and_endpoint(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify POST /api/v1/companies/:id/merge merges source into target."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Merge WS", slug="merge-ws"))
    user = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_reviewer_merge",
            email="reviewer@example.com",
            display_name="Reviewer User",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="reviewer", status="active")
    )

    source = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Old Trading Corp",
            normalized_name="old trading corp",
            status="draft",
        )
    )
    target = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="New Global Corp",
            normalized_name="new global corp",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_reviewer_merge",
        "X-Workspace-ID": str(ws.id),
    }

    # Call POST /api/v1/companies/{target_id}/merge
    res_merge = await async_client.post(
        f"/api/v1/companies/{target.id}/merge",
        headers=headers,
        json={"source_company_id": str(source.id)},
    )
    assert res_merge.status_code == 200
    res_data = res_merge.json()["data"]
    assert res_data["id"] == str(target.id)

    # Check updated source status
    source_refreshed = await comp_repo.get_by_id(ws.id, source.id)
    assert source_refreshed is not None
    assert source_refreshed.status == "merged"
    assert source_refreshed.merged_into_id == target.id

    # Check former_name alias added to target company
    target_aliases = await comp_repo.list_aliases(ws.id, target.id)
    former_names = [a for a in target_aliases if a.alias_type == "former_name"]
    assert len(former_names) == 1
    assert former_names[0].alias_name == "Old Trading Corp"
