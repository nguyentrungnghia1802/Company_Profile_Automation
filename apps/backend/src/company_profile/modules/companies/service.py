"""Application service for Company Profile creation, update, and identity resolution."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from company_profile.db.models.company import CompanyAlias, CompanyProfile
from company_profile.db.transaction import transactional
from company_profile.modules.companies.repository import CompanyRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CompanyService:
    """Service handling company entity lifecycle, resolution, and audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CompanyRepository(session)

    async def create_company(
        self,
        workspace_id: uuid.UUID,
        company_name: str,
        tax_id: str | None = None,
        legal_name: str | None = None,
        registration_number: str | None = None,
        industry: str | None = None,
        website_url: str | None = None,
        headquarters_address: str | None = None,
        primary_phone: str | None = None,
        primary_email: str | None = None,
        actor_id: str | None = None,
    ) -> CompanyProfile:
        """Create a new company profile with audit logging."""
        async with transactional(self.session):
            company = CompanyProfile(
                workspace_id=workspace_id,
                company_name=company_name,
                tax_id=tax_id,
                legal_name=legal_name,
                registration_number=registration_number,
                industry=industry,
                website_url=website_url,
                headquarters_address=headquarters_address,
                primary_phone=primary_phone,
                primary_email=primary_email,
                status="published",
            )
            created = await self.repo.create(company)

            logger.info(
                "Audit Event: company.created",
                extra={
                    "audit_event": "company.created",
                    "workspace_id": str(workspace_id),
                    "company_id": str(created.id),
                    "company_name": company_name,
                    "tax_id": tax_id,
                    "actor_id": actor_id,
                },
            )
            return created

    async def get_company(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> CompanyProfile | None:
        """Fetch company profile by ID."""
        return await self.repo.get_by_id(workspace_id, company_id)

    async def update_company(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        updates: dict[str, Any],
        actor_id: str | None = None,
    ) -> CompanyProfile:
        """Update fields of an existing company profile."""
        async with transactional(self.session):
            company = await self.repo.get_by_id(workspace_id, company_id)
            if not company:
                raise ValueError("COMPANY_NOT_FOUND")

            for field, val in updates.items():
                if hasattr(company, field) and field not in ("id", "workspace_id", "created_at"):
                    setattr(company, field, val)

            company.version += 1
            logger.info(
                "Audit Event: company.updated",
                extra={
                    "audit_event": "company.updated",
                    "workspace_id": str(workspace_id),
                    "company_id": str(company.id),
                    "updated_fields": list(updates.keys()),
                    "version": company.version,
                    "actor_id": actor_id,
                },
            )
            return company

    async def add_alias(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        alias_name: str,
        alias_type: str = "trade_name",
        actor_id: str | None = None,
    ) -> CompanyAlias:
        """Add an alias name for a company profile with audit logging."""
        async with transactional(self.session):
            company = await self.repo.get_by_id(workspace_id, company_id)
            if not company:
                raise ValueError("COMPANY_NOT_FOUND")

            alias = await self.repo.add_alias(
                workspace_id=workspace_id,
                company_id=company_id,
                alias_name=alias_name,
                alias_type=alias_type,
            )

            logger.info(
                "Audit Event: company.alias_added",
                extra={
                    "audit_event": "company.alias_added",
                    "workspace_id": str(workspace_id),
                    "company_id": str(company_id),
                    "alias_name": alias_name,
                    "alias_type": alias_type,
                    "actor_id": actor_id,
                },
            )
            return alias

    async def archive_company(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: str | None = None,
    ) -> CompanyProfile:
        """Archive a company profile with audit logging."""
        async with transactional(self.session):
            company = await self.repo.get_by_id(workspace_id, company_id)
            if not company:
                raise ValueError("COMPANY_NOT_FOUND")

            if company.status == "archived":
                return company

            company.status = "archived"
            company.version += 1

            logger.info(
                "Audit Event: company.archived",
                extra={
                    "audit_event": "company.archived",
                    "workspace_id": str(workspace_id),
                    "company_id": str(company.id),
                    "actor_id": actor_id,
                },
            )
            return company

    async def restore_company(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: str | None = None,
    ) -> CompanyProfile:
        """Restore an archived company profile back to published status."""
        async with transactional(self.session):
            company = await self.repo.get_by_id(workspace_id, company_id)
            if not company:
                raise ValueError("COMPANY_NOT_FOUND")

            if company.status == "merged":
                raise ValueError("CANNOT_RESTORE_MERGED_COMPANY")

            company.status = "published"
            company.version += 1

            logger.info(
                "Audit Event: company.restored",
                extra={
                    "audit_event": "company.restored",
                    "workspace_id": str(workspace_id),
                    "company_id": str(company.id),
                    "actor_id": actor_id,
                },
            )
            return company
