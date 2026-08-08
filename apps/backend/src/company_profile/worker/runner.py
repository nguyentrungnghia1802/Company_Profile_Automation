"""Worker pool background runner with cancellation handling and graceful shutdown."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING

from company_profile.db.session import get_db_session
from company_profile.modules.research.dispatcher import PostgresTaskDispatcher
from company_profile.modules.research.pipeline import ResearchPipelineExecutor
from company_profile.modules.research.queue import ResearchQueueRepository

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.db.models.research import ResearchTask

logger = logging.getLogger("company_profile.worker.runner")


class WorkerRunner:
    """Async background worker running research tasks queue loop."""

    def __init__(
        self,
        worker_id: str = "worker-1",
        poll_interval: float = 2.0,
        batch_size: int = 5,
        lease_seconds: int = 300,
        session_factory: Callable[[], AsyncSession] | None = None,
        pipeline_factory: Callable[[AsyncSession], ResearchPipelineExecutor] | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self.session_factory = session_factory
        self.pipeline_factory = pipeline_factory
        self._running = False
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start worker polling loop."""
        self._running = True
        logger.info("Worker runner started", extra={"worker_id": self.worker_id})

        while self._running and not self._stop_event.is_set():
            try:
                await self.tick()
            except Exception as exc:
                logger.error("Error in worker tick: %s", exc, exc_info=True)

            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)

        logger.info("Worker runner stopped gracefully", extra={"worker_id": self.worker_id})

    def stop(self) -> None:
        """Signal worker to stop processing."""
        self._running = False
        self._stop_event.set()

    async def tick(self) -> int:
        """Run a single polling tick to claim and process tasks."""
        if self.session_factory is not None:
            session = self.session_factory()
            repo = ResearchQueueRepository(session)
            await repo.recover_stale_locks()
            claimed = await repo.claim_due_tasks(
                worker_id=self.worker_id,
                batch_size=self.batch_size,
                lease_seconds=self.lease_seconds,
            )
            for task in claimed:
                await self.execute_task(session, task)
            return len(claimed)

        async for session in get_db_session():
            repo = ResearchQueueRepository(session)
            await repo.recover_stale_locks()
            claimed = await repo.claim_due_tasks(
                worker_id=self.worker_id,
                batch_size=self.batch_size,
                lease_seconds=self.lease_seconds,
            )
            for task in claimed:
                await self.execute_task(session, task)
            return len(claimed)
        return 0

    async def execute_task(
        self,
        session: AsyncSession,
        task: ResearchTask,
    ) -> None:
        """Execute a single task step."""
        logger.info(
            "Executing task step",
            extra={
                "task_id": str(task.id),
                "step_type": task.step_type,
                "worker_id": self.worker_id,
            },
        )
        try:
            pipeline = (
                self.pipeline_factory(session)
                if self.pipeline_factory is not None
                else ResearchPipelineExecutor(session)
            )
            output_payload = await pipeline.execute(task)
            task.complete(json.dumps(output_payload, ensure_ascii=False, sort_keys=True))
            await session.commit()

            # Advance job pipeline step sequence
            dispatcher = PostgresTaskDispatcher(session)
            await dispatcher.advance_job_pipeline(task.research_job_id)
        except Exception as exc:
            logger.error("Task execution failed: %s", exc, exc_info=True)
            task.fail(str(exc))
            await session.commit()
            dispatcher = PostgresTaskDispatcher(session)
            await dispatcher.advance_job_pipeline(task.research_job_id)
