"""Review task management and decision audit logging service."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.review import ReviewDecision, ReviewTask

if TYPE_CHECKING:
    from collections.abc import Sequence


class ReviewTaskService:
    """Service for handling review task lifecycles, optimistic locking, and decision logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        task_type: str,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        research_job_id: uuid.UUID | None = None,
        conflict_id: uuid.UUID | None = None,
        fact_candidate_id: uuid.UUID | None = None,
        due_at: datetime | None = None,
    ) -> ReviewTask:
        """Create a new ReviewTask."""
        task = ReviewTask(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            company_id=company_id,
            research_job_id=research_job_id,
            conflict_id=conflict_id,
            fact_candidate_id=fact_candidate_id,
            task_type=task_type,
            status="open",
            priority=priority,
            title=title,
            description=description,
            due_at=due_at,
        )
        self._session.add(task)
        await self._session.flush()
        return task

    async def list_tasks(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
        status: str | None = None,
        task_type: str | None = None,
        assigned_to: uuid.UUID | None = None,
    ) -> Sequence[ReviewTask]:
        """List review tasks in workspace with optional filters."""
        stmt = (
            select(ReviewTask)
            .options(selectinload(ReviewTask.decisions))
            .where(ReviewTask.workspace_id == workspace_id)
        )
        if company_id:
            stmt = stmt.where(ReviewTask.company_id == company_id)
        if status:
            stmt = stmt.where(ReviewTask.status == status)
        if task_type:
            stmt = stmt.where(ReviewTask.task_type == task_type)
        if assigned_to:
            stmt = stmt.where(ReviewTask.assigned_to == assigned_to)
        stmt = stmt.order_by(ReviewTask.created_at.desc())
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def get_task(self, workspace_id: uuid.UUID, task_id: uuid.UUID) -> ReviewTask | None:
        """Get single review task by ID."""
        stmt = (
            select(ReviewTask)
            .options(selectinload(ReviewTask.decisions))
            .where(
                ReviewTask.workspace_id == workspace_id,
                ReviewTask.id == task_id,
            )
            .execution_options(populate_existing=True)
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def claim_task(
        self, workspace_id: uuid.UUID, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> ReviewTask:
        """Claim open review task."""
        task = await self.get_task(workspace_id, task_id)
        if not task:
            raise ValueError(f"ReviewTask '{task_id}' not found.")
        prev_state = task.status
        task.claim(user_id)
        self._record_decision(
            workspace_id=workspace_id,
            review_task_id=task.id,
            actor_id=user_id,
            action="claim",
            target_type="review_task",
            target_id=str(task.id),
            previous_state={"status": prev_state},
            new_state={"status": task.status, "assigned_to": str(user_id)},
            reason="Claimed by reviewer",
        )
        await self._session.flush()
        return task

    async def release_task(
        self, workspace_id: uuid.UUID, task_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ReviewTask:
        """Release claimed task back to unassigned pool."""
        task = await self.get_task(workspace_id, task_id)
        if not task:
            raise ValueError(f"ReviewTask '{task_id}' not found.")
        prev_state = task.status
        task.release()
        self._record_decision(
            workspace_id=workspace_id,
            review_task_id=task.id,
            actor_id=actor_id,
            action="release",
            target_type="review_task",
            target_id=str(task.id),
            previous_state={"status": prev_state},
            new_state={"status": task.status},
            reason="Released by reviewer",
        )
        await self._session.flush()
        return task

    async def complete_task(
        self,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        actor_id: uuid.UUID,
        decision_code: str,
        reason: str,
        expected_row_version: int | None = None,
    ) -> ReviewTask:
        """Complete task with decision code, rationale, and optimistic locking check."""
        task = await self.get_task(workspace_id, task_id)
        if not task:
            raise ValueError(f"ReviewTask '{task_id}' not found.")
        if expected_row_version is not None and task.row_version != expected_row_version:
            raise ValueError(
                "Row version conflict: task version is "
                f"{task.row_version}, expected {expected_row_version}"
            )
        prev_state = task.status
        task.complete(decision_code, reason)
        self._record_decision(
            workspace_id=workspace_id,
            review_task_id=task.id,
            actor_id=actor_id,
            action="complete",
            target_type="review_task",
            target_id=str(task.id),
            previous_state={"status": prev_state},
            new_state={"status": task.status, "decision_code": decision_code},
            reason=reason,
        )
        await self._session.flush()
        return task

    async def reopen_task(
        self,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> ReviewTask:
        """Reopen a completed review task."""
        task = await self.get_task(workspace_id, task_id)
        if not task:
            raise ValueError(f"ReviewTask '{task_id}' not found.")
        prev_state = task.status
        task.reopen(reason)
        self._record_decision(
            workspace_id=workspace_id,
            review_task_id=task.id,
            actor_id=actor_id,
            action="reopen",
            target_type="review_task",
            target_id=str(task.id),
            previous_state={"status": prev_state},
            new_state={"status": task.status},
            reason=reason,
        )
        await self._session.flush()
        return task

    def _record_decision(
        self,
        workspace_id: uuid.UUID,
        review_task_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: str,
        previous_state: dict[str, Any] | None,
        new_state: dict[str, Any] | None,
        reason: str,
    ) -> None:
        """Record append-only decision audit entry."""
        dec = ReviewDecision(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            review_task_id=review_task_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            previous_state_json=json.dumps(previous_state) if previous_state else None,
            new_state_json=json.dumps(new_state) if new_state else None,
            reason=reason,
        )
        self._session.add(dec)
