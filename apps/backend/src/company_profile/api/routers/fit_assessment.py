"""API router for Program Fit Assessment management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import get_db_session
from company_profile.modules.audit.service import AuditService
from company_profile.modules.fit_assessment.service import ProgramFitAssessmentService

router = APIRouter()


class EvaluateFitRequest(BaseModel):
    """Request payload to evaluate company program fit."""

    program_name: str = "AI Riser Innovation Accelerator 2026"


class OverrideFitRequest(BaseModel):
    """Request payload to apply human reviewer override."""

    override_status: str
    notes: str | None = None


class FitAssessmentResponse(BaseModel):
    """Program fit assessment response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: uuid.UUID
    program_name: str
    overall_fit_status: str
    fit_score: float
    assessment_json: dict[str, Any]
    reviewer_override_status: str | None = None
    reviewer_notes: str | None = None
    reviewed_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


@router.get("/companies/{company_id}/fit-assessments", response_model=list[FitAssessmentResponse])
async def list_fit_assessments(
    company_id: uuid.UUID,
    x_workspace_id: uuid.UUID = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
) -> list[FitAssessmentResponse]:
    """List program fit assessments for a company profile."""
    svc = ProgramFitAssessmentService(db)
    assessments = await svc.list_assessments(x_workspace_id, company_id)
    return [FitAssessmentResponse.model_validate(a) for a in assessments]


@router.post(
    "/companies/{company_id}/fit-assessments",
    response_model=FitAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_program_fit(
    company_id: uuid.UUID,
    payload: EvaluateFitRequest,
    x_workspace_id: uuid.UUID = Header(..., alias="X-Workspace-ID"),
    x_actor_id: uuid.UUID | None = Header(None, alias="X-Actor-ID"),
    db: AsyncSession = Depends(get_db_session),
) -> FitAssessmentResponse:
    """Evaluate company program fit against innovation program criteria."""
    try:
        svc = ProgramFitAssessmentService(db)
        assessment = await svc.evaluate_program_fit(
            workspace_id=x_workspace_id,
            company_id=company_id,
            program_name=payload.program_name,
        )

        audit_svc = AuditService(db)
        await audit_svc.log_event(
            workspace_id=x_workspace_id,
            actor_id=x_actor_id,
            actor_type="user" if x_actor_id else "system",
            action="fit_assessment.evaluated",
            resource_type="program_fit_assessment",
            resource_id=str(assessment.id),
            metadata={"program_name": payload.program_name, "status": assessment.overall_fit_status},
        )

        await db.commit()
        return FitAssessmentResponse.model_validate(assessment)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/fit-assessments/{assessment_id}/override", response_model=FitAssessmentResponse)
async def override_fit_assessment(
    assessment_id: uuid.UUID,
    payload: OverrideFitRequest,
    x_workspace_id: uuid.UUID = Header(..., alias="X-Workspace-ID"),
    x_actor_id: uuid.UUID = Header(..., alias="X-Actor-ID"),
    db: AsyncSession = Depends(get_db_session),
) -> FitAssessmentResponse:
    """Apply human reviewer decision override on a program fit assessment."""
    try:
        svc = ProgramFitAssessmentService(db)
        assessment = await svc.apply_reviewer_override(
            workspace_id=x_workspace_id,
            assessment_id=assessment_id,
            user_id=x_actor_id,
            override_status=payload.override_status,
            notes=payload.notes,
        )

        audit_svc = AuditService(db)
        await audit_svc.log_event(
            workspace_id=x_workspace_id,
            actor_id=x_actor_id,
            actor_type="user",
            action="fit_assessment.overridden",
            resource_type="program_fit_assessment",
            resource_id=str(assessment.id),
            metadata={"override_status": payload.override_status, "notes": payload.notes},
        )

        await db.commit()
        return FitAssessmentResponse.model_validate(assessment)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
