"""FastAPI router for profile drafts, draft field selection overrides, and immutable version publication."""

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
from company_profile.modules.drafts.service import ProfileDraftService
from company_profile.modules.publication.service import PublicationService

router = APIRouter(tags=["profiles"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DraftFieldSelectionResponse(BaseModel):
    id: str
    field_key: str
    context_key: str
    selected_fact_candidate_id: str | None = None
    selection_state: str
    reviewer_note: str | None = None
    display_order: int

    model_config = {"from_attributes": True}


class ProfileDraftResponse(BaseModel):
    id: str
    workspace_id: str
    company_id: str
    research_job_id: str | None = None
    status: str
    schema_version: int
    title: str
    summary_draft: str | None = None
    notes: str | None = None
    row_version: int
    created_at: str
    field_selections: list[DraftFieldSelectionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UpdateDraftSelectionRequest(BaseModel):
    field_key: str = Field(..., description="Target field key")
    selected_candidate_id: str | None = Field(None, description="Chosen candidate ID")
    selection_state: str = Field("overridden", description="'accepted' | 'overridden' | 'rejected' | 'unknown'")
    note: str | None = Field(None, description="Reviewer selection rationale")


class PublishDraftRequest(BaseModel):
    publication_note: str | None = Field(None, description="Optional release notes for publication")


class WithdrawProfileRequest(BaseModel):
    reason: str = Field(..., description="Mandatory reason for profile withdrawal")


class ProfileFieldEvidenceResponse(BaseModel):
    id: str
    original_excerpt: str
    translated_excerpt: str | None = None
    source_canonical_url: str | None = None
    source_authority_tier: int
    support_type: str
    evidence_quality_score: float

    model_config = {"from_attributes": True}


class ProfileFieldValueResponse(BaseModel):
    id: str
    field_key: str
    context_key: str
    value: Any
    display_value: str | None = None
    display_status: str
    confidence_score: float
    confidence_explanation: str | None = None
    observed_at: str | None = None
    origin_type: str
    display_order: int
    evidences: list[ProfileFieldEvidenceResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProfileVersionResponse(BaseModel):
    id: str
    workspace_id: str
    company_id: str
    profile_draft_id: str | None = None
    version_number: int
    status: str
    title: str
    executive_summary: str
    publication_note: str | None = None
    published_by: str | None = None
    published_at: str
    superseded_at: str | None = None
    withdrawn_at: str | None = None
    withdrawal_reason: str | None = None
    source_count: int
    evidence_count: int
    overall_confidence: float
    content_hash: str
    field_values: list[ProfileFieldValueResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Draft Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/companies/{company_id}/profile-drafts",
    response_model=list[ProfileDraftResponse],
    summary="List profile drafts for a company",
)
async def list_company_profile_drafts(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List drafts for a company."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ProfileDraftService(session)
    drafts = await svc.list_drafts(actor.active_workspace.id, company_id)

    out = []
    for d in drafts:
        sel_list = [
            {
                "id": str(s.id),
                "field_key": s.field_key,
                "context_key": s.context_key,
                "selected_fact_candidate_id": str(s.selected_fact_candidate_id) if s.selected_fact_candidate_id else None,
                "selection_state": s.selection_state,
                "reviewer_note": s.reviewer_note,
                "display_order": s.display_order,
            }
            for s in d.field_selections
        ]
        out.append(
            {
                "id": str(d.id),
                "workspace_id": str(d.workspace_id),
                "company_id": str(d.company_id),
                "research_job_id": str(d.research_job_id) if d.research_job_id else None,
                "status": d.status,
                "schema_version": d.schema_version,
                "title": d.title,
                "summary_draft": d.summary_draft,
                "notes": d.notes,
                "row_version": d.row_version,
                "created_at": d.created_at.isoformat(),
                "field_selections": sel_list,
            }
        )
    return out


@router.post(
    "/companies/{company_id}/profile-drafts",
    response_model=ProfileDraftResponse,
    summary="Assemble a new profile draft",
)
async def assemble_company_profile_draft(
    company_id: uuid.UUID,
    title: str = Query("Draft Profile", description="Draft title"),
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Assemble draft from candidates."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ProfileDraftService(session)
    d = await svc.assemble_draft(
        workspace_id=actor.active_workspace.id,
        company_id=company_id,
        title=title,
        created_by=actor.user_id,
    )

    sel_list = [
        {
            "id": str(s.id),
            "field_key": s.field_key,
            "context_key": s.context_key,
            "selected_fact_candidate_id": str(s.selected_fact_candidate_id) if s.selected_fact_candidate_id else None,
            "selection_state": s.selection_state,
            "reviewer_note": s.reviewer_note,
            "display_order": s.display_order,
        }
        for s in d.field_selections
    ]
    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "company_id": str(d.company_id),
        "research_job_id": str(d.research_job_id) if d.research_job_id else None,
        "status": d.status,
        "schema_version": d.schema_version,
        "title": d.title,
        "summary_draft": d.summary_draft,
        "notes": d.notes,
        "row_version": d.row_version,
        "created_at": d.created_at.isoformat(),
        "field_selections": sel_list,
    }


@router.get(
    "/profile-drafts/{draft_id}",
    response_model=ProfileDraftResponse,
    summary="Get profile draft detail",
)
async def get_profile_draft(
    draft_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get single profile draft."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ProfileDraftService(session)
    d = await svc.get_draft(actor.active_workspace.id, draft_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile draft not found.")

    sel_list = [
        {
            "id": str(s.id),
            "field_key": s.field_key,
            "context_key": s.context_key,
            "selected_fact_candidate_id": str(s.selected_fact_candidate_id) if s.selected_fact_candidate_id else None,
            "selection_state": s.selection_state,
            "reviewer_note": s.reviewer_note,
            "display_order": s.display_order,
        }
        for s in d.field_selections
    ]
    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "company_id": str(d.company_id),
        "status": d.status,
        "schema_version": d.schema_version,
        "title": d.title,
        "summary_draft": d.summary_draft,
        "notes": d.notes,
        "row_version": d.row_version,
        "created_at": d.created_at.isoformat(),
        "field_selections": sel_list,
    }


@router.patch(
    "/profile-drafts/{draft_id}",
    response_model=ProfileDraftResponse,
    summary="Update draft field selection",
)
async def update_profile_draft_selection(
    draft_id: uuid.UUID,
    body: UpdateDraftSelectionRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update field candidate selection in draft."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    cand_uuid = uuid.UUID(body.selected_candidate_id) if body.selected_candidate_id else None
    svc = ProfileDraftService(session)
    try:
        d = await svc.update_field_selection(
            workspace_id=actor.active_workspace.id,
            draft_id=draft_id,
            field_key=body.field_key,
            candidate_id=cand_uuid,
            note=body.note,
            selection_state=body.selection_state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sel_list = [
        {
            "id": str(s.id),
            "field_key": s.field_key,
            "context_key": s.context_key,
            "selected_fact_candidate_id": str(s.selected_fact_candidate_id) if s.selected_fact_candidate_id else None,
            "selection_state": s.selection_state,
            "reviewer_note": s.reviewer_note,
            "display_order": s.display_order,
        }
        for s in d.field_selections
    ]
    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "company_id": str(d.company_id),
        "status": d.status,
        "schema_version": d.schema_version,
        "title": d.title,
        "row_version": d.row_version,
        "created_at": d.created_at.isoformat(),
        "field_selections": sel_list,
    }


@router.post(
    "/profile-drafts/{draft_id}/request-review",
    response_model=ProfileDraftResponse,
    summary="Request review for profile draft",
)
async def request_profile_draft_review(
    draft_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark draft ready for review and create task."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ProfileDraftService(session)
    try:
        d = await svc.request_review(actor.active_workspace.id, draft_id, actor.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "company_id": str(d.company_id),
        "status": d.status,
        "title": d.title,
        "row_version": d.row_version,
        "created_at": d.created_at.isoformat(),
        "field_selections": [],
    }


@router.post(
    "/profile-drafts/{draft_id}/publish",
    response_model=ProfileVersionResponse,
    summary="Publish draft into immutable profile version",
)
async def publish_profile_draft(
    draft_id: uuid.UUID,
    body: PublishDraftRequest,
    actor: RequestActor = Depends(require_capability("profile:publish")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Publish draft into an immutable ProfileVersion."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    try:
        pv = await pub_svc.publish_draft(
            workspace_id=actor.active_workspace.id,
            draft_id=draft_id,
            published_by=actor.user_id,
            publication_note=body.publication_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    fv_list = []
    for fv in pv.field_values:
        ev_list = [
            {
                "id": str(e.id),
                "original_excerpt": e.original_excerpt,
                "translated_excerpt": e.translated_excerpt,
                "source_canonical_url": e.source_canonical_url,
                "source_authority_tier": e.source_authority_tier,
                "support_type": e.support_type,
                "evidence_quality_score": e.evidence_quality_score,
            }
            for e in fv.evidences
        ]
        fv_list.append(
            {
                "id": str(fv.id),
                "field_key": fv.field_key,
                "context_key": fv.context_key,
                "value": fv.get_value(),
                "display_value": fv.display_value,
                "display_status": fv.display_status,
                "confidence_score": fv.confidence_score,
                "confidence_explanation": fv.confidence_explanation,
                "observed_at": fv.observed_at.isoformat() if fv.observed_at else None,
                "origin_type": fv.origin_type,
                "display_order": fv.display_order,
                "evidences": ev_list,
            }
        )

    return {
        "id": str(pv.id),
        "workspace_id": str(pv.workspace_id),
        "company_id": str(pv.company_id),
        "profile_draft_id": str(pv.profile_draft_id) if pv.profile_draft_id else None,
        "version_number": pv.version_number,
        "status": pv.status,
        "title": pv.title,
        "executive_summary": pv.executive_summary,
        "publication_note": pv.publication_note,
        "published_by": str(pv.published_by) if pv.published_by else None,
        "published_at": pv.published_at.isoformat(),
        "superseded_at": pv.superseded_at.isoformat() if pv.superseded_at else None,
        "withdrawn_at": pv.withdrawn_at.isoformat() if pv.withdrawn_at else None,
        "withdrawal_reason": pv.withdrawal_reason,
        "source_count": pv.source_count,
        "evidence_count": pv.evidence_count,
        "overall_confidence": pv.overall_confidence,
        "content_hash": pv.content_hash,
        "field_values": fv_list,
    }


# ---------------------------------------------------------------------------
# Published Profile Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/companies/{company_id}/profiles",
    response_model=list[ProfileVersionResponse],
    summary="List published profile versions for a company",
)
async def list_company_profile_versions(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List all profile versions for a company."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    versions = await pub_svc.list_profile_versions(actor.active_workspace.id, company_id)

    out = []
    for pv in versions:
        out.append(
            {
                "id": str(pv.id),
                "workspace_id": str(pv.workspace_id),
                "company_id": str(pv.company_id),
                "version_number": pv.version_number,
                "status": pv.status,
                "title": pv.title,
                "executive_summary": pv.executive_summary,
                "published_at": pv.published_at.isoformat(),
                "source_count": pv.source_count,
                "evidence_count": pv.evidence_count,
                "overall_confidence": pv.overall_confidence,
                "content_hash": pv.content_hash,
                "field_values": [],
            }
        )
    return out


@router.get(
    "/companies/{company_id}/profile",
    response_model=ProfileVersionResponse,
    summary="Get current published profile for a company",
)
async def get_current_company_profile(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get current active published profile version."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    pv = await pub_svc.get_current_profile(actor.active_workspace.id, company_id)
    if not pv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active published profile version found.")

    fv_list = []
    for fv in pv.field_values:
        ev_list = [
            {
                "id": str(e.id),
                "original_excerpt": e.original_excerpt,
                "translated_excerpt": e.translated_excerpt,
                "source_canonical_url": e.source_canonical_url,
                "source_authority_tier": e.source_authority_tier,
                "support_type": e.support_type,
                "evidence_quality_score": e.evidence_quality_score,
            }
            for e in fv.evidences
        ]
        fv_list.append(
            {
                "id": str(fv.id),
                "field_key": fv.field_key,
                "context_key": fv.context_key,
                "value": fv.get_value(),
                "display_value": fv.display_value,
                "display_status": fv.display_status,
                "confidence_score": fv.confidence_score,
                "confidence_explanation": fv.confidence_explanation,
                "observed_at": fv.observed_at.isoformat() if fv.observed_at else None,
                "origin_type": fv.origin_type,
                "display_order": fv.display_order,
                "evidences": ev_list,
            }
        )

    return {
        "id": str(pv.id),
        "workspace_id": str(pv.workspace_id),
        "company_id": str(pv.company_id),
        "version_number": pv.version_number,
        "status": pv.status,
        "title": pv.title,
        "executive_summary": pv.executive_summary,
        "publication_note": pv.publication_note,
        "published_by": str(pv.published_by) if pv.published_by else None,
        "published_at": pv.published_at.isoformat(),
        "source_count": pv.source_count,
        "evidence_count": pv.evidence_count,
        "overall_confidence": pv.overall_confidence,
        "content_hash": pv.content_hash,
        "field_values": fv_list,
    }


@router.get(
    "/profiles/{version_id}",
    response_model=ProfileVersionResponse,
    summary="Get specific published profile version detail",
)
async def get_profile_version_detail(
    version_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get single profile version by ID."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    pv = await pub_svc.get_profile_version(actor.active_workspace.id, version_id)
    if not pv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile version not found.")

    fv_list = []
    for fv in pv.field_values:
        ev_list = [
            {
                "id": str(e.id),
                "original_excerpt": e.original_excerpt,
                "translated_excerpt": e.translated_excerpt,
                "source_canonical_url": e.source_canonical_url,
                "source_authority_tier": e.source_authority_tier,
                "support_type": e.support_type,
                "evidence_quality_score": e.evidence_quality_score,
            }
            for e in fv.evidences
        ]
        fv_list.append(
            {
                "id": str(fv.id),
                "field_key": fv.field_key,
                "context_key": fv.context_key,
                "value": fv.get_value(),
                "display_value": fv.display_value,
                "display_status": fv.display_status,
                "confidence_score": fv.confidence_score,
                "confidence_explanation": fv.confidence_explanation,
                "observed_at": fv.observed_at.isoformat() if fv.observed_at else None,
                "origin_type": fv.origin_type,
                "display_order": fv.display_order,
                "evidences": ev_list,
            }
        )

    return {
        "id": str(pv.id),
        "workspace_id": str(pv.workspace_id),
        "company_id": str(pv.company_id),
        "version_number": pv.version_number,
        "status": pv.status,
        "title": pv.title,
        "executive_summary": pv.executive_summary,
        "published_at": pv.published_at.isoformat(),
        "superseded_at": pv.superseded_at.isoformat() if pv.superseded_at else None,
        "withdrawn_at": pv.withdrawn_at.isoformat() if pv.withdrawn_at else None,
        "withdrawal_reason": pv.withdrawal_reason,
        "source_count": pv.source_count,
        "evidence_count": pv.evidence_count,
        "overall_confidence": pv.overall_confidence,
        "content_hash": pv.content_hash,
        "field_values": fv_list,
    }


@router.post(
    "/profiles/{version_id}/withdraw",
    response_model=ProfileVersionResponse,
    summary="Withdraw published profile version",
)
async def withdraw_published_profile(
    version_id: uuid.UUID,
    body: WithdrawProfileRequest,
    actor: RequestActor = Depends(require_capability("profile:publish")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Withdraw a published profile version."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    try:
        pv = await pub_svc.withdraw_profile(actor.active_workspace.id, version_id, actor.user_id, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "id": str(pv.id),
        "workspace_id": str(pv.workspace_id),
        "company_id": str(pv.company_id),
        "version_number": pv.version_number,
        "status": pv.status,
        "title": pv.title,
        "executive_summary": pv.executive_summary,
        "published_at": pv.published_at.isoformat(),
        "withdrawn_at": pv.withdrawn_at.isoformat() if pv.withdrawn_at else None,
        "withdrawal_reason": pv.withdrawal_reason,
        "source_count": pv.source_count,
        "evidence_count": pv.evidence_count,
        "overall_confidence": pv.overall_confidence,
        "content_hash": pv.content_hash,
        "field_values": [],
    }
