"""FastAPI router for company fact candidates, evidence, confidence, and conflict management."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError
from company_profile.db.session import get_db_session
from company_profile.modules.conflicts.engine import ConflictEngine
from company_profile.modules.facts.repository import FactCandidateRepository

router = APIRouter(prefix="/companies", tags=["facts", "conflicts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EvidenceResponse(BaseModel):
    id: str
    source_snapshot_id: str
    document_block_id: str
    original_excerpt: str
    translated_excerpt: str | None = None
    support_type: str
    evidence_quality_score: float
    review_status: str

    model_config = {"from_attributes": True}


class FactCandidateResponse(BaseModel):
    id: str
    workspace_id: str
    company_id: str
    field_key: str
    context_key: str
    value: Any
    display_value: str | None = None
    fact_status: str
    origin_type: str
    is_inferred: bool
    is_estimated: bool
    is_unknown: bool
    confidence_score: float
    confidence_explanation: str | None = None
    observed_at: str
    freshness_status: str
    evidences: list[EvidenceResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConflictCandidateResponse(BaseModel):
    id: str
    fact_candidate_id: str
    candidate_role: str
    is_selected: bool
    fact_candidate: FactCandidateResponse | None = None

    model_config = {"from_attributes": True}


class ConflictResponse(BaseModel):
    id: str
    workspace_id: str
    company_id: str
    field_key: str
    context_key: str
    status: str
    materiality: str
    resolution_type: str | None = None
    resolution_reason: str | None = None
    resolved_at: str | None = None
    candidates: list[ConflictCandidateResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ResolveConflictRequest(BaseModel):
    resolution_type: str = Field(
        ..., description="'select_one' | 'accepted_multiple' | 'dismissed'"
    )
    reason: str = Field(..., description="Explanation for resolution decision")
    selected_candidate_ids: list[str] = Field(
        default_factory=list, description="Candidate IDs selected for acceptance"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{company_id}/facts",
    response_model=list[FactCandidateResponse],
    summary="List fact candidates for a company",
)
async def list_company_facts(
    company_id: uuid.UUID,
    field_key: str | None = Query(None, description="Optional field key filter"),
    fact_status: str | None = Query(None, description="Optional status filter"),
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List fact candidates and evidence links for a company."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    repo = FactCandidateRepository(session)
    candidates = await repo.list_candidates(
        workspace_id=actor.active_workspace.id,
        company_id=company_id,
        field_key=field_key,
        fact_status=fact_status,
    )

    out = []
    for c in candidates:
        ev_list = [
            {
                "id": str(e.id),
                "source_snapshot_id": str(e.source_snapshot_id),
                "document_block_id": str(e.document_block_id),
                "original_excerpt": e.original_excerpt,
                "translated_excerpt": e.translated_excerpt,
                "support_type": e.support_type,
                "evidence_quality_score": e.evidence_quality_score,
                "review_status": e.review_status,
            }
            for e in c.evidences
        ]
        out.append(
            {
                "id": str(c.id),
                "workspace_id": str(c.workspace_id),
                "company_id": str(c.company_id),
                "field_key": c.field_key,
                "context_key": c.context_key,
                "value": c.get_value(),
                "display_value": c.display_value,
                "fact_status": c.fact_status,
                "origin_type": c.origin_type,
                "is_inferred": c.is_inferred,
                "is_estimated": c.is_estimated,
                "is_unknown": c.is_unknown,
                "confidence_score": c.confidence_score,
                "confidence_explanation": c.confidence_explanation,
                "observed_at": c.observed_at.isoformat(),
                "freshness_status": c.freshness_status,
                "evidences": ev_list,
            }
        )
    return out


@router.get(
    "/{company_id}/conflicts",
    response_model=list[ConflictResponse],
    summary="List conflicts for a company",
)
async def list_company_conflicts(
    company_id: uuid.UUID,
    conflict_status: str | None = Query(None, alias="status", description="Optional status filter"),
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List material conflicts and competing candidates for a company."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    engine = ConflictEngine(session)
    conflicts = await engine.list_conflicts(
        workspace_id=actor.active_workspace.id,
        company_id=company_id,
        status=conflict_status,
    )

    out = []
    for conf in conflicts:
        cand_list = []
        for cc in conf.candidates:
            fc = cc.fact_candidate
            fc_dict = None
            if fc is not None:
                fc_dict = {
                    "id": str(fc.id),
                    "workspace_id": str(fc.workspace_id),
                    "company_id": str(fc.company_id),
                    "field_key": fc.field_key,
                    "context_key": fc.context_key,
                    "value": fc.get_value(),
                    "display_value": fc.display_value,
                    "fact_status": fc.fact_status,
                    "origin_type": fc.origin_type,
                    "is_inferred": fc.is_inferred,
                    "is_estimated": fc.is_estimated,
                    "is_unknown": fc.is_unknown,
                    "confidence_score": fc.confidence_score,
                    "confidence_explanation": fc.confidence_explanation,
                    "observed_at": fc.observed_at.isoformat(),
                    "freshness_status": fc.freshness_status,
                    "evidences": [],
                }
            cand_list.append(
                {
                    "id": str(cc.id),
                    "fact_candidate_id": str(cc.fact_candidate_id),
                    "candidate_role": cc.candidate_role,
                    "is_selected": cc.is_selected,
                    "fact_candidate": fc_dict,
                }
            )

        out.append(
            {
                "id": str(conf.id),
                "workspace_id": str(conf.workspace_id),
                "company_id": str(conf.company_id),
                "field_key": conf.field_key,
                "context_key": conf.context_key,
                "status": conf.status,
                "materiality": conf.materiality,
                "resolution_type": conf.resolution_type,
                "resolution_reason": conf.resolution_reason,
                "resolved_at": conf.resolved_at.isoformat() if conf.resolved_at else None,
                "candidates": cand_list,
            }
        )
    return out


@router.post(
    "/{company_id}/conflicts/{conflict_id}/resolve",
    response_model=ConflictResponse,
    summary="Resolve a conflict",
)
async def resolve_conflict(
    company_id: uuid.UUID,
    conflict_id: uuid.UUID,
    body: ResolveConflictRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Resolve a conflict with resolution type, reason, and selected candidates."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    engine = ConflictEngine(session)
    try:
        selected_uuids = [uuid.UUID(cid) for cid in body.selected_candidate_ids]
        conf = await engine.resolve_conflict(
            workspace_id=actor.active_workspace.id,
            conflict_id=conflict_id,
            resolution_type=body.resolution_type,
            reason=body.reason,
            selected_candidate_ids=selected_uuids,
            resolved_by=actor.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "id": str(conf.id),
        "workspace_id": str(conf.workspace_id),
        "company_id": str(conf.company_id),
        "field_key": conf.field_key,
        "context_key": conf.context_key,
        "status": conf.status,
        "materiality": conf.materiality,
        "resolution_type": conf.resolution_type,
        "resolution_reason": conf.resolution_reason,
        "resolved_at": conf.resolved_at.isoformat() if conf.resolved_at else None,
        "candidates": [],
    }
