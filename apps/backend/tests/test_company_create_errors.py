"""Regression tests for duplicate-safe company creation API behavior."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.companies.errors import CompanyDuplicateError
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.companies.service import CompanyService
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_company_returns_actionable_conflict_for_normalized_alias_duplicate(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A duplicate normalized alias is a typed 409, not an opaque database 500."""
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(id=workspace_id, name="Duplicate Test", slug=f"duplicate-{workspace_id.hex[:8]}")
    )
    user = await UserRepository(db_session).create(
        User(
            id=user_id,
            auth_provider="mock",
            auth_subject="sub_company_duplicate_test",
            email="duplicate@example.com",
            display_name="Duplicate Tester",
            status="active",
        )
    )
    await WorkspaceMemberRepository(db_session).create_membership(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="researcher",
            status="active",
        )
    )
    existing = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="VNPT",
            normalized_name="vnpt",
            status="published",
        )
    )

    response = await async_client.post(
        "/api/v1/companies",
        headers={
            "Authorization": "Bearer sub_company_duplicate_test",
            "X-Workspace-ID": str(workspace.id),
        },
        json={"company_name": "Công ty TNHH VNPT", "website_url": "https://vnpt.com.vn/"},
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "COMPANY_DUPLICATE_REVIEW_REQUIRED"
    assert error["retryable"] is False
    assert error["details"] == {
        "submitted_company_name": "Công ty TNHH VNPT",
        "normalized_name": "vnpt",
        "match_reason": "EXACT_NORMALIZED_NAME_OR_ALIAS_MATCH",
        "next_step": (
            "Use the existing company profile or review duplicate candidates before "
            "creating another record."
        ),
        "existing_company_id": str(existing.id),
        "existing_company_name": "VNPT",
    }

    companies = await CompanyRepository(db_session).list_by_workspace(workspace.id)
    assert [company.id for company in companies] == [existing.id]


@pytest.mark.asyncio
async def test_create_company_returns_actionable_conflict_for_exact_tax_id(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A reused tax identifier reports the existing company and match reason."""
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(id=workspace_id, name="Tax Test", slug=f"tax-{workspace_id.hex[:8]}")
    )
    user = await UserRepository(db_session).create(
        User(
            id=user_id,
            auth_provider="mock",
            auth_subject="sub_company_tax_duplicate_test",
            email="tax-duplicate@example.com",
            display_name="Tax Duplicate Tester",
            status="active",
        )
    )
    await WorkspaceMemberRepository(db_session).create_membership(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="researcher",
            status="active",
        )
    )
    existing = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Existing Tax Company",
            normalized_name="existing tax company",
            tax_id="0100100686",
            status="published",
        )
    )

    response = await async_client.post(
        "/api/v1/companies",
        headers={
            "Authorization": "Bearer sub_company_tax_duplicate_test",
            "X-Workspace-ID": str(workspace.id),
        },
        json={"company_name": "Different Display Name", "tax_id": "0100100686"},
    )

    assert response.status_code == 409
    details = response.json()["error"]["details"]
    assert details["match_reason"] == "EXACT_TAX_ID_MATCH"
    assert details["existing_company_id"] == str(existing.id)


@pytest.mark.asyncio
async def test_create_company_maps_normalized_alias_uniqueness_race(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A constraint race after preflight becomes the same typed duplicate outcome."""
    workspace_id = uuid.uuid4()
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(id=workspace_id, name="Race Test", slug=f"race-{workspace_id.hex[:8]}")
    )
    existing = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="VNPT",
            normalized_name="vnpt",
            status="published",
        )
    )
    service = CompanyService(db_session)

    async def _no_preflight_match(**_kwargs: object) -> tuple[None, str]:
        return None, "EXACT_NORMALIZED_NAME_OR_ALIAS_MATCH"

    async def _raise_alias_race(_company: CompanyProfile) -> CompanyProfile:
        raise IntegrityError(
            "INSERT company_aliases",
            {},
            RuntimeError(
                'duplicate key violates unique constraint "uq_company_aliases_workspace_alias"'
            ),
        )

    async def _find_race_winner(_workspace_id: uuid.UUID, _name: str) -> CompanyProfile:
        return existing

    monkeypatch.setattr(service, "_find_creation_duplicate", _no_preflight_match)
    monkeypatch.setattr(service.repo, "create", _raise_alias_race)
    monkeypatch.setattr(service.repo, "find_by_exact_name", _find_race_winner)

    with pytest.raises(CompanyDuplicateError) as error_info:
        await service.create_company(workspace.id, "Công ty TNHH VNPT")

    assert error_info.value.match.existing_company_id == existing.id
    assert error_info.value.match.match_reason == "EXACT_NORMALIZED_NAME_OR_ALIAS_MATCH"
