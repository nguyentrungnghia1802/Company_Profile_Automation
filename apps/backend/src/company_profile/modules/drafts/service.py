"""Draft profile assembly, field selection overrides, and publication blocker evaluation service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.conflict import Conflict
from company_profile.db.models.draft import DraftFieldSelection, ProfileDraft
from company_profile.db.models.fact import FactCandidate
from company_profile.modules.review.service import ReviewTaskService

if TYPE_CHECKING:
    from collections.abc import Sequence


class ProfileDraftService:
    """Service for managing draft profile assembly, field selections, and publication blockers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assemble_draft(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        research_job_id: uuid.UUID | None = None,
        title: str = "Draft Profile",
        notes: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> ProfileDraft:
        """Assemble a new ProfileDraft from currently accepted and recommended fact candidates."""
        # Supersede existing active building drafts for this company
        stmt_old = select(ProfileDraft).where(
            ProfileDraft.workspace_id == workspace_id,
            ProfileDraft.company_id == company_id,
            ProfileDraft.status.in_(["building", "ready_for_review"]),
        )
        res_old = await self._session.execute(stmt_old)
        for old in res_old.scalars().all():
            old.status = "superseded"

        draft = ProfileDraft(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            company_id=company_id,
            research_job_id=research_job_id,
            status="building",
            schema_version=1,
            title=title,
            notes=notes,
            created_by=created_by,
        )
        self._session.add(draft)
        await self._session.flush()

        # Fetch candidates for company
        stmt_cand = (
            select(FactCandidate)
            .where(
                FactCandidate.workspace_id == workspace_id,
                FactCandidate.company_id == company_id,
                FactCandidate.fact_status.in_(["accepted", "recommended", "validated", "candidate"]),
            )
            .order_by(FactCandidate.confidence_score.desc())
        )
        res_cand = await self._session.execute(stmt_cand)
        candidates = res_cand.scalars().all()

        # Pick highest confidence candidate per field_key
        best_candidates: dict[str, FactCandidate] = {}
        for c in candidates:
            if c.field_key not in best_candidates:
                best_candidates[c.field_key] = c

        order = 0
        for field_key, c in best_candidates.items():
            sel = DraftFieldSelection(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                profile_draft_id=draft.id,
                field_key=field_key,
                context_key=c.context_key,
                selected_fact_candidate_id=c.id,
                selection_state="accepted" if c.fact_status in ("accepted", "recommended") else "overridden",
                display_order=order,
            )
            self._session.add(sel)
            order += 1

        await self._session.flush()

        # Reload with field_selections and evidences
        stmt_reload = (
            select(ProfileDraft)
            .options(
                selectinload(ProfileDraft.field_selections)
                .selectinload(DraftFieldSelection.selected_fact_candidate)
                .selectinload(FactCandidate.evidences)
            )
            .where(ProfileDraft.id == draft.id)
        )
        res_reload = await self._session.execute(stmt_reload)
        return res_reload.scalar_one()

    async def list_drafts(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> Sequence[ProfileDraft]:
        """List drafts for a company."""
        stmt = (
            select(ProfileDraft)
            .options(
                selectinload(ProfileDraft.field_selections)
                .selectinload(DraftFieldSelection.selected_fact_candidate)
                .selectinload(FactCandidate.evidences)
            )
            .where(
                ProfileDraft.workspace_id == workspace_id,
                ProfileDraft.company_id == company_id,
            )
            .order_by(ProfileDraft.created_at.desc())
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def get_draft(
        self, workspace_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ProfileDraft | None:
        """Get ProfileDraft by ID."""
        stmt = (
            select(ProfileDraft)
            .options(
                selectinload(ProfileDraft.field_selections)
                .selectinload(DraftFieldSelection.selected_fact_candidate)
                .selectinload(FactCandidate.evidences)
            )
            .where(
                ProfileDraft.workspace_id == workspace_id,
                ProfileDraft.id == draft_id,
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_field_selection(
        self,
        workspace_id: uuid.UUID,
        draft_id: uuid.UUID,
        field_key: str,
        candidate_id: uuid.UUID | None,
        note: str | None = None,
        selection_state: str = "overridden",
    ) -> ProfileDraft:
        """Override selected candidate for a specific field key in a draft."""
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise ValueError(f"ProfileDraft '{draft_id}' not found.")

        target_sel = next((s for s in draft.field_selections if s.field_key == field_key), None)
        if target_sel:
            target_sel.selected_fact_candidate_id = candidate_id
            target_sel.selection_state = selection_state
            if note:
                target_sel.reviewer_note = note
        else:
            sel = DraftFieldSelection(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                profile_draft_id=draft.id,
                field_key=field_key,
                selected_fact_candidate_id=candidate_id,
                selection_state=selection_state,
                reviewer_note=note,
                display_order=len(draft.field_selections),
            )
            self._session.add(sel)

        draft.row_version = (draft.row_version or 1) + 1
        await self._session.flush()

        reloaded = await self.get_draft(workspace_id, draft_id)
        assert reloaded is not None
        return reloaded

    async def check_publication_blockers(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Check for mandatory publication blockers (open conflicts, missing identity fields)."""
        blockers = []

        # 1. Unresolved material conflicts
        stmt_conf = select(Conflict).where(
            Conflict.workspace_id == workspace_id,
            Conflict.company_id == company_id,
            Conflict.status.in_(["open", "reopened", "needs_research"]),
        )
        res_conf = await self._session.execute(stmt_conf)
        open_conflicts = res_conf.scalars().all()

        for conf in open_conflicts:
            blockers.append(
                {
                    "code": "UNRESOLVED_CONFLICT",
                    "materiality": conf.materiality,
                    "field_key": conf.field_key,
                    "message": f"Field '{conf.field_key}' has open material conflict ({conf.status}).",
                }
            )

        # 2. Mandatory identity fields check
        stmt_cand = select(FactCandidate.field_key).where(
            FactCandidate.workspace_id == workspace_id,
            FactCandidate.company_id == company_id,
            FactCandidate.fact_status.in_(["accepted", "recommended", "validated"]),
        )
        res_cand = await self._session.execute(stmt_cand)
        existing_fields = set(res_cand.scalars().all())

        mandatory_fields = ["identity.legal_name"]
        for mf in mandatory_fields:
            if mf not in existing_fields:
                blockers.append(
                    {
                        "code": "MISSING_MANDATORY_FIELD",
                        "field_key": mf,
                        "message": f"Mandatory field '{mf}' has no accepted/validated candidate.",
                    }
                )

        return blockers

    async def request_review(
        self, workspace_id: uuid.UUID, draft_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProfileDraft:
        """Mark draft ready for review and create publication review task."""
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise ValueError(f"ProfileDraft '{draft_id}' not found.")

        blockers = await self.check_publication_blockers(workspace_id, draft.company_id)
        critical_blockers = [b for b in blockers if b.get("materiality") == "critical" or b.get("code") == "MISSING_MANDATORY_FIELD"]
        if critical_blockers:
            raise ValueError(f"Cannot request review: {critical_blockers[0]['message']}")

        draft.status = "ready_for_review"
        draft.row_version = (draft.row_version or 1) + 1

        review_svc = ReviewTaskService(self._session)
        await review_svc.create_task(
            workspace_id=workspace_id,
            company_id=draft.company_id,
            task_type="publication_approval",
            title=f"Publication Review: {draft.title}",
            description=f"Review draft profile '{draft.id}' for publication.",
            priority="high",
            research_job_id=draft.research_job_id,
        )
        await self._session.flush()

        reloaded = await self.get_draft(workspace_id, draft_id)
        assert reloaded is not None
        return reloaded
