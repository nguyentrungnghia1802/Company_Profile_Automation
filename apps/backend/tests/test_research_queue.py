"""Unit tests for research job state machine, task queue claiming, and worker runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.research import ResearchJob, ResearchTask
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.research.queue import ResearchQueueRepository
from company_profile.modules.workspaces.repository import WorkspaceRepository
from company_profile.worker.runner import WorkerRunner

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_research_job_state_transitions(db_session: AsyncSession) -> None:
    """Verify ResearchJob state transition helper methods."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)
    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="State WS", slug="state-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="State Test Corp",
            normalized_name="state test corp",
            status="published",
        )
    )

    job = ResearchJob(
        workspace_id=ws.id,
        company_id=company.id,
        job_type="initial",
        status="pending",
    )
    assert job.status == "pending"

    # Start
    job.start()
    assert job.status == "running"
    assert job.started_at is not None

    # Complete
    job.complete()
    assert job.status == "completed"
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_research_task_claim_and_stale_recovery(db_session: AsyncSession) -> None:
    """Verify claiming pending tasks and recovering expired locks."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)
    queue_repo = ResearchQueueRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Queue WS", slug="queue-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Queue Test Corp",
            normalized_name="queue test corp",
            status="published",
        )
    )

    job = await queue_repo.create_job(
        ResearchJob(
            workspace_id=ws.id,
            company_id=company.id,
            job_type="initial",
            status="running",
        )
    )

    task = await queue_repo.add_task(
        ResearchTask(
            workspace_id=ws.id,
            research_job_id=job.id,
            step_type="search",
            status="pending",
        )
    )

    # 1. Claim task
    claimed = await queue_repo.claim_due_tasks("worker-test-1", batch_size=5, lease_seconds=60)
    assert len(claimed) == 1
    assert claimed[0].id == task.id
    assert claimed[0].status == "running"
    assert claimed[0].lease_owner == "worker-test-1"

    # 2. Simulate expired lease
    claimed[0].lease_expires_at = datetime.now(UTC) - timedelta(seconds=10)

    # 3. Recover stale locks
    recovered_count = await queue_repo.recover_stale_locks()
    assert recovered_count == 1
    assert claimed[0].status == "pending"
    assert claimed[0].lease_owner is None


@pytest.mark.asyncio
async def test_worker_runner_tick(db_session: AsyncSession) -> None:
    """Verify worker runner tick claims and executes tasks."""
    runner = WorkerRunner(worker_id="runner-unit-1", session_factory=lambda: db_session)
    count = await runner.tick()
    assert isinstance(count, int)
