"""FastAPI router for research job execution, status retrieval, and cancellation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from company_profile.db.session import get_db_session
from company_profile.modules.research.service import ResearchJobService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from company_profile.db.models.research import ResearchJob

router = APIRouter()


class ResearchTaskResponse(BaseModel):
    """Research task step response model."""

    id: uuid.UUID
    step_type: str
    status: str
    attempt_count: int
    max_attempts: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_payload: str | None = None
    error_message: str | None = None


class ResearchJobResponseData(BaseModel):
    """Research job detail response model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: uuid.UUID
    job_type: str
    requested_locale: str
    status: str
    priority: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    error_message: str | None = None
    tasks: list[ResearchTaskResponse] = []


class ResearchJobDetailResponse(BaseModel):
    """Research job detail envelope."""

    success: bool = True
    data: ResearchJobResponseData


class ResearchJobListResponse(BaseModel):
    """Research job list envelope."""

    success: bool = True
    data: list[ResearchJobResponseData]


class TriggerResearchRequest(BaseModel):
    """Trigger research job request body."""

    job_type: str = "initial"
    scope: dict[str, Any] | None = None
    requested_locale: str = "vi"


def verify_active_workspace(actor: RequestActor) -> uuid.UUID:
    """Ensure current request actor has an active workspace selected."""
    if not actor.active_workspace:
        raise ForbiddenError(
            code="NO_ACTIVE_WORKSPACE",
            message="No active workspace selected for request.",
        )
    return actor.active_workspace.id


@router.post("/companies/{company_id}/research", response_model=ResearchJobDetailResponse)
async def trigger_company_research(
    company_id: uuid.UUID,
    payload: TriggerResearchRequest,
    actor: RequestActor = Depends(require_capability("research:start")),
    session: AsyncSession = Depends(get_db_session),
) -> ResearchJobDetailResponse:
    """Trigger an automated research job for a company profile."""
    workspace_id = verify_active_workspace(actor)
    service = ResearchJobService(session)

    try:
        job = await service.start_research_job(
            workspace_id=workspace_id,
            company_id=company_id,
            job_type=payload.job_type,
            scope=payload.scope,
            requested_by=actor.user_id,
        )
    except ValueError as err:
        if str(err) == "COMPANY_NOT_FOUND":
            raise NotFoundError(
                code="COMPANY_NOT_FOUND",
                message="Company profile not found in the active workspace.",
            ) from err
        raise
    full_job = await service.get_job(workspace_id, job.id)
    if not full_job:
        raise NotFoundError(code="JOB_NOT_FOUND", message="Failed to retrieve created job.")

    return ResearchJobDetailResponse(
        success=True,
        data=ResearchJobResponseData(
            id=full_job.id,
            workspace_id=full_job.workspace_id,
            company_id=full_job.company_id,
            job_type=full_job.job_type,
            requested_locale=full_job.requested_locale,
            status=full_job.status,
            priority=full_job.priority,
            started_at=full_job.started_at,
            completed_at=full_job.completed_at,
            cancel_requested_at=full_job.cancel_requested_at,
            error_message=full_job.error_message,
            tasks=[
                ResearchTaskResponse(
                    id=t.id,
                    step_type=t.step_type,
                    status=t.status,
                    attempt_count=t.attempt_count,
                    max_attempts=t.max_attempts,
                    started_at=t.started_at,
                    completed_at=t.completed_at,
                    output_payload=t.output_payload,
                    error_message=t.error_message,
                )
                for t in full_job.tasks
            ],
        ),
    )


@router.get("/research-jobs", response_model=ResearchJobListResponse)
async def list_research_jobs(
    company_id: uuid.UUID | None = None,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> ResearchJobListResponse:
    """List research jobs in active workspace."""
    workspace_id = verify_active_workspace(actor)
    service = ResearchJobService(session)

    jobs: Sequence[ResearchJob] = await service.list_jobs(workspace_id, company_id=company_id)
    return ResearchJobListResponse(
        success=True,
        data=[
            ResearchJobResponseData(
                id=j.id,
                workspace_id=j.workspace_id,
                company_id=j.company_id,
                job_type=j.job_type,
                requested_locale=j.requested_locale,
                status=j.status,
                priority=j.priority,
                started_at=j.started_at,
                completed_at=j.completed_at,
                cancel_requested_at=j.cancel_requested_at,
                error_message=j.error_message,
            )
            for j in jobs
        ],
    )


@router.get("/research-jobs/{job_id}", response_model=ResearchJobDetailResponse)
async def get_research_job(
    job_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> ResearchJobDetailResponse:
    """Get research job details and task step status."""
    workspace_id = verify_active_workspace(actor)
    service = ResearchJobService(session)

    job = await service.get_job(workspace_id, job_id)
    if not job:
        raise NotFoundError(code="JOB_NOT_FOUND", message="Research job not found.")

    return ResearchJobDetailResponse(
        success=True,
        data=ResearchJobResponseData(
            id=job.id,
            workspace_id=job.workspace_id,
            company_id=job.company_id,
            job_type=job.job_type,
            requested_locale=job.requested_locale,
            status=job.status,
            priority=job.priority,
            started_at=job.started_at,
            completed_at=job.completed_at,
            cancel_requested_at=job.cancel_requested_at,
            error_message=job.error_message,
            tasks=[
                ResearchTaskResponse(
                    id=t.id,
                    step_type=t.step_type,
                    status=t.status,
                    attempt_count=t.attempt_count,
                    max_attempts=t.max_attempts,
                    started_at=t.started_at,
                    completed_at=t.completed_at,
                    output_payload=t.output_payload,
                    error_message=t.error_message,
                )
                for t in job.tasks
            ],
        ),
    )


@router.post("/research-jobs/{job_id}/cancel", response_model=ResearchJobDetailResponse)
async def cancel_research_job(
    job_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("research:start")),
    session: AsyncSession = Depends(get_db_session),
) -> ResearchJobDetailResponse:
    """Cancel a running research job."""
    workspace_id = verify_active_workspace(actor)
    service = ResearchJobService(session)

    try:
        job = await service.cancel_job(workspace_id, job_id)
    except ValueError as err:
        raise ValidationError(code="CANCEL_FAILED", message=str(err)) from err

    return ResearchJobDetailResponse(
        success=True,
        data=ResearchJobResponseData(
            id=job.id,
            workspace_id=job.workspace_id,
            company_id=job.company_id,
            job_type=job.job_type,
            requested_locale=job.requested_locale,
            status=job.status,
            priority=job.priority,
            started_at=job.started_at,
            completed_at=job.completed_at,
            cancel_requested_at=job.cancel_requested_at,
            error_message=job.error_message,
            tasks=[
                ResearchTaskResponse(
                    id=t.id,
                    step_type=t.step_type,
                    status=t.status,
                    attempt_count=t.attempt_count,
                    max_attempts=t.max_attempts,
                    started_at=t.started_at,
                    completed_at=t.completed_at,
                    output_payload=t.output_payload,
                    error_message=t.error_message,
                )
                for t in job.tasks
            ],
        ),
    )


class LiveScrapeRequest(BaseModel):
    """Deprecated synchronous scraper request retained for an explicit error response."""

    query: str
    website_url: str | None = None


@router.post("/research/live-scrape")
async def live_scrape_company(
    payload: LiveScrapeRequest,
    actor: RequestActor = Depends(require_capability("research:start")),
) -> dict[str, Any]:
    """Reject the old synchronous path instead of returning unverified snippets."""
    verify_active_workspace(actor)
    raise AppError(
        code="LIVE_SCRAPE_RETIRED",
        message=(
            "Synchronous live scraping is retired because search snippets are not evidence. "
            "Create a research job so sources, snapshots, and evidence are persisted."
        ),
        status_code=410,
        details={
            "query_received": bool(payload.query.strip()),
            "website_url_received": bool(payload.website_url and payload.website_url.strip()),
            "next_action": "POST /api/v1/companies/{company_id}/research",
            "ai_required": False,
            "name_only_requirement": (
                "Configure SEARCH_PROVIDER=google with SEARCH_API_KEY and "
                "SEARCH_ENGINE_ID, or provide an official website URL."
            ),
        },
    )
