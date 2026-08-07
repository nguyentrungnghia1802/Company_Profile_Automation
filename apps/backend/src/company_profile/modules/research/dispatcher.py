"""TaskDispatcher protocol and PostgreSQL implementation for research pipeline step execution."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.research import ResearchJob, ResearchTask
from company_profile.db.transaction import transactional

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("company_profile.research.dispatcher")


@runtime_checkable
class TaskDispatcher(Protocol):
    """Abstract task dispatcher protocol."""

    async def create_research_job(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        job_type: str = "initial",
        scope: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ResearchJob: ...

    async def advance_job_pipeline(self, job_id: uuid.UUID) -> ResearchJob: ...


class PostgresTaskDispatcher:
    """PostgreSQL-backed task dispatcher managing step dependencies and job state transitions."""

    STEP_SEQUENCE: ClassVar[list[str]] = ["search", "fetch", "extract", "synthesize"]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_research_job(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        job_type: str = "initial",
        scope: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ResearchJob:
        """Create a research job and enqueue the initial 'search' step task."""
        scope_json = json.dumps(scope or {})

        async with transactional(self.session):
            job = ResearchJob(
                workspace_id=workspace_id,
                company_id=company_id,
                job_type=job_type,
                scope=scope_json,
                status="running",
                idempotency_key=idempotency_key,
                requested_by=requested_by,
            )
            self.session.add(job)
            await self.session.flush()

            # Enqueue initial task step ('search')
            initial_task = ResearchTask(
                workspace_id=workspace_id,
                research_job_id=job.id,
                step_type="search",
                status="pending",
                input_payload=scope_json,
            )
            self.session.add(initial_task)
            await self.session.flush()

            logger.info(
                "Created research job and initial task step",
                extra={
                    "job_id": str(job.id),
                    "company_id": str(company_id),
                    "step_type": "search",
                },
            )
            return job

    async def advance_job_pipeline(self, job_id: uuid.UUID) -> ResearchJob:
        """Evaluate task step completion and enqueue the next step or complete the job."""
        async with transactional(self.session):
            stmt = select(ResearchJob).where(ResearchJob.id == job_id).with_for_update()
            result = await self.session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                raise ValueError(f"Research job '{job_id}' not found.")

            if job.status not in ("pending", "running"):
                return job

            # Fetch tasks for this job
            t_stmt = (
                select(ResearchTask)
                .where(ResearchTask.research_job_id == job.id)
                .order_by(ResearchTask.created_at.asc())
            )
            t_result = await self.session.execute(t_stmt)
            tasks: Sequence[ResearchTask] = t_result.scalars().all()

            # Check for failed or cancelled tasks
            if any(t.status == "failed" for t in tasks):
                failed_task = next(t for t in tasks if t.status == "failed")
                job.fail(failed_task.error_message or "Task step failed.")
                return job

            if any(t.status == "cancelled" for t in tasks) or job.cancel_requested_at is not None:
                job.status = "cancelled"
                return job

            completed_types = {t.step_type for t in tasks if t.status == "completed"}

            # Determine next step in sequence
            for step in self.STEP_SEQUENCE:
                if step not in completed_types:
                    # If step is not yet enqueued, enqueue it now
                    if not any(t.step_type == step for t in tasks):
                        prev_output = next(
                            (t.output_payload for t in reversed(tasks) if t.status == "completed"),
                            None,
                        )
                        next_task = ResearchTask(
                            workspace_id=job.workspace_id,
                            research_job_id=job.id,
                            step_type=step,
                            status="pending",
                            input_payload=prev_output,
                        )
                        self.session.add(next_task)
                        await self.session.flush()
                        logger.info(
                            "Advanced pipeline to next step",
                            extra={"job_id": str(job.id), "next_step": step},
                        )
                    return job

            # All steps in sequence completed -> complete job
            job.complete()
            logger.info(
                "All pipeline steps completed. Job marked complete", extra={"job_id": str(job.id)}
            )
            return job
