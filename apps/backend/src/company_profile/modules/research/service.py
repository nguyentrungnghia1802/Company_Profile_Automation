"""Application service for research jobs management and status tracking."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.research import ResearchJob, ResearchTask
from company_profile.db.transaction import transactional
from company_profile.modules.research.dispatcher import PostgresTaskDispatcher

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("company_profile.research.service")


class ResearchJobService:
    """Service for research job orchestration, progress retrieval, and cancellation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.dispatcher = PostgresTaskDispatcher(session)

    async def start_research_job(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        job_type: str = "initial",
        scope: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ResearchJob:
        """Start a new research job for a company profile."""
        return await self.dispatcher.create_research_job(
            workspace_id=workspace_id,
            company_id=company_id,
            job_type=job_type,
            scope=scope,
            requested_by=requested_by,
            idempotency_key=idempotency_key,
        )

    async def get_job(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ResearchJob | None:
        """Get research job by ID with tasks eager loaded."""
        stmt = (
            select(ResearchJob)
            .where(
                ResearchJob.id == job_id,
                ResearchJob.workspace_id == workspace_id,
            )
            .options(selectinload(ResearchJob.tasks))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> Sequence[ResearchJob]:
        """List research jobs in workspace, optionally filtered by company."""
        stmt = (
            select(ResearchJob)
            .where(ResearchJob.workspace_id == workspace_id)
            .order_by(ResearchJob.created_at.desc())
        )
        if company_id:
            stmt = stmt.where(ResearchJob.company_id == company_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def cancel_job(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ResearchJob:
        """Request cancellation of a running research job."""
        async with transactional(self.session):
            job = await self.get_job(workspace_id, job_id)
            if not job:
                raise ValueError(f"Research job '{job_id}' not found.")

            job.request_cancel()

            # Also cancel any pending/running tasks
            t_stmt = select(ResearchTask).where(ResearchTask.research_job_id == job.id)
            t_result = await self.session.execute(t_stmt)
            tasks: Sequence[ResearchTask] = t_result.scalars().all()
            for t in tasks:
                if t.status in ("pending", "queued", "running"):
                    t.status = "cancelled"

            logger.info("Cancelled research job", extra={"job_id": str(job.id)})
            return job
