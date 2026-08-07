"""Unit and integration tests for research job dispatcher, step execution, and service lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.research.retry import calculate_backoff_delay
from company_profile.modules.research.service import ResearchJobService
from company_profile.modules.workspaces.repository import WorkspaceRepository
from company_profile.worker.runner import WorkerRunner

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def test_exponential_backoff_calculator() -> None:
    """Verify exponential backoff delay calculation values."""
    assert calculate_backoff_delay(0) == 0
    assert calculate_backoff_delay(1, base_delay=10) == 10
    assert calculate_backoff_delay(2, base_delay=10) == 20
    assert calculate_backoff_delay(3, base_delay=10) == 40
    assert calculate_backoff_delay(4, base_delay=10) == 80
    assert calculate_backoff_delay(10, base_delay=10, max_delay=600) == 600


@pytest.mark.asyncio
async def test_full_research_pipeline_execution(db_session: AsyncSession) -> None:
    """Verify end-to-end research pipeline step progression from search to completed."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)
    service = ResearchJobService(db_session)
    runner = WorkerRunner(worker_id="test-pipeline-worker", session_factory=lambda: db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Pipeline WS", slug="pipe-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Pipeline Corp",
            normalized_name="pipeline corp",
            status="published",
        )
    )

    # 1. Start job (enqueues 'search' step)
    job = await service.start_research_job(
        workspace_id=ws.id,
        company_id=company.id,
        job_type="initial",
    )
    assert job.status == "running"

    # 2. Run worker ticks to process search, fetch, extract, synthesize steps
    for _ in range(5):
        await runner.tick()

    # 3. Retrieve completed job
    completed_job = await service.get_job(ws.id, job.id)
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert len(completed_job.tasks) == 4
    step_types = [t.step_type for t in completed_job.tasks]
    assert step_types == ["search", "fetch", "extract", "synthesize"]


@pytest.mark.asyncio
async def test_research_job_cancellation(db_session: AsyncSession) -> None:
    """Verify requesting cancellation updates job and pending tasks to cancelled."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)
    service = ResearchJobService(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Cancel WS", slug="cancel-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Cancel Corp",
            normalized_name="cancel corp",
            status="published",
        )
    )

    job = await service.start_research_job(
        workspace_id=ws.id,
        company_id=company.id,
        job_type="initial",
    )

    cancelled_job = await service.cancel_job(ws.id, job.id)
    assert cancelled_job.status == "cancelled"
    assert cancelled_job.cancel_requested_at is not None
