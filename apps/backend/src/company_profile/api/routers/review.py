"""FastAPI router for human review tasks, inbox management, and decision tracking."""

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
from company_profile.modules.review.service import ReviewTaskService

router = APIRouter(prefix="/review-tasks", tags=["review-tasks"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReviewDecisionResponse(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str
    previous_state_json: str | None = None
    new_state_json: str | None = None
    reason: str
    created_at: str

    model_config = {"from_attributes": True}


class ReviewTaskResponse(BaseModel):
    id: str
    workspace_id: str
    company_id: str
    research_job_id: str | None = None
    conflict_id: str | None = None
    fact_candidate_id: str | None = None
    task_type: str
    status: str
    priority: str
    title: str
    description: str | None = None
    assigned_to: str | None = None
    claimed_at: str | None = None
    due_at: str | None = None
    decision_code: str | None = None
    decision_reason: str | None = None
    row_version: int
    created_at: str
    completed_at: str | None = None
    decisions: list[ReviewDecisionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CompleteReviewTaskRequest(BaseModel):
    decision_code: str = Field(..., description="Approved / Rejected / Changes Requested decision code")
    reason: str = Field(..., description="Explanation for decision")
    expected_row_version: int | None = Field(None, description="Optimistic locking row version check")


class ReopenReviewTaskRequest(BaseModel):
    reason: str = Field(..., description="Explanation for reopening review task")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[ReviewTaskResponse],
    summary="List review tasks in inbox",
)
async def list_review_tasks(
    company_id: uuid.UUID | None = Query(None, description="Optional company ID filter"),
    task_status: str | None = Query(None, alias="status", description="Optional status filter"),
    task_type: str | None = Query(None, description="Optional task type filter"),
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List review tasks for workspace inbox."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    tasks = await svc.list_tasks(
        workspace_id=actor.active_workspace.id,
        company_id=company_id,
        status=task_status,
        task_type=task_type,
    )

    out = []
    for t in tasks:
        dec_list = [
            {
                "id": str(d.id),
                "action": d.action,
                "target_type": d.target_type,
                "target_id": d.target_id,
                "previous_state_json": d.previous_state_json,
                "new_state_json": d.new_state_json,
                "reason": d.reason,
                "created_at": d.created_at.isoformat(),
            }
            for d in t.decisions
        ]
        out.append(
            {
                "id": str(t.id),
                "workspace_id": str(t.workspace_id),
                "company_id": str(t.company_id),
                "research_job_id": str(t.research_job_id) if t.research_job_id else None,
                "conflict_id": str(t.conflict_id) if t.conflict_id else None,
                "fact_candidate_id": str(t.fact_candidate_id) if t.fact_candidate_id else None,
                "task_type": t.task_type,
                "status": t.status,
                "priority": t.priority,
                "title": t.title,
                "description": t.description,
                "assigned_to": str(t.assigned_to) if t.assigned_to else None,
                "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "decision_code": t.decision_code,
                "decision_reason": t.decision_reason,
                "row_version": t.row_version,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "decisions": dec_list,
            }
        )
    return out


@router.get(
    "/{task_id}",
    response_model=ReviewTaskResponse,
    summary="Get review task detail",
)
async def get_review_task(
    task_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get single review task details."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    t = await svc.get_task(actor.active_workspace.id, task_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review task not found.")

    dec_list = [
        {
            "id": str(d.id),
            "action": d.action,
            "target_type": d.target_type,
            "target_id": d.target_id,
            "previous_state_json": d.previous_state_json,
            "new_state_json": d.new_state_json,
            "reason": d.reason,
            "created_at": d.created_at.isoformat(),
        }
        for d in t.decisions
    ]
    return {
        "id": str(t.id),
        "workspace_id": str(t.workspace_id),
        "company_id": str(t.company_id),
        "research_job_id": str(t.research_job_id) if t.research_job_id else None,
        "conflict_id": str(t.conflict_id) if t.conflict_id else None,
        "fact_candidate_id": str(t.fact_candidate_id) if t.fact_candidate_id else None,
        "task_type": t.task_type,
        "status": t.status,
        "priority": t.priority,
        "title": t.title,
        "description": t.description,
        "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "decision_code": t.decision_code,
        "decision_reason": t.decision_reason,
        "row_version": t.row_version,
        "created_at": t.created_at.isoformat(),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "decisions": dec_list,
    }


@router.post(
    "/{task_id}/claim",
    response_model=ReviewTaskResponse,
    summary="Claim review task",
)
async def claim_review_task(
    task_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Claim open review task."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    try:
        t = await svc.claim_task(actor.active_workspace.id, task_id, actor.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "id": str(t.id),
        "workspace_id": str(t.workspace_id),
        "company_id": str(t.company_id),
        "task_type": t.task_type,
        "status": t.status,
        "priority": t.priority,
        "title": t.title,
        "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
        "row_version": t.row_version,
        "created_at": t.created_at.isoformat(),
        "decisions": [],
    }


@router.post(
    "/{task_id}/release",
    response_model=ReviewTaskResponse,
    summary="Release review task",
)
async def release_review_task(
    task_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Release claimed task."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    try:
        t = await svc.release_task(actor.active_workspace.id, task_id, actor.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "id": str(t.id),
        "workspace_id": str(t.workspace_id),
        "company_id": str(t.company_id),
        "task_type": t.task_type,
        "status": t.status,
        "priority": t.priority,
        "title": t.title,
        "assigned_to": None,
        "row_version": t.row_version,
        "created_at": t.created_at.isoformat(),
        "decisions": [],
    }


@router.post(
    "/{task_id}/complete",
    response_model=ReviewTaskResponse,
    summary="Complete review task",
)
async def complete_review_task(
    task_id: uuid.UUID,
    body: CompleteReviewTaskRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Complete review task with decision code and rationale."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    try:
        t = await svc.complete_task(
            workspace_id=actor.active_workspace.id,
            task_id=task_id,
            actor_id=actor.user_id,
            decision_code=body.decision_code,
            reason=body.reason,
            expected_row_version=body.expected_row_version,
        )
    except ValueError as exc:
        st = status.HTTP_409_CONFLICT if "version" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=st, detail=str(exc)) from exc

    return {
        "id": str(t.id),
        "workspace_id": str(t.workspace_id),
        "company_id": str(t.company_id),
        "task_type": t.task_type,
        "status": t.status,
        "priority": t.priority,
        "title": t.title,
        "decision_code": t.decision_code,
        "decision_reason": t.decision_reason,
        "row_version": t.row_version,
        "created_at": t.created_at.isoformat(),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "decisions": [],
    }


@router.post(
    "/{task_id}/reopen",
    response_model=ReviewTaskResponse,
    summary="Reopen review task",
)
async def reopen_review_task(
    task_id: uuid.UUID,
    body: ReopenReviewTaskRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reopen review task."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = ReviewTaskService(session)
    try:
        t = await svc.reopen_task(
            workspace_id=actor.active_workspace.id,
            task_id=task_id,
            actor_id=actor.user_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "id": str(t.id),
        "workspace_id": str(t.workspace_id),
        "company_id": str(t.company_id),
        "task_type": t.task_type,
        "status": t.status,
        "priority": t.priority,
        "title": t.title,
        "row_version": t.row_version,
        "created_at": t.created_at.isoformat(),
        "decisions": [],
    }
