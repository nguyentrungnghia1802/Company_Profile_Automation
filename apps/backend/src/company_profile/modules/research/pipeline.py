"""AI-independent research pipeline orchestration.

The pipeline persists acquisition artifacts before invoking optional semantic
processing. Each step receives the complete JSON state from its predecessor so
worker retries can resume from durable source/snapshot/fact records.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from company_profile.config.settings import Settings, get_settings
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.research import ResearchJob, ResearchTask
from company_profile.db.models.review import ReviewTask
from company_profile.db.models.source import DocumentBlock, Source, SourceSnapshot, normalize_url
from company_profile.integrations.ai.mock_ai import MockAiProvider
from company_profile.integrations.ai.protocol import AiInputBlock
from company_profile.integrations.fetch.website_discovery import HttpxWebsiteFetchProvider
from company_profile.integrations.search.fixture_search import FixtureSearchProvider
from company_profile.modules.ai.service import AiExtractionService
from company_profile.modules.conflicts.engine import ConflictEngine
from company_profile.modules.facts.confidence import ConfidenceCalculator
from company_profile.modules.facts.deterministic import DeterministicFactExtractor
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.review.service import ReviewTaskService
from company_profile.modules.sources.discovery import SourceDiscoveryService
from company_profile.modules.sources.fetcher import CrawlCoordinator, WebFetcher
from company_profile.modules.sources.official_discovery import OfficialWebsiteDiscovery

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.integrations.ai.protocol import AiProvider
    from company_profile.modules.sources.trusted_sources import CountrySourceRegistry


class ResearchPipelineError(RuntimeError):
    """Raised for a critical pipeline dependency failure."""


class ResearchPipelineExecutor:
    """Execute one durable research step at a time."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        search_provider: Any | None = None,
        fetcher: WebFetcher | None = None,
        ai_provider: AiProvider | None = None,
        source_registry: CountrySourceRegistry | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.search_provider = search_provider
        self.fetcher = fetcher or WebFetcher(session)
        self.source_registry = source_registry
        self.ai_provider = (
            ai_provider if ai_provider is not None else self._build_ai_provider(self.settings)
        )

    async def execute(self, task: ResearchTask) -> dict[str, Any]:
        """Execute the claimed task and return the durable state payload."""
        job = await self.session.get(ResearchJob, task.research_job_id)
        if job is None or job.workspace_id != task.workspace_id:
            raise ResearchPipelineError("RESEARCH_JOB_NOT_FOUND_OR_CROSS_WORKSPACE")

        state = self._decode_state(task.input_payload)
        scope = self._decode_scope(job.scope)
        if "scope" not in state:
            state = {"scope": scope, **state}
        else:
            # The job scope is authoritative; a retried task cannot replace it
            # with an arbitrary predecessor payload.
            state["scope"] = scope
        state.setdefault("workspace_id", str(job.workspace_id))
        state.setdefault("company_id", str(job.company_id))
        state.setdefault("research_job_id", str(job.id))
        state.setdefault("warnings", [])
        state.setdefault("partial", False)

        handlers = {
            "entity_resolution": self._entity_resolution,
            "source_discovery": self._source_discovery,
            "source_selection": self._source_selection,
            "source_fetch": self._source_fetch,
            "document_parse": self._document_parse,
            "deterministic_extraction": self._deterministic_extraction,
            "ai_extraction": self._ai_extraction,
            "fact_processing": self._fact_processing,
            "finalize": self._finalize,
        }
        handler = handlers.get(task.step_type)
        if handler is None:
            raise ResearchPipelineError(f"UNKNOWN_RESEARCH_STEP:{task.step_type}")
        return await handler(job, state)

    async def _entity_resolution(self, _job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Resolve the already-created company within the job workspace."""
        company_id = uuid.UUID(state["company_id"])
        workspace_id = uuid.UUID(state["workspace_id"])
        stmt = select(CompanyProfile).where(
            CompanyProfile.id == company_id,
            CompanyProfile.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        company = result.scalar_one_or_none()
        if company is None or company.status == "merged":
            raise ResearchPipelineError("COMPANY_ENTITY_RESOLUTION_FAILED")

        state["entity"] = {
            "company_name": company.company_name,
            "legal_name": company.legal_name,
            "tax_id": company.tax_id,
            "registration_number": company.registration_number,
            "website_url": company.website_url,
        }
        return state

    async def _source_discovery(self, job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Discover source candidates without invoking AI or semantic processors."""
        company = await self._get_company(state)
        scope = state["scope"]
        provider = self.search_provider
        if provider is None and self.settings.search_provider == "fixture":
            provider = FixtureSearchProvider()
        website_discoverer = OfficialWebsiteDiscovery(
            HttpxWebsiteFetchProvider(
                user_agent=self.settings.fetch_user_agent,
                timeout=self.settings.fetch_timeout,
                max_response_bytes=self.settings.fetch_max_response_bytes,
                max_redirects=self.settings.fetch_max_redirects,
            ),
            user_agent=self.settings.fetch_user_agent,
            max_response_bytes=self.settings.fetch_max_response_bytes,
            max_depth=self.settings.crawl_max_depth,
            max_pages_per_domain=self.settings.crawl_max_pages_per_domain,
            max_pages_per_job=self.settings.crawl_max_pages_per_job,
            max_sitemaps=self.settings.crawl_max_sitemaps,
            max_sitemap_urls=self.settings.crawl_max_sitemap_urls,
        )
        discovery = SourceDiscoveryService(
            self.session,
            search_provider=provider,
            trusted_registry=self.source_registry,
            locale=self.settings.default_locale,
            website_discoverer=website_discoverer,
        )
        discovery_state = (
            await discovery.discover(company, scope, research_job_id=job.id)
        ).to_dict()
        state.update(discovery_state)
        for warning in discovery_state.get("source_discovery_warnings", []):
            self._warn(state, warning)
        return state

    async def _source_selection(self, _job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Apply deterministic URL/entity checks and persist source provenance."""
        company = await self._get_company(state)
        discovery = SourceDiscoveryService(
            self.session,
            trusted_registry=self.source_registry,
            locale=self.settings.default_locale,
        )
        selection = await discovery.select_sources(company, state.get("source_candidates", []))
        state["selected_sources"] = selection.selected
        state["rejected_sources"] = selection.rejected
        if selection.rejected:
            self._warn(state, f"SOURCES_REJECTED:{len(selection.rejected)}")
        if not selection.selected:
            self._warn(state, "NO_SELECTED_SOURCES")
        return state

    async def _source_fetch(self, job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Fetch selected sources while preserving successes when one fails."""
        workspace_id = uuid.UUID(state["workspace_id"])
        company_id = uuid.UUID(state["company_id"])
        fetched: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        selected_sources = list(state.get("selected_sources", []))
        selected_by_url = {
            normalize_url(str(selected["url"])): selected for selected in selected_sources
        }
        source_types = {
            normalize_url(str(selected["url"])): str(selected.get("source_type", "web_page"))
            for selected in selected_sources
        }
        coordinator = CrawlCoordinator(
            self.fetcher,
            max_depth=self.settings.crawl_max_depth,
            max_pages_per_domain=self.settings.crawl_max_pages_per_domain,
            max_pages_per_job=self.settings.crawl_max_pages_per_job,
        )
        pages = await coordinator.crawl(
            workspace_id,
            company_id,
            [str(selected["url"]) for selected in selected_sources],
            research_job_id=job.id,
            source_type_by_url=source_types,
            parse_content=False,
        )
        fetched_urls: set[str] = set()
        for page in pages:
            result = page.result
            fetched_urls.add(normalize_url(page.url))
            if result.snapshot is None:
                failures.append(
                    {
                        "url": page.url,
                        "error": result.error_message or f"HTTP_{result.status_code}",
                    }
                )
                continue
            selected = selected_by_url.get(normalize_url(page.url), {})
            fetched.append(
                {
                    "source_id": str(result.source.id),
                    "snapshot_id": str(result.snapshot.id),
                    "url": page.url,
                    "content_type": result.snapshot.content_type,
                    "crawl_depth": page.depth,
                    "discovered_via": selected.get("discovered_via", "crawl_link"),
                }
            )
        for selected in selected_sources:
            selected_url = normalize_url(str(selected["url"]))
            if selected_url not in fetched_urls:
                failures.append(
                    {"url": str(selected["url"]), "error": "CRAWL_BUDGET_OR_QUEUE_LIMIT"}
                )

        state["fetched_sources"] = fetched
        state["fetch_failures"] = failures
        if failures:
            self._warn(state, f"SOURCE_FETCH_PARTIAL:{len(failures)}")
        if not fetched:
            self._warn(state, "NO_FETCHED_SOURCES")
        return state

    async def _document_parse(self, _job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Parse stored snapshots after fetch has committed their metadata."""
        parsed: list[dict[str, Any]] = []
        for fetched in state.get("fetched_sources", []):
            snapshot_id = uuid.UUID(str(fetched["snapshot_id"]))
            snapshot = await self.session.get(SourceSnapshot, snapshot_id)
            if snapshot is None:
                self._warn(state, f"SNAPSHOT_NOT_FOUND:{snapshot_id}")
                continue
            try:
                blocks = await self.fetcher.parse_snapshot(snapshot)
            except Exception as exc:
                self._warn(state, f"DOCUMENT_PARSE_FAILED:{snapshot_id}:{type(exc).__name__}")
                continue
            parsed.append(
                {
                    "snapshot_id": str(snapshot.id),
                    "source_id": str(snapshot.source_id),
                    "block_count": len(blocks),
                    "block_ids": [block.block_key for block in blocks],
                }
            )
            if not blocks:
                self._warn(state, f"NO_DOCUMENT_BLOCKS:{snapshot_id}")

        state["parsed_snapshots"] = parsed
        return state

    async def _deterministic_extraction(
        self, job: ResearchJob, state: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract direct structured/labelled facts before any AI call."""
        snapshot_ids = [
            uuid.UUID(str(item["snapshot_id"])) for item in state.get("parsed_snapshots", [])
        ]
        if snapshot_ids:
            summary = await DeterministicFactExtractor(self.session).extract(
                workspace_id=job.workspace_id,
                company_id=job.company_id,
                research_job_id=job.id,
                snapshot_ids=snapshot_ids,
            )
            state["deterministic_fact_ids"] = summary.candidate_ids
            state["deterministic_fact_count"] = summary.fact_count
            for warning in summary.warnings:
                self._warn(state, warning)
        else:
            state["deterministic_fact_ids"] = []
            state["deterministic_fact_count"] = 0
        return state

    async def _ai_extraction(self, job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Run optional AI after acquisition and retain all prior artifacts on failure."""
        if self.ai_provider is None:
            state["ai"] = {"status": "skipped", "reason": "AI_UNAVAILABLE"}
            self._warn(state, "AI_EXTRACTION_UNAVAILABLE")
            return state

        company = await self._get_company(state)
        ai_service = AiExtractionService(
            provider=self.ai_provider,
            ai_budget_usd_per_job=self.settings.ai_budget_usd_per_job,
            ai_kill_switch_enabled=self.settings.ai_kill_switch_enabled,
        )
        ai_fact_ids: list[str] = []
        ai_failures: list[str] = []

        for parsed in state.get("parsed_snapshots", []):
            snapshot_id = uuid.UUID(str(parsed["snapshot_id"]))
            blocks_stmt = select(DocumentBlock).where(
                DocumentBlock.workspace_id == job.workspace_id,
                DocumentBlock.source_snapshot_id == snapshot_id,
            )
            blocks_result = await self.session.execute(blocks_stmt)
            blocks = list(blocks_result.scalars().all())
            if not blocks:
                continue

            ai_blocks = [
                AiInputBlock(
                    block_id=block.block_key,
                    block_type=block.block_type,
                    text_content=block.text_content,
                )
                for block in blocks
            ]
            try:
                outcome, _cost = await ai_service.extract(
                    session=self.session,
                    operation="extract_identity",
                    blocks=ai_blocks,
                    company_name=company.company_name,
                    workspace_id=job.workspace_id,
                    company_id=job.company_id,
                    valid_block_ids={block.block_key for block in blocks},
                    research_job_id=job.id,
                )
            except Exception as exc:
                ai_failures.append(f"{type(exc).__name__}:{exc}")
                continue

            if not outcome.is_valid or outcome.sanitized_result is None:
                ai_failures.extend(outcome.errors or ["AI_OUTPUT_INVALID"])
                continue
            ai_fact_ids.extend(
                await self._persist_ai_facts(
                    job, snapshot_id, blocks, outcome.sanitized_result.facts
                )
            )

        state["ai"] = {
            "status": "completed" if not ai_failures else "partial",
            "fact_ids": ai_fact_ids,
            "failures": ai_failures,
        }
        if ai_failures:
            for failure in ai_failures:
                self._warn(state, f"AI_EXTRACTION_FAILED:{failure}")
        return state

    async def _persist_ai_facts(
        self,
        job: ResearchJob,
        snapshot_id: uuid.UUID,
        blocks: list[DocumentBlock],
        facts: list[Any],
    ) -> list[str]:
        """Persist validated AI facts with the same evidence boundary as deterministic facts."""
        source = await self._source_for_snapshot(snapshot_id)
        if source is None:
            return []
        block_by_key = {block.block_key: block for block in blocks}
        repo = FactCandidateRepository(self.session)
        confidence_calculator = ConfidenceCalculator()
        persisted: list[str] = []
        for fact in facts:
            if fact.is_unknown:
                continue
            block = block_by_key.get(fact.evidence_block_ids[0])
            if block is None:
                continue
            confidence = confidence_calculator.calculate(
                field_key=fact.field_key,
                authority_tier=source.authority_for_field(fact.field_key),
                origin_type="ai",
                ai_confidence_hint=fact.confidence_hint,
            )
            candidate = await repo.create_candidate(
                workspace_id=job.workspace_id,
                company_id=job.company_id,
                field_key=fact.field_key,
                value=fact.value,
                origin_type="ai",
                value_type=DeterministicFactExtractor.value_type_for(fact.value),
                research_job_id=job.id,
                is_inferred=fact.is_inferred,
                confidence_score=confidence.total_score,
                confidence_components=confidence.to_dict(),
                confidence_explanation=confidence.explanation,
            )
            await repo.add_evidence(
                workspace_id=job.workspace_id,
                fact_candidate_id=candidate.id,
                source_snapshot_id=snapshot_id,
                document_block_id=block.id,
                original_excerpt=block.text_content,
                start_offset=0,
                end_offset=len(block.text_content),
                extraction_method="ai",
            )
            if str(candidate.id) not in persisted:
                persisted.append(str(candidate.id))
        return persisted

    async def _fact_processing(self, job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Detect material conflicts and create idempotent review tasks."""
        candidate_stmt = select(FactCandidate).where(
            FactCandidate.workspace_id == job.workspace_id,
            FactCandidate.company_id == job.company_id,
            FactCandidate.research_job_id == job.id,
        )
        candidate_result = await self.session.execute(candidate_stmt)
        fields = {candidate.field_key for candidate in candidate_result.scalars().all()}
        conflict_ids: list[str] = []
        review_ids: list[str] = []
        conflict_engine = ConflictEngine(self.session)
        review_service = ReviewTaskService(self.session)

        for field_key in sorted(fields):
            conflict = await conflict_engine.detect_and_update_conflicts(
                workspace_id=job.workspace_id,
                company_id=job.company_id,
                field_key=field_key,
            )
            if conflict is None:
                continue
            conflict_ids.append(str(conflict.id))
            review_stmt = select(ReviewTask).where(
                ReviewTask.workspace_id == job.workspace_id,
                ReviewTask.research_job_id == job.id,
                ReviewTask.conflict_id == conflict.id,
                ReviewTask.task_type == "field_conflict",
            )
            review_result = await self.session.execute(review_stmt)
            review_task = review_result.scalar_one_or_none()
            if review_task is None:
                review_task = await review_service.create_task(
                    workspace_id=job.workspace_id,
                    company_id=job.company_id,
                    research_job_id=job.id,
                    conflict_id=conflict.id,
                    task_type="field_conflict",
                    title=f"Review conflicting value for {field_key}",
                    description="Automated sources disagree; compare evidence before publication.",
                    priority="high" if conflict.materiality in ("critical", "high") else "medium",
                )
            review_ids.append(str(review_task.id))

        state["conflict_ids"] = conflict_ids
        state["review_task_ids"] = review_ids
        if conflict_ids:
            self._warn(state, f"REVIEW_REQUIRED_CONFLICTS:{len(conflict_ids)}")
        return state

    async def _finalize(self, _job: ResearchJob, state: dict[str, Any]) -> dict[str, Any]:
        """Emit a stable result status without changing prior artifacts."""
        state["result_status"] = "partial_success" if state.get("partial") else "completed"
        return state

    async def _get_company(self, state: dict[str, Any]) -> CompanyProfile:
        company = await self.session.get(CompanyProfile, uuid.UUID(state["company_id"]))
        if company is None or str(company.workspace_id) != str(state["workspace_id"]):
            raise ResearchPipelineError("COMPANY_NOT_FOUND")
        return company

    async def _source_for_snapshot(self, snapshot_id: uuid.UUID) -> Source | None:
        snapshot = await self.session.get(SourceSnapshot, snapshot_id)
        if snapshot is None:
            return None
        return await self.session.get(Source, snapshot.source_id)

    @staticmethod
    def _build_ai_provider(settings: Settings) -> AiProvider | None:
        provider_name = settings.ai_provider.strip().lower()
        if provider_name in {"disabled", "none", "off", "unavailable"}:
            return None
        if provider_name == "mock":
            return MockAiProvider()
        if provider_name == "gemini" and settings.gemini_api_key.strip():
            from company_profile.integrations.ai.gemini_adapter import GeminiAiProvider

            return GeminiAiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout=settings.ai_timeout,
                max_retries=settings.ai_max_retries,
                budget_usd_per_job=settings.ai_budget_usd_per_job,
            )
        return None

    @staticmethod
    def _decode_state(payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @staticmethod
    def _decode_scope(scope: str) -> dict[str, Any]:
        try:
            decoded = json.loads(scope or "{}")
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @staticmethod
    def _warn(state: dict[str, Any], warning: str) -> None:
        state["partial"] = True
        warnings = state.setdefault("warnings", [])
        if warning not in warnings:
            warnings.append(warning)
