"""Repository for workspace-scoped Company Profile entities and aliases."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import (
    CompanyAlias,
    CompanyProfile,
    CompanyRelationship,
    normalize_company_name,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class CompanyRepository:
    """Workspace-scoped repository for managing company profiles and aliases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company: CompanyProfile) -> CompanyProfile:
        """Create a new company profile."""
        if not company.normalized_name:
            company.normalized_name = normalize_company_name(company.company_name)

        self.session.add(company)
        await self.session.flush()
        # Automatically add primary name as default trade_name alias
        alias = CompanyAlias(
            workspace_id=company.workspace_id,
            company_id=company.id,
            alias_name=company.company_name,
            normalized_alias=company.normalized_name,
            alias_type="trade_name",
        )
        self.session.add(alias)
        await self.session.flush()
        return company

    async def get_by_id(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> CompanyProfile | None:
        """Get company profile by ID within a workspace boundary."""
        stmt = select(CompanyProfile).where(
            CompanyProfile.workspace_id == workspace_id, CompanyProfile.id == company_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_tax_id(self, workspace_id: uuid.UUID, tax_id: str) -> CompanyProfile | None:
        """Find company by tax identification number within a workspace."""
        stmt = select(CompanyProfile).where(
            CompanyProfile.workspace_id == workspace_id, CompanyProfile.tax_id == tax_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_registration_number(
        self, workspace_id: uuid.UUID, reg_num: str
    ) -> CompanyProfile | None:
        """Find company by registration number within a workspace."""
        stmt = select(CompanyProfile).where(
            CompanyProfile.workspace_id == workspace_id,
            CompanyProfile.registration_number == reg_num,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def find_by_exact_name(self, workspace_id: uuid.UUID, name: str) -> CompanyProfile | None:
        """Find company profile by exact normalized company name or alias."""
        normalized = normalize_company_name(name)

        # 1. Search company_profiles by normalized_name
        stmt = select(CompanyProfile).where(
            CompanyProfile.workspace_id == workspace_id,
            CompanyProfile.normalized_name == normalized,
        )
        res = await self.session.execute(stmt)
        company = res.scalar_one_or_none()
        if company:
            return company

        # 2. Search company_aliases by normalized_alias
        stmt_alias = select(CompanyAlias).where(
            CompanyAlias.workspace_id == workspace_id,
            CompanyAlias.normalized_alias == normalized,
        )
        res_alias = await self.session.execute(stmt_alias)
        alias = res_alias.scalar_one_or_none()
        if alias:
            return await self.get_by_id(workspace_id, alias.company_id)

        return None

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[CompanyProfile]:
        """List company profiles for a workspace with optional status filter."""
        stmt = select(CompanyProfile).where(CompanyProfile.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(CompanyProfile.status == status)
        stmt = stmt.order_by(CompanyProfile.company_name.asc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def add_alias(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        alias_name: str,
        alias_type: str = "trade_name",
    ) -> CompanyAlias:
        """Add an alternative name alias for a company profile."""
        normalized = normalize_company_name(alias_name)
        alias = CompanyAlias(
            workspace_id=workspace_id,
            company_id=company_id,
            alias_name=alias_name,
            normalized_alias=normalized,
            alias_type=alias_type,
        )
        self.session.add(alias)
        await self.session.flush()
        return alias

    async def list_aliases(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> Sequence[CompanyAlias]:
        """List all aliases for a company profile."""
        stmt = select(CompanyAlias).where(
            CompanyAlias.workspace_id == workspace_id, CompanyAlias.company_id == company_id
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def add_relationship(
        self,
        workspace_id: uuid.UUID,
        source_company_id: uuid.UUID,
        target_company_id: uuid.UUID,
        relationship_type: str,
        notes: str | None = None,
    ) -> CompanyRelationship:
        """Add a directional relationship between two company profiles."""
        rel = CompanyRelationship(
            workspace_id=workspace_id,
            source_company_id=source_company_id,
            target_company_id=target_company_id,
            relationship_type=relationship_type,
            notes=notes,
        )
        self.session.add(rel)
        await self.session.flush()
        return rel
