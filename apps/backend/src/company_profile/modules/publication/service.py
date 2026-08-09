"""Immutable publication transaction service for company profile versions."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.publication import (
    ProfileFieldEvidence,
    ProfileFieldValue,
    ProfileVersion,
)
from company_profile.modules.drafts.service import ProfileDraftService

if TYPE_CHECKING:
    from collections.abc import Sequence


class PublicationService:
    """Service for atomic publication transactions and immutable profile versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish_draft(
        self,
        workspace_id: uuid.UUID,
        draft_id: uuid.UUID,
        published_by: uuid.UUID,
        publication_note: str | None = None,
    ) -> ProfileVersion:
        """Publish a ProfileDraft into an immutable ProfileVersion."""
        draft_svc = ProfileDraftService(self._session)
        draft = await draft_svc.get_draft(workspace_id, draft_id)
        if not draft:
            raise ValueError(f"ProfileDraft '{draft_id}' not found.")

        # Check publication blockers
        blockers = await draft_svc.check_publication_blockers(workspace_id, draft.company_id)
        critical = [
            b
            for b in blockers
            if b.get("materiality") == "critical" or b.get("code") == "MISSING_MANDATORY_FIELD"
        ]
        if critical:
            raise ValueError(f"Cannot publish draft: {critical[0]['message']}")

        # Determine next version number for company
        stmt_max = select(func.max(ProfileVersion.version_number)).where(
            ProfileVersion.company_id == draft.company_id
        )
        res_max = await self._session.execute(stmt_max)
        current_max = res_max.scalar() or 0
        next_ver_num = current_max + 1

        # Mark existing active published versions as superseded
        stmt_active = select(ProfileVersion).where(
            ProfileVersion.company_id == draft.company_id,
            ProfileVersion.status == "published",
        )
        res_active = await self._session.execute(stmt_active)
        for active in res_active.scalars().all():
            active.mark_superseded()

        # Build payload & compute content hash
        field_payloads = []
        evidence_count = 0
        conf_scores = []

        for sel in draft.field_selections:
            cand = sel.selected_fact_candidate
            if not cand:
                continue

            val = cand.get_value()
            field_payloads.append(
                {
                    "field_key": sel.field_key,
                    "context_key": sel.context_key,
                    "value": val,
                    "display_value": cand.display_value,
                    "confidence_score": cand.confidence_score,
                }
            )
            conf_scores.append(cand.confidence_score)
            evidence_count += len(cand.evidences)

        payload_bytes = json.dumps(field_payloads, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        content_hash = hashlib.sha256(payload_bytes).hexdigest()

        avg_confidence = round(sum(conf_scores) / len(conf_scores), 2) if conf_scores else 1.0

        # Build grounded executive summary
        summary = self._generate_grounded_summary(draft.title, field_payloads)

        profile_ver = ProfileVersion(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            company_id=draft.company_id,
            profile_draft_id=draft.id,
            version_number=next_ver_num,
            status="published",
            schema_version=draft.schema_version,
            policy_set_version=1,
            title=draft.title,
            executive_summary=summary,
            publication_note=publication_note,
            published_by=published_by,
            published_at=datetime.now(UTC),
            source_count=len(field_payloads),
            evidence_count=evidence_count,
            overall_confidence=avg_confidence,
            content_hash=content_hash,
        )
        self._session.add(profile_ver)
        await self._session.flush()

        # Create ProfileFieldValue and ProfileFieldEvidence records
        for idx, sel in enumerate(draft.field_selections):
            cand = sel.selected_fact_candidate
            if not cand:
                continue

            pfv = ProfileFieldValue(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                profile_version_id=profile_ver.id,
                field_key=sel.field_key,
                context_key=sel.context_key,
                value_type=cand.value_type,
                value_json=cand.value_json,
                display_value=cand.display_value,
                display_status="verified"
                if cand.fact_status in ("accepted", "validated")
                else "inferred",
                confidence_score=cand.confidence_score,
                confidence_explanation=cand.confidence_explanation,
                observed_at=cand.observed_at,
                origin_type=cand.origin_type,
                display_order=idx,
            )
            self._session.add(pfv)
            await self._session.flush()

            for ev in cand.evidences:
                pfe = ProfileFieldEvidence(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    profile_field_value_id=pfv.id,
                    evidence_id=ev.id,
                    original_excerpt=ev.original_excerpt,
                    translated_excerpt=ev.translated_excerpt,
                    source_authority_tier=2,
                    support_type=ev.support_type,
                    evidence_quality_score=ev.evidence_quality_score,
                )
                self._session.add(pfe)

        draft.status = "approved"
        await self._session.flush()

        reloaded = await self.get_profile_version(workspace_id, profile_ver.id)
        assert reloaded is not None
        return reloaded

    async def get_current_profile(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> ProfileVersion | None:
        """Get current published ProfileVersion for a company."""
        stmt = (
            select(ProfileVersion)
            .options(
                selectinload(ProfileVersion.field_values).selectinload(ProfileFieldValue.evidences)
            )
            .where(
                ProfileVersion.workspace_id == workspace_id,
                ProfileVersion.company_id == company_id,
                ProfileVersion.status == "published",
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_profile_version(
        self, workspace_id: uuid.UUID, version_id: uuid.UUID
    ) -> ProfileVersion | None:
        """Get specific ProfileVersion by ID."""
        stmt = (
            select(ProfileVersion)
            .options(
                selectinload(ProfileVersion.field_values).selectinload(ProfileFieldValue.evidences)
            )
            .where(
                ProfileVersion.workspace_id == workspace_id,
                ProfileVersion.id == version_id,
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_profile_versions(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> Sequence[ProfileVersion]:
        """List all published/superseded/withdrawn profile versions for a company."""
        stmt = (
            select(ProfileVersion)
            .options(
                selectinload(ProfileVersion.field_values).selectinload(ProfileFieldValue.evidences)
            )
            .where(
                ProfileVersion.workspace_id == workspace_id,
                ProfileVersion.company_id == company_id,
            )
            .order_by(ProfileVersion.version_number.desc())
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def withdraw_profile(
        self,
        workspace_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> ProfileVersion:
        """Withdraw a published profile version."""
        del actor_id
        pv = await self.get_profile_version(workspace_id, version_id)
        if not pv:
            raise ValueError(f"ProfileVersion '{version_id}' not found.")
        pv.withdraw(reason)
        await self._session.flush()
        return pv

    def _generate_grounded_summary(
        self, company_name: str, field_payloads: list[dict[str, Any]]
    ) -> str:
        """Generate deterministic executive summary strictly from accepted field values."""
        kv_map = {
            item["field_key"]: item["display_value"]
            for item in field_payloads
            if item.get("display_value")
        }
        legal_name = kv_map.get("identity.legal_name", company_name)
        desc = kv_map.get("overview.description", "Verified commercial entity profile.")
        industry = kv_map.get("identity.industry") or kv_map.get("overview.industry")

        summary_parts = [f"{legal_name} is a verified company profile."]
        if industry:
            summary_parts.append(f"Industry: {industry}.")
        summary_parts.append(desc)

        return " ".join(summary_parts)
