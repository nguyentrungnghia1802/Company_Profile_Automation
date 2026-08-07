"""Unit tests for company models, normalization, repository, and service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.company_fixtures import (
    DEV_COMPANY_ID,
    DEV_COMPANY_TAX_ID,
    get_dev_company,
)
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID, get_dev_workspace

from company_profile.db.models.company import normalize_company_name
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.companies.service import CompanyService
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def test_normalize_company_name() -> None:
    """Verify name normalization strips accents and legal noise words."""
    assert normalize_company_name("Công ty TNHH AI Riser Việt Nam") == "ai riser viet nam"
    assert normalize_company_name("Cổ phần FPT Corp") == "fpt"
    assert normalize_company_name("VinGroup Inc.") == "vingroup"


@pytest.mark.asyncio
async def test_company_repository_crud(db_session: AsyncSession) -> None:
    """Verify CompanyRepository creation, alias generation, and lookups."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    await ws_repo.create(get_dev_workspace())

    # Create company
    company = await comp_repo.create(get_dev_company())
    assert company.id == DEV_COMPANY_ID

    # Verify lookups by tax_id, reg_num, and exact name
    by_tax = await comp_repo.get_by_tax_id(DEV_WORKSPACE_ID, DEV_COMPANY_TAX_ID)
    assert by_tax is not None
    assert by_tax.company_name == "Công ty TNHH AI Riser Việt Nam"

    by_reg = await comp_repo.get_by_registration_number(DEV_WORKSPACE_ID, "0101234567")
    assert by_reg is not None

    by_name = await comp_repo.find_by_exact_name(DEV_WORKSPACE_ID, "AI Riser Viet Nam")
    assert by_name is not None
    assert by_name.id == DEV_COMPANY_ID

    # Add alias and lookup by alias
    await comp_repo.add_alias(DEV_WORKSPACE_ID, DEV_COMPANY_ID, "AIRiser VN", "abbreviation")
    by_alias = await comp_repo.find_by_exact_name(DEV_WORKSPACE_ID, "AIRiser VN")
    assert by_alias is not None
    assert by_alias.id == DEV_COMPANY_ID


@pytest.mark.asyncio
async def test_company_service_lifecycle(db_session: AsyncSession) -> None:
    """Verify CompanyService create, update, and add_alias methods."""
    ws_repo = WorkspaceRepository(db_session)
    await ws_repo.create(get_dev_workspace())

    service = CompanyService(db_session)

    created = await service.create_company(
        workspace_id=DEV_WORKSPACE_ID,
        company_name="Công ty TNHH Tech Pioneer",
        tax_id="0987654321",
        industry="Technology",
    )
    assert created.company_name == "Công ty TNHH Tech Pioneer"
    assert created.status == "draft"

    updated = await service.update_company(
        workspace_id=DEV_WORKSPACE_ID,
        company_id=created.id,
        updates={"status": "published", "website_url": "https://techpioneer.com"},
    )
    assert updated.status == "published"
    assert updated.version == 2

    alias = await service.add_alias(
        workspace_id=DEV_WORKSPACE_ID,
        company_id=created.id,
        alias_name="TechPioneer",
        alias_type="trade_name",
    )
    assert alias.alias_name == "TechPioneer"
