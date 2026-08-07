"""API integration and security isolation tests for sources and domain policies endpoints."""

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
async def test_sources_and_domain_policies_api_flow(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify adding sources, managing domain policies, and enforcing blocked domain rules."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(
        Workspace(id=DEV_WORKSPACE_ID, name="Sources API WS", slug="src-api-ws")
    )
    admin = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_sources_admin",
            email="sources_admin@example.com",
            display_name="Sources Admin",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws.id, user_id=admin.id, role="workspace_admin", status="active"
        )
    )

    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Domain Policy Corp",
            normalized_name="domain policy corp",
            status="published",
        )
    )

    headers = {
        "Authorization": "Bearer sub_sources_admin",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Add valid source URL
    res_add_source = await async_client.post(
        "/api/v1/sources",
        headers=headers,
        json={"company_id": str(company.id), "url": "https://valid.example.com/about"},
    )
    assert res_add_source.status_code == 200
    assert res_add_source.json()["data"]["domain"] == "valid.example.com"

    # 2. Add blocked domain policy for spam.com
    res_add_pol = await async_client.post(
        "/api/v1/domain-policies",
        headers=headers,
        json={"domain": "spam.com", "policy_type": "blocked", "reason": "Spam directory domain"},
    )
    assert res_add_pol.status_code == 200
    pol_id = res_add_pol.json()["data"]["id"]

    # 3. Attempt to add source from blocked domain -> 400 Bad Request DOMAIN_BLOCKED
    res_blocked = await async_client.post(
        "/api/v1/sources",
        headers=headers,
        json={"company_id": str(company.id), "url": "https://spam.com/company/123"},
    )
    assert res_blocked.status_code == 400
    assert res_blocked.json()["error"]["code"] == "DOMAIN_BLOCKED"

    # 4. List domain policies
    res_list_pols = await async_client.get("/api/v1/domain-policies", headers=headers)
    assert res_list_pols.status_code == 200
    assert len(res_list_pols.json()["data"]) == 1

    # 5. Delete domain policy
    res_del_pol = await async_client.delete(f"/api/v1/domain-policies/{pol_id}", headers=headers)
    assert res_del_pol.status_code == 200


@pytest.mark.asyncio
async def test_domain_policy_tenant_isolation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify tenant isolation: User in Workspace B cannot delete domain policy in Workspace A."""
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)

    # Workspace A
    ws_a = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Policy WS A", slug="pol-ws-a"))
    user_a = await user_repo.create(
        User(
            id=DEV_ADMIN_ID,
            auth_provider="mock",
            auth_subject="sub_pol_a",
            email="pol_a@example.com",
            display_name="Pol A",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws_a.id, user_id=user_a.id, role="workspace_admin", status="active"
        )
    )

    # Workspace B
    ws_b_id = uuid.uuid4()
    ws_b = await ws_repo.create(Workspace(id=ws_b_id, name="Policy WS B", slug="pol-ws-b"))
    user_b = await user_repo.create(
        User(
            id=DEV_USER_ID,
            auth_provider="mock",
            auth_subject="sub_pol_b",
            email="pol_b@example.com",
            display_name="Pol B",
            status="active",
        )
    )
    await member_repo.create_membership(
        WorkspaceMember(
            workspace_id=ws_b.id, user_id=user_b.id, role="workspace_admin", status="active"
        )
    )

    # User A creates policy in WS A
    headers_a = {"Authorization": "Bearer sub_pol_a", "X-Workspace-ID": str(ws_a.id)}
    res_add = await async_client.post(
        "/api/v1/domain-policies",
        headers=headers_a,
        json={"domain": "block-a.com", "policy_type": "blocked"},
    )
    pol_a_id = res_add.json()["data"]["id"]

    # User B attempts to delete WS A policy with WS B context -> 404 Not Found
    headers_b = {"Authorization": "Bearer sub_pol_b", "X-Workspace-ID": str(ws_b.id)}
    res_cross = await async_client.delete(f"/api/v1/domain-policies/{pol_a_id}", headers=headers_b)
    assert res_cross.status_code == 404
