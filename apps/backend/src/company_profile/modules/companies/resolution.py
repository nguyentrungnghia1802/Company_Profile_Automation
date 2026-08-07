"""Entity resolution and duplicate-candidate scoring service."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import select

from company_profile.db.models.company import (
    CompanyAlias,
    CompanyProfile,
    normalize_company_name,
)
from company_profile.db.transaction import transactional
from company_profile.modules.companies.repository import CompanyRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ResolutionCandidate(BaseModel):
    """Duplicate candidate match result."""

    company_id: uuid.UUID
    company_name: str
    tax_id: str | None
    registration_number: str | None
    match_score: float
    match_reason: str


class CompanyResolutionService:
    """Service handling company identity resolution, candidate scoring, and entity merging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CompanyRepository(session)

    @staticmethod
    def calculate_match_score(
        target_name: str,
        target_tax_id: str | None,
        target_reg_num: str | None,
        candidate: CompanyProfile,
    ) -> tuple[float, str]:
        """Calculate identity match score using strong and weak signals.

        Returns tuple of (score, reason).
        """
        # Strong identity signal 1: Exact Tax ID match
        if target_tax_id and candidate.tax_id and target_tax_id == candidate.tax_id:
            return 1.0, "EXACT_TAX_ID_MATCH"

        # Strong identity signal 2: Exact Registration Number match
        if (
            target_reg_num
            and candidate.registration_number
            and target_reg_num == candidate.registration_number
        ):
            return 1.0, "EXACT_REGISTRATION_NUMBER_MATCH"

        # Weak identity signal 1: Normalized name exact match
        norm_target = normalize_company_name(target_name)
        if norm_target and norm_target == candidate.normalized_name:
            return 0.85, "EXACT_NORMALIZED_NAME_MATCH"

        # Weak identity signal 2: Substring or prefix match
        if norm_target and (
            norm_target in candidate.normalized_name or candidate.normalized_name in norm_target
        ):
            return 0.65, "PARTIAL_NAME_SUBSTRING_MATCH"

        return 0.0, "NO_MATCH"

    async def find_candidates(
        self,
        workspace_id: uuid.UUID,
        company_name: str,
        tax_id: str | None = None,
        registration_number: str | None = None,
    ) -> list[ResolutionCandidate]:
        """Search workspace for potential duplicate company profile candidates."""
        candidates: list[ResolutionCandidate] = []
        visited_ids: set[uuid.UUID] = set()

        # 1. Tax ID lookup
        if tax_id:
            c_tax = await self.repo.get_by_tax_id(workspace_id, tax_id)
            if c_tax and c_tax.id not in visited_ids:
                visited_ids.add(c_tax.id)
                score, reason = self.calculate_match_score(
                    company_name, tax_id, registration_number, c_tax
                )
                candidates.append(
                    ResolutionCandidate(
                        company_id=c_tax.id,
                        company_name=c_tax.company_name,
                        tax_id=c_tax.tax_id,
                        registration_number=c_tax.registration_number,
                        match_score=score,
                        match_reason=reason,
                    )
                )

        # 2. Registration number lookup
        if registration_number:
            c_reg = await self.repo.get_by_registration_number(workspace_id, registration_number)
            if c_reg and c_reg.id not in visited_ids:
                visited_ids.add(c_reg.id)
                score, reason = self.calculate_match_score(
                    company_name, tax_id, registration_number, c_reg
                )
                candidates.append(
                    ResolutionCandidate(
                        company_id=c_reg.id,
                        company_name=c_reg.company_name,
                        tax_id=c_reg.tax_id,
                        registration_number=c_reg.registration_number,
                        match_score=score,
                        match_reason=reason,
                    )
                )

        # 3. List all company profiles for name comparison
        all_companies = await self.repo.list_by_workspace(workspace_id, limit=200)
        for c in all_companies:
            if c.id not in visited_ids and c.status != "merged":
                score, reason = self.calculate_match_score(
                    company_name, tax_id, registration_number, c
                )
                if score >= 0.5:
                    visited_ids.add(c.id)
                    candidates.append(
                        ResolutionCandidate(
                            company_id=c.id,
                            company_name=c.company_name,
                            tax_id=c.tax_id,
                            registration_number=c.registration_number,
                            match_score=score,
                            match_reason=reason,
                        )
                    )

        # Sort candidates descending by match_score
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        return candidates

    async def merge_companies(
        self,
        workspace_id: uuid.UUID,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        actor_id: str | None = None,
    ) -> CompanyProfile:
        """Merge source company into target company profile.

        - Sets source status to 'merged' and merged_into_id to target_id.
        - Preserves source primary name as a 'former_name' alias on target company.
        - Reassigns source aliases to target company.
        - Emits structured audit event 'company.merged'.
        """
        async with transactional(self.session):
            source = await self.repo.get_by_id(workspace_id, source_id)
            target = await self.repo.get_by_id(workspace_id, target_id)

            if not source or not target:
                raise ValueError("COMPANY_NOT_FOUND")

            if source.id == target.id:
                raise ValueError("CANNOT_MERGE_SAME_COMPANY")

            # 1. Update source status & reference
            source.status = "merged"
            source.merged_into_id = target.id
            source.version += 1

            # 2. Add source primary name as former_name alias on target company
            norm_former = normalize_company_name(source.company_name)
            stmt_alias_exists = select(CompanyAlias).where(
                CompanyAlias.workspace_id == workspace_id,
                CompanyAlias.normalized_alias == norm_former,
            )
            res_alias = await self.session.execute(stmt_alias_exists)
            existing_alias = res_alias.scalar_one_or_none()

            if existing_alias:
                existing_alias.company_id = target.id
                existing_alias.alias_type = "former_name"
            else:
                former_alias = CompanyAlias(
                    workspace_id=workspace_id,
                    company_id=target.id,
                    alias_name=source.company_name,
                    normalized_alias=norm_former,
                    alias_type="former_name",
                )
                self.session.add(former_alias)

            # 3. Reassign source aliases to target company
            source_aliases = await self.repo.list_aliases(workspace_id, source.id)
            for alias in source_aliases:
                alias.company_id = target.id

            target.version += 1

            logger.info(
                "Audit Event: company.merged",
                extra={
                    "audit_event": "company.merged",
                    "workspace_id": str(workspace_id),
                    "source_company_id": str(source_id),
                    "target_company_id": str(target_id),
                    "former_name": source.company_name,
                    "actor_id": actor_id,
                },
            )
            return target
