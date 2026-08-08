"""Unit and integration tests for research job dispatcher, step execution, and service lifecycle."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from httpx import Request, Response
from sqlalchemy import select

from company_profile.config.settings import Settings
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.research import ResearchTask
from company_profile.db.models.source import DocumentBlock, SourceSnapshot
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.research.dispatcher import PostgresTaskDispatcher
from company_profile.modules.research.pipeline import ResearchPipelineExecutor
from company_profile.modules.research.retry import calculate_backoff_delay
from company_profile.modules.research.service import ResearchJobService
from company_profile.modules.sources.fetcher import WebFetcher
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
    """Verify acquisition completes and AI-disabled work is reported as partial."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)
    service = ResearchJobService(db_session)
    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Pipeline WS", slug="pipe-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Pipeline Corp",
            normalized_name="pipeline corp",
            status="published",
        )
    )

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        html = (
            b'<script type="application/ld+json">'
            b'{"@type":"Organization","legalName":"Pipeline Corp",'
            b'"url":"https://pipeline.example.com",'
            b'"address":{"streetAddress":"1 Test Street","addressCountry":"VN"}}'
            b"</script><h1>Pipeline Corp</h1>"
        )
        return Response(
            status_code=200,
            content=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=Request("GET", url),
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        settings = Settings(ai_provider="disabled", search_provider="fixture")
        runner = WorkerRunner(
            worker_id="test-pipeline-worker",
            session_factory=lambda: db_session,
            pipeline_factory=lambda session: ResearchPipelineExecutor(
                session,
                settings=settings,
                fetcher=fetcher,
                search_provider=None,
            ),
        )

        # 1. Start job with a supplied public website.
        job = await service.start_research_job(
            workspace_id=ws.id,
            company_id=company.id,
            job_type="initial",
            scope={"website_url": "https://pipeline.example.com"},
        )
        assert job.status == "running"

        # 2. Run every durable step, plus one harmless idle tick.
        for _ in range(len(PostgresTaskDispatcher.STEP_SEQUENCE) + 1):
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
            try:
                await runner.tick()
            finally:
                monkeypatch.undo()

        # 3. Acquisition artifacts survive the optional AI branch.
        completed_job = await service.get_job(ws.id, job.id)
        assert completed_job is not None
        assert completed_job.status == "partial_success"
        assert "AI_EXTRACTION_UNAVAILABLE" in (completed_job.error_message or "")
        assert [t.step_type for t in completed_job.tasks] == PostgresTaskDispatcher.STEP_SEQUENCE

        snapshot_result = await db_session.execute(select(SourceSnapshot))
        assert len(snapshot_result.scalars().all()) == 1
        block_result = await db_session.execute(select(DocumentBlock))
        assert len(block_result.scalars().all()) >= 2

        task_result = await db_session.execute(
            select(ResearchTask).where(ResearchTask.research_job_id == job.id)
        )
        outputs = [task.output_payload or "" for task in task_result.scalars().all()]
        assert any('"deterministic_fact_count": 4' in output for output in outputs)


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
