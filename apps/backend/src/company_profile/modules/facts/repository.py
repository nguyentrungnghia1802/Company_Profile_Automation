"""Repository for FactCandidate and Evidence data access and transactional operations."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.fact import Evidence, FactCandidate


class FactCandidateRepository:
    """Workspace-scoped repository for managing fact candidates and evidence links."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_candidate(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        field_key: str,
        value: Any,
        origin_type: str = "ai",
        context_key: str = "",
        value_type: str = "string",
        research_job_id: uuid.UUID | None = None,
        is_inferred: bool = False,
        is_estimated: bool = False,
        is_unknown: bool = False,
        confidence_score: float = 0.0,
        confidence_components: dict[str, Any] | None = None,
        confidence_explanation: str | None = None,
        observed_at: datetime | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        freshness_status: str = "fresh",
        created_by: uuid.UUID | None = None,
    ) -> FactCandidate:
        """Create a new FactCandidate.

        Handles duplicate prevention by checking if an identical candidate value
        already exists for the same workspace/company/field_key/context_key/origin_type.
        """
        value_json_str = json.dumps(value, ensure_ascii=False) if value is not None else None

        # Duplicate check: check if exact same value exists in candidate/validated state
        stmt = select(FactCandidate).where(
            FactCandidate.workspace_id == workspace_id,
            FactCandidate.company_id == company_id,
            FactCandidate.field_key == field_key,
            FactCandidate.context_key == context_key,
            FactCandidate.origin_type == origin_type,
            FactCandidate.value_json == value_json_str,
            FactCandidate.fact_status.in_(["candidate", "validated", "recommended", "accepted"]),
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        display_val = (
            str(value)
            if value is not None and not isinstance(value, (dict, list))
            else (json.dumps(value, ensure_ascii=False) if value is not None else None)
        )
        conf_comp_str = (
            json.dumps(confidence_components, ensure_ascii=False) if confidence_components else None
        )

        candidate = FactCandidate(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            company_id=company_id,
            research_job_id=research_job_id,
            field_key=field_key,
            context_key=context_key,
            value_type=value_type,
            value_json=value_json_str,
            normalized_value_json=value_json_str,
            display_value=display_val,
            fact_status="candidate",
            origin_type=origin_type,
            is_inferred=is_inferred,
            is_estimated=is_estimated,
            is_unknown=is_unknown,
            confidence_score=confidence_score,
            confidence_components=conf_comp_str,
            confidence_explanation=confidence_explanation,
            observed_at=observed_at or datetime.now(UTC),
            valid_from=valid_from,
            valid_to=valid_to,
            freshness_status=freshness_status,
            created_by=created_by,
        )
        self._session.add(candidate)
        await self._session.flush()
        return candidate

    async def add_evidence(
        self,
        workspace_id: uuid.UUID,
        fact_candidate_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        document_block_id: uuid.UUID,
        original_excerpt: str,
        translated_excerpt: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        support_type: str = "direct",
        evidence_quality_score: float = 1.0,
        extraction_method: str = "ai",
    ) -> Evidence:
        """Add an Evidence record linking a FactCandidate to a DocumentBlock.

        Enforces duplicate prevention by returning existing Evidence if identical
        link already exists.
        """
        stmt = select(Evidence).where(
            Evidence.fact_candidate_id == fact_candidate_id,
            Evidence.source_snapshot_id == source_snapshot_id,
            Evidence.document_block_id == document_block_id,
        )
        res = await self._session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing is not None:
            return existing

        ev = Evidence(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            fact_candidate_id=fact_candidate_id,
            source_snapshot_id=source_snapshot_id,
            document_block_id=document_block_id,
            original_excerpt=original_excerpt,
            translated_excerpt=translated_excerpt,
            start_offset=start_offset,
            end_offset=end_offset,
            support_type=support_type,
            evidence_quality_score=evidence_quality_score,
            extraction_method=extraction_method,
            review_status="pending",
        )
        self._session.add(ev)
        await self._session.flush()
        return ev

    async def get_by_id(
        self, workspace_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> FactCandidate | None:
        """Get FactCandidate by ID within workspace scope."""
        stmt = (
            select(FactCandidate)
            .options(selectinload(FactCandidate.evidences))
            .where(
                FactCandidate.workspace_id == workspace_id,
                FactCandidate.id == candidate_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_candidates(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        field_key: str | None = None,
        fact_status: str | None = None,
    ) -> Sequence[FactCandidate]:
        """List FactCandidates for a company filtered by field_key and status."""
        stmt = (
            select(FactCandidate)
            .options(selectinload(FactCandidate.evidences))
            .where(
                FactCandidate.workspace_id == workspace_id,
                FactCandidate.company_id == company_id,
            )
        )
        if field_key is not None:
            stmt = stmt.where(FactCandidate.field_key == field_key)
        if fact_status is not None:
            stmt = stmt.where(FactCandidate.fact_status == fact_status)
        stmt = stmt.order_by(FactCandidate.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()
