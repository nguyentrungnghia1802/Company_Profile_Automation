"""Task queue dispatcher supporting claim leasing and stale lock recovery."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.research import ResearchJob, ResearchTask
from company_profile.db.transaction import transactional

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("company_profile.research.queue")


class ResearchQueueRepository:
    """Queue manager for claiming due research tasks and handling lease expirations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(self, job: ResearchJob) -> ResearchJob:
        """Create a new research job."""
        async with transactional(self.session):
            self.session.add(job)
            await self.session.flush()
            return job

    async def add_task(self, task: ResearchTask) -> ResearchTask:
        """Add a task step to a research job."""
        async with transactional(self.session):
            self.session.add(task)
            await self.session.flush()
            return task

    async def claim_due_tasks(
        self,
        worker_id: str,
        batch_size: int = 5,
        lease_seconds: int = 300,
    ) -> list[ResearchTask]:
        """Claim due or expired tasks for worker execution."""
        now = datetime.now(UTC)
        async with transactional(self.session):
            # Select pending tasks or running tasks with expired leases
            stmt = (
                select(ResearchTask)
                .where(
                    or_(
                        ResearchTask.status == "pending",
                        ResearchTask.status == "queued",
                        (
                            (ResearchTask.status == "running")
                            & (ResearchTask.lease_expires_at < now)
                        ),
                    )
                )
                .where(
                    or_(
                        ResearchTask.next_attempt_at.is_(None),
                        ResearchTask.next_attempt_at <= now,
                    )
                )
                .order_by(ResearchTask.created_at.asc())
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )

            result = await self.session.execute(stmt)
            tasks: list[ResearchTask] = list(result.scalars().all())

            claimed: list[ResearchTask] = []
            for task in tasks:
                task.claim(worker_id, lease_seconds=lease_seconds)
                claimed.append(task)

            return claimed

    async def recover_stale_locks(self) -> int:
        """Find running tasks with expired leases and release them back to pending state."""
        now = datetime.now(UTC)
        async with transactional(self.session):
            stmt = select(ResearchTask).where(
                ResearchTask.status == "running",
                ResearchTask.lease_expires_at < now,
            )
            result = await self.session.execute(stmt)
            stale_tasks: Sequence[ResearchTask] = result.scalars().all()

            recovered_count = 0
            for task in stale_tasks:
                task.release()
                recovered_count += 1
                logger.warning(
                    "Recovered stale task lock",
                    extra={
                        "task_id": str(task.id),
                        "job_id": str(task.research_job_id),
                        "previous_lease_owner": task.lease_owner,
                    },
                )
            return recovered_count
