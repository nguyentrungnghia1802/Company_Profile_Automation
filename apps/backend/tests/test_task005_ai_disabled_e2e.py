"""Deterministic end-to-end coverage for TASK-CRAWL-005."""

from __future__ import annotations

import json
import tempfile
from typing import TYPE_CHECKING, Any, cast

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID, get_dev_admin, get_dev_workspace
from httpx import Request, Response
from sqlalchemy import select

from company_profile.config.settings import Settings
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.conflict import Conflict
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.identity import Workspace, WorkspaceMember
from company_profile.db.models.review import ReviewTask
from company_profile.db.models.source import (
    DocumentBlock,
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
)
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.research.dispatcher import PostgresTaskDispatcher
from company_profile.modules.research.pipeline import ResearchPipelineExecutor
from company_profile.modules.research.service import ResearchJobService
from company_profile.modules.sources.discovery import (
    ProviderOutcome,
    SourceDiscoveryService,
    TrustedSourceDefinition,
    TrustedSourceLookup,
)
from company_profile.modules.sources.fetcher import WebFetcher
from company_profile.modules.sources.trusted_sources import CountrySourceRegistry
from company_profile.modules.workspaces.repository import WorkspaceRepository
from company_profile.worker.runner import WorkerRunner

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.modules.sources.official_discovery import OfficialWebsiteDiscovery


HTML_FIXTURE = """
<html lang="vi">
  <head>
    <script type="application/ld+json">
      {"@type":"Organization","legalName":"Cong ty Co phan Fixture Acme",
       "url":"https://acme.example.com","taxID":"0312345678",
       "address":{"streetAddress":"1 Test Street","addressCountry":"VN"},
       "sameAs":["https://www.linkedin.com/company/acme"]}
    </script>
  </head>
  <body>
    <h1>Công ty cổ phần Fixture Acme</h1>
    <p>Mã số thuế: 0312345678</p>
    <p>Địa chỉ: 1 Test Street, Hồ Chí Minh</p>
  </body>
</html>
""".encode()


class FailingSearchProvider:
    """Search provider double that never touches the network."""

    provider_name = "failing-search"

    async def search(self, query: str, **kwargs: Any) -> list[Any]:
        del query, kwargs
        raise TimeoutError("fixture search timeout")


class RaisingWebsiteDiscoverer:
    """Website discovery double for provider-outage behavior."""

    async def discover(self, _url: str, *, scope: Mapping[str, Any]) -> Any:
        del scope
        raise ConnectionError("fixture website unavailable")


class RaisingTrustedProvider:
    """Trusted provider double that reports an outage through an exception."""

    definition = TrustedSourceDefinition(
        key="fixture_registry",
        domain="registry.example",
        provider_type="government_registry",
        source_type="registry",
        default_authority_tier=1,
        authority_by_field={"*": 1},
    )

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        del company, scope
        raise ConnectionError("fixture registry unavailable")


async def _make_company(
    db_session: AsyncSession,
    *,
    name: str = "Fixture Acme",
    website_url: str | None = "https://acme.example.com",
) -> CompanyProfile:
    """Create a deterministic workspace/company fixture."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(
            id=DEV_WORKSPACE_ID,
            name="TASK-CRAWL-005",
            slug="task-crawl-005",
        )
    )
    return await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name=name,
            normalized_name=name.lower(),
            website_url=website_url,
            status="published",
        )
    )


async def _run_fixture_job(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    settings: Settings,
    scope: dict[str, Any],
    search_provider: Any | None = None,
    company_website_url: str | None = "https://acme.example.com",
) -> tuple[Any, dict[str, Any]]:
    """Run the durable pipeline with mocked HTTP and inspect its final state."""

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        return Response(
            status_code=200,
            content=HTML_FIXTURE,
            headers={"content-type": "text/html; charset=utf-8"},
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    company = await _make_company(db_session, website_url=company_website_url)
    service = ResearchJobService(db_session)
    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        runner = WorkerRunner(
            worker_id="task-005-fixture-worker",
            session_factory=lambda: db_session,
            pipeline_factory=lambda session: ResearchPipelineExecutor(
                session,
                settings=settings,
                search_provider=search_provider,
                fetcher=fetcher,
            ),
        )
        job = await service.start_research_job(
            workspace_id=DEV_WORKSPACE_ID,
            company_id=company.id,
            scope=scope,
        )
        for _ in range(len(PostgresTaskDispatcher.STEP_SEQUENCE) + 2):
            await runner.tick()

    refreshed = await service.get_job(DEV_WORKSPACE_ID, job.id)
    assert refreshed is not None
    final_task = next(task for task in refreshed.tasks if task.step_type == "finalize")
    return refreshed, json.loads(final_task.output_payload or "{}")


@pytest.mark.asyncio
async def test_ai_disabled_keeps_artifacts_and_skips_only_semantic_work(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Official website + JSON-LD succeeds without an AI provider or live calls."""
    job, state = await _run_fixture_job(
        db_session,
        monkeypatch,
        settings=Settings(ai_provider="disabled", search_provider="none"),
        scope={"website_url": "https://acme.example.com", "crawl_website": False},
    )

    assert job.status == "partial_success"
    assert state["ai"]["status"] == "skipped"
    assert state["ai"]["reason"] == "AI_DISABLED"
    assert state["ai"]["translation"] == "skipped"
    assert state["ai"]["comparison"] == "skipped"
    assert state["ai"]["summary"] == "skipped"
    assert state["fetched_sources"]
    assert state["parsed_snapshots"]
    assert state["deterministic_fact_count"] >= 4
    assert state["review_task_count"] >= 1
    assert (await db_session.execute(select(SourceSnapshot))).scalars().all()
    assert (await db_session.execute(select(DocumentBlock))).scalars().all()
    assert (await db_session.execute(select(FactCandidate))).scalars().all()


@pytest.mark.asyncio
async def test_mock_ai_path_runs_after_acquisition(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional AI branch remains evidence-bound when a deterministic mock is configured."""
    job, state = await _run_fixture_job(
        db_session,
        monkeypatch,
        settings=Settings(ai_provider="mock", search_provider="none"),
        scope={"website_url": "https://acme.example.com", "crawl_website": False},
    )

    assert job.status == "partial_success"
    assert state["ai"]["status"] == "completed"
    assert state["ai"]["semantic_extraction"] == "completed"
    assert state["ai"]["fact_ids"]
    ai_candidates = (
        (await db_session.execute(select(FactCandidate).where(FactCandidate.origin_type == "ai")))
        .scalars()
        .all()
    )
    assert ai_candidates


@pytest.mark.asyncio
async def test_missing_gemini_key_skips_ai_after_acquisition(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured Gemini provider without credentials is an explicit partial result."""
    job, state = await _run_fixture_job(
        db_session,
        monkeypatch,
        settings=Settings(ai_provider="gemini", gemini_api_key="", search_provider="none"),
        scope={"website_url": "https://acme.example.com", "crawl_website": False},
    )

    assert job.status == "partial_success"
    assert state["ai"]["status"] == "skipped"
    assert state["ai"]["reason"] == "GEMINI_KEY_MISSING"
    assert state["ai"]["semantic_extraction"] == "skipped"
    assert state["fetched_sources"]
    assert state["deterministic_fact_count"] >= 4


@pytest.mark.asyncio
async def test_no_usable_source_finishes_without_fake_evidence(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No usable public source yields a clear partial result with no fabricated artifacts."""
    job, state = await _run_fixture_job(
        db_session,
        monkeypatch,
        settings=Settings(ai_provider="disabled", search_provider="none"),
        scope={},
        company_website_url=None,
    )

    assert job.status == "partial_success"
    assert state["result_status"] == "partial_success"
    assert state["fetched_sources"] == []
    assert state["parsed_snapshots"] == []
    assert state["deterministic_fact_count"] == 0
    assert "NO_SELECTED_SOURCES" in state["warnings"]
    assert not (await db_session.execute(select(SourceSnapshot))).scalars().all()
    assert not (await db_session.execute(select(DocumentBlock))).scalars().all()
    assert not (await db_session.execute(select(FactCandidate))).scalars().all()


@pytest.mark.asyncio
async def test_provider_outages_are_typed_and_do_not_stop_other_discovery(
    db_session: AsyncSession,
) -> None:
    """Search, official, and trusted outages remain warnings, not job crashes."""
    company = await _make_company(db_session, website_url=None)
    registry = CountrySourceRegistry(country_code="VN", providers=(RaisingTrustedProvider(),))
    result = await SourceDiscoveryService(
        db_session,
        search_provider=FailingSearchProvider(),
        trusted_registry=registry,
        website_discoverer=cast("OfficialWebsiteDiscovery", RaisingWebsiteDiscoverer()),
    ).discover(
        company,
        {
            "website_url": "https://acme.example.com",
            "include_search_results": True,
        },
    )

    outcomes = {(item.provider, item.outcome) for item in result.provider_outcomes}
    assert ("search_provider", ProviderOutcome.UNAVAILABLE) in outcomes
    assert ("official_website", ProviderOutcome.UNAVAILABLE) in outcomes
    assert ("fixture_registry", ProviderOutcome.UNAVAILABLE) in outcomes
    assert any(item.startswith("SEARCH_PROVIDER_UNAVAILABLE") for item in result.warnings)
    assert any(item.startswith("TRUSTED_PROVIDER_UNAVAILABLE") for item in result.warnings)

    unconfigured = await SourceDiscoveryService(
        db_session,
        trusted_registry=CountrySourceRegistry(country_code="VN", providers=()),
    ).discover(company, {"include_search_results": True})
    assert "SEARCH_PROVIDER_UNAVAILABLE:NOT_CONFIGURED" in unconfigured.warnings
    assert ("search_provider", ProviderOutcome.UNAVAILABLE) in {
        (item.provider, item.outcome) for item in unconfigured.provider_outcomes
    }


@pytest.mark.asyncio
async def test_review_inbox_tasks_cover_ambiguity_provider_and_missing_high_impact_fields(
    db_session: AsyncSession,
) -> None:
    """Review task creation is AI-independent and idempotent for each job reason."""
    company = await _make_company(db_session, website_url=None)
    job = await ResearchJobService(db_session).start_research_job(
        workspace_id=DEV_WORKSPACE_ID,
        company_id=company.id,
        scope={"mandatory_high_impact_fields": ["identity.tax_id"]},
    )
    executor = ResearchPipelineExecutor(
        db_session,
        settings=Settings(ai_provider="disabled", search_provider="none"),
    )
    state = {
        "workspace_id": str(DEV_WORKSPACE_ID),
        "company_id": str(company.id),
        "scope": {"mandatory_high_impact_fields": ["identity.tax_id"]},
        "rejected_sources": [
            {"url": "https://same-name.example", "reason": "ENTITY_MATCH_REVIEW_REQUIRED"},
            {"url": "https://unrelated.example", "reason": "LOW_ENTITY_MATCH:0.0"},
        ],
        "source_provider_outcomes": [
            {"provider": "tracuunnt_gdt", "outcome": "unavailable", "reason": "TIMEOUT"}
        ],
    }

    first = await executor._fact_processing(job, state)  # noqa: SLF001
    second = await executor._fact_processing(job, first)  # noqa: SLF001
    tasks = (
        (await db_session.execute(select(ReviewTask).where(ReviewTask.research_job_id == job.id)))
        .scalars()
        .all()
    )

    assert {task.task_type for task in tasks} == {
        "identity_ambiguity",
        "source_verification",
        "high_impact_fact",
    }
    assert len(tasks) == len(second["review_task_ids"])
    assert len({task.title for task in tasks}) == len(tasks)
    assert not any("unrelated.example" in task.title for task in tasks)


@pytest.mark.asyncio
async def test_strong_identifier_conflict_creates_urgent_review_task(
    db_session: AsyncSession,
) -> None:
    """Conflicting tax IDs are never silently accepted when AI is unavailable."""
    company = await _make_company(db_session, website_url=None)
    job = await ResearchJobService(db_session).start_research_job(
        workspace_id=DEV_WORKSPACE_ID,
        company_id=company.id,
        scope={"mandatory_high_impact_fields": []},
    )
    repository = FactCandidateRepository(db_session)
    for tax_id in ("0312345678", "0319999999"):
        await repository.create_candidate(
            workspace_id=DEV_WORKSPACE_ID,
            company_id=company.id,
            research_job_id=job.id,
            field_key="identity.tax_id",
            value=tax_id,
            origin_type="deterministic",
        )

    executor = ResearchPipelineExecutor(
        db_session,
        settings=Settings(ai_provider="disabled", search_provider="none"),
    )
    state = await executor._fact_processing(  # noqa: SLF001
        job,
        {
            "workspace_id": str(DEV_WORKSPACE_ID),
            "company_id": str(company.id),
            "scope": {"mandatory_high_impact_fields": []},
        },
    )
    conflicts = (await db_session.execute(select(Conflict))).scalars().all()
    review_tasks = (await db_session.execute(select(ReviewTask))).scalars().all()

    assert conflicts
    assert conflicts[0].materiality == "critical"
    assert state["review_task_count"] == 1
    assert review_tasks[0].task_type == "field_conflict"
    assert review_tasks[0].priority == "urgent"


@pytest.mark.asyncio
async def test_source_api_exposes_fetch_parser_and_provenance_state(
    async_client: Any,
    db_session: AsyncSession,
) -> None:
    """The source UI can render policy, parser, authority, and discovery evidence."""
    user = get_dev_admin()
    workspace = get_dev_workspace()
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="workspace_admin")
    )
    company = CompanyProfile(
        workspace_id=workspace.id,
        company_name="Source UI Corp",
        normalized_name="source ui corp",
    )
    db_session.add(company)
    await db_session.flush()
    source = Source(
        workspace_id=workspace.id,
        company_id=company.id,
        canonical_url="https://source-ui.example/company",
        normalized_url="https://source-ui.example/company",
        domain="source-ui.example",
        source_type="official_site",
        discovered_via="official_website",
        provider="fixture",
        authority_tier=1,
        entity_match_score=0.95,
        selection_reason="provided_url",
        discovery_provenance=["official_website", "source_history"],
        status="fetched",
    )
    db_session.add(source)
    await db_session.flush()
    db_session.add(
        SourceFetchAttempt(
            workspace_id=workspace.id,
            source_id=source.id,
            adapter="httpx",
            requested_url=source.canonical_url,
            http_status=200,
            byte_count=20,
            outcome_code="success",
            policy_result="allowed",
        )
    )
    snapshot = SourceSnapshot(
        workspace_id=workspace.id,
        source_id=source.id,
        content_hash="source-ui-hash",
        object_key="source-ui.html",
        content_type="text/html",
        byte_size=20,
        language="vi",
        parser_version="html-1.0",
        parser_status="success",
    )
    db_session.add(snapshot)
    await db_session.flush()
    db_session.add(
        DocumentBlock(
            workspace_id=workspace.id,
            source_snapshot_id=snapshot.id,
            block_key="h1_b0",
            block_type="heading",
            text_content="Source UI Corp",
            block_hash="source-ui-block",
            language="vi",
            parser_version="html-1.0",
            section_path=["h1"],
            location={"tag": "h1"},
        )
    )
    await db_session.flush()

    headers = {"Authorization": "Bearer mock-token-admin", "X-Workspace-ID": str(workspace.id)}
    response = await async_client.get(
        f"/api/v1/sources?company_id={company.id}",
        headers=headers,
    )
    assert response.status_code == 200
    item = response.json()["data"][0]
    assert item["discovered_via"] == "official_website"
    assert item["selection_reason"] == "provided_url"
    assert item["latest_fetch_policy_result"] == "allowed"
    assert item["latest_parser_status"] == "success"
