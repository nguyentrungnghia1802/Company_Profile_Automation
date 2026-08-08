"""Regression coverage for acquisition-first, AI-optional research execution."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING, Any

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from httpx import Request, Response
from sqlalchemy import select

from company_profile.config.settings import Settings
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.identity import Workspace
from company_profile.db.models.source import DocumentBlock, SourceSnapshot
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.research.dispatcher import PostgresTaskDispatcher
from company_profile.modules.research.pipeline import ResearchPipelineExecutor
from company_profile.modules.research.service import ResearchJobService
from company_profile.modules.sources.fetcher import WebFetcher
from company_profile.modules.workspaces.repository import WorkspaceRepository
from company_profile.worker.runner import WorkerRunner

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.integrations.ai.protocol import (
        AiInputBlock,
        AiRunResult,
        AiTranslationResult,
    )


class TimeoutAiProvider:
    """Provider double that simulates a bounded Gemini timeout."""

    async def run_extraction(
        self,
        _operation: str,
        _blocks: list[AiInputBlock],
        _company_name: str,
        **_kwargs: Any,
    ) -> AiRunResult:
        raise TimeoutError("simulated Gemini timeout")

    async def run_translation(
        self,
        _text: str,
        _target_language: str,
        _source_language: str | None = None,
        **_kwargs: Any,
    ) -> AiTranslationResult:
        raise TimeoutError("simulated Gemini timeout")


async def _run_fixture_pipeline(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    ai_provider: Any | None,
) -> tuple[AsyncSession, Any]:
    """Run a website-only fixture job through every durable step."""
    html = (
        b'<script type="application/ld+json">'
        b'{"@type":"Organization","legalName":"Timeout Corp",'
        b'"url":"https://timeout.example.com",'
        b'"address":{"streetAddress":"2 Test Street","addressCountry":"VN"}}'
        b"</script><h1>Timeout Corp</h1>"
    )

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        return Response(
            status_code=200,
            content=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    ws_repo = WorkspaceRepository(db_session)
    company_repo = CompanyRepository(db_session)
    service = ResearchJobService(db_session)
    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="AI Optional WS", slug="ai-opt"))
    company = await company_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Timeout Corp",
            normalized_name="timeout corp",
            status="published",
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        settings = Settings(ai_provider="disabled", search_provider="fixture")
        runner = WorkerRunner(
            worker_id="ai-optional-worker",
            session_factory=lambda: db_session,
            pipeline_factory=lambda session: ResearchPipelineExecutor(
                session,
                settings=settings,
                fetcher=fetcher,
                ai_provider=ai_provider,
            ),
        )
        job = await service.start_research_job(
            workspace_id=ws.id,
            company_id=company.id,
            scope={"website_url": "https://timeout.example.com"},
        )
        for _ in range(len(PostgresTaskDispatcher.STEP_SEQUENCE) + 1):
            await runner.tick()
        return db_session, job


@pytest.mark.asyncio
async def test_gemini_timeout_preserves_acquisition_artifacts(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AI failure becomes partial success after snapshots, blocks, and facts exist."""
    session, job = await _run_fixture_pipeline(db_session, monkeypatch, TimeoutAiProvider())

    refreshed_job = await ResearchJobService(session).get_job(DEV_WORKSPACE_ID, job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == "partial_success"
    assert "AI_EXTRACTION_FAILED" in (refreshed_job.error_message or "")

    snapshots = (await session.execute(select(SourceSnapshot))).scalars().all()
    blocks = (await session.execute(select(DocumentBlock))).scalars().all()
    candidates = (await session.execute(select(FactCandidate))).scalars().all()
    assert len(snapshots) == 1
    assert len(blocks) >= 2
    assert candidates
    assert {candidate.origin_type for candidate in candidates} == {"deterministic"}
