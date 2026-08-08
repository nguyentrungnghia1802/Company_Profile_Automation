"""AI-independent source discovery, provenance, and deterministic selection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Protocol
from urllib.parse import urlparse

from sqlalchemy import select

from company_profile.db.models.source import Source, normalize_url
from company_profile.modules.sources.policy import (
    calculate_entity_match_score,
    classify_source_type,
)
from company_profile.modules.sources.query_builder import DiscoveryQuery, DiscoveryQueryBuilder
from company_profile.modules.sources.ranking import classify_and_rank_url
from company_profile.modules.sources.validator import validate_url_safety

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.db.models.company import CompanyProfile
    from company_profile.modules.sources.official_discovery import OfficialWebsiteDiscovery
    from company_profile.modules.sources.trusted_sources import CountrySourceRegistry


class ProviderOutcome(StrEnum):
    """Typed outcome for a discovery provider call."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
    MANUAL_REQUIRED = "manual_required"
    UNAVAILABLE = "unavailable"


class SearchProvider(Protocol):
    """Provider-neutral search contract returning metadata, not evidence."""

    async def search(self, query: str, **kwargs: Any) -> Sequence[Any]:
        """Return public search result metadata for a query."""


@dataclass(frozen=True, slots=True)
class TrustedSourceDefinition:
    """Configuration describing one trusted source without embedding core logic."""

    key: str
    domain: str
    provider_type: str
    source_type: str
    default_authority_tier: int
    authority_by_field: dict[str, int]
    access_policy: str = "structured_first_no_bypass"


@dataclass(frozen=True, slots=True)
class TrustedSourceLookup:
    """Typed result returned by a trusted-source provider adapter."""

    provider: str
    outcome: ProviderOutcome
    candidates: tuple[SourceDiscoveryCandidate, ...] = ()
    reason: str = ""


class TrustedSourceProvider(Protocol):
    """Provider contract for country-specific trusted source adapters."""

    definition: TrustedSourceDefinition

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Discover public source URLs for a company without fabricating records."""


@dataclass(slots=True)
class SourceDiscoveryCandidate:
    """A canonicalizable source candidate with explainable provenance."""

    url: str
    discovered_via: str
    provider: str | None = None
    source_type: str | None = None
    authority_tier: int | None = None
    authority_by_field: dict[str, int] = field(default_factory=dict)
    entity_match_score: float | None = None
    title: str = ""
    snippet: str = ""
    provided: bool = False
    selection_reason: str | None = None
    normalized_url: str = ""
    provenance: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    crawl_depth: int = 0
    page_group: str | None = None
    rank: int | None = None
    search_query: str | None = None

    def __post_init__(self) -> None:
        """Keep the primary discovery method represented in provenance."""
        if self.discovered_via not in self.provenance:
            self.provenance.insert(0, self.discovered_via)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe state representation for durable research steps."""
        return {
            "url": self.url,
            "normalized_url": self.normalized_url,
            "discovered_via": self.discovered_via,
            "discovery_provenance": list(self.provenance),
            "provider": self.provider,
            "source_type": self.source_type,
            "authority_tier": self.authority_tier,
            "authority_by_field": dict(self.authority_by_field),
            "entity_match_score": self.entity_match_score,
            "title": self.title,
            "snippet": self.snippet,
            "provided": self.provided,
            "selection_reason": self.selection_reason,
            "relevance_score": self.relevance_score,
            "crawl_depth": self.crawl_depth,
            "page_group": self.page_group,
            "rank": self.rank,
            "search_query": self.search_query,
        }


@dataclass(frozen=True, slots=True)
class ProviderOutcomeRecord:
    """Serializable provider outcome retained in research state."""

    provider: str
    provider_type: str
    outcome: ProviderOutcome
    reason: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-safe provider outcome."""
        return {
            "provider": self.provider,
            "provider_type": self.provider_type,
            "outcome": self.outcome.value,
            "reason": self.reason,
        }


@dataclass(slots=True)
class DiscoveryResult:
    """Discovery output used by the durable research pipeline."""

    candidates: list[SourceDiscoveryCandidate] = field(default_factory=list)
    provider_outcomes: list[ProviderOutcomeRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    search_queries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the discovery result as durable JSON state."""
        return {
            "source_candidates": [candidate.to_dict() for candidate in self.candidates],
            "source_provider_outcomes": [outcome.to_dict() for outcome in self.provider_outcomes],
            "source_discovery_warnings": list(self.warnings),
            "search_queries": list(self.search_queries),
        }


@dataclass(slots=True)
class SelectionResult:
    """Selected and rejected source records produced by deterministic policy."""

    selected: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)


class SourceDiscoveryService:
    """Aggregate source candidates and persist deterministic selection metadata."""

    _DISCOVERY_PRIORITY: ClassVar[dict[str, int]] = {
        "verified_official_domain": 70,
        "official_website": 65,
        "manual_url": 60,
        "trusted_provider": 55,
        "source_history": 50,
        "sitemap": 40,
        "internal_link": 35,
        "search_provider": 30,
    }

    def __init__(
        self,
        session: AsyncSession,
        search_provider: SearchProvider | None = None,
        trusted_registry: CountrySourceRegistry | None = None,
        locale: str = "vi",
        website_discoverer: OfficialWebsiteDiscovery | None = None,
        query_builder: DiscoveryQueryBuilder | None = None,
    ) -> None:
        self.session = session
        self.search_provider = search_provider
        self.locale = locale
        self.website_discoverer = website_discoverer
        self.query_builder = query_builder or DiscoveryQueryBuilder()
        if trusted_registry is None:
            from company_profile.modules.sources.trusted_sources import CountrySourceRegistry

            trusted_registry = CountrySourceRegistry.for_country("VN")
        self.trusted_registry = trusted_registry

    async def discover(
        self,
        company: CompanyProfile,
        scope: Mapping[str, Any],
        *,
        research_job_id: uuid.UUID | None = None,
    ) -> DiscoveryResult:
        """Discover and deduplicate candidates from configured public metadata sources."""
        result = DiscoveryResult()
        candidates: dict[str, SourceDiscoveryCandidate] = {}

        website_urls = self._string_values(scope, ("website_url", "website"))
        if company.website_url:
            website_urls.append(company.website_url)
        website_urls = list(dict.fromkeys(website_urls))
        if self.website_discoverer is not None and bool(scope.get("crawl_website", True)):
            for url in website_urls:
                await self._discover_from_official_website(url, scope, candidates, result, company)
        else:
            for url in website_urls:
                self._add_candidate(
                    candidates,
                    SourceDiscoveryCandidate(
                        url=url,
                        discovered_via="official_website",
                        provided=True,
                    ),
                    company,
                )

        for url in self._string_values(
            scope, ("verified_official_domain", "official_domain", "verified_domain")
        ):
            self._add_candidate(
                candidates,
                SourceDiscoveryCandidate(
                    url=self._ensure_url_scheme(url),
                    discovered_via="verified_official_domain",
                    provided=True,
                ),
                company,
            )

        if company.website_url and self.website_discoverer is None:
            self._add_candidate(
                candidates,
                SourceDiscoveryCandidate(
                    url=company.website_url,
                    discovered_via="official_website",
                    provided=True,
                ),
                company,
            )

        for key, via in (
            (("manual_url", "manual_urls", "source_url", "source_urls"), "manual_url"),
            (("sitemap", "sitemap_url", "sitemap_urls"), "sitemap"),
            (("internal_link", "internal_links", "links"), "internal_link"),
        ):
            for item in self._items(scope, key):
                self._add_candidate(
                    candidates,
                    self._candidate_from_item(item, discovered_via=via),
                    company,
                )

        search_scope = dict(scope)
        if self.search_provider is not None and "aliases" not in search_scope:
            from company_profile.db.models.company import CompanyAlias

            alias_statement = select(CompanyAlias.alias_name).where(
                CompanyAlias.workspace_id == company.workspace_id,
                CompanyAlias.company_id == company.id,
            )
            alias_rows = (await self.session.execute(alias_statement)).scalars().all()
            search_scope["aliases"] = list(alias_rows)
        await self._discover_from_search(company, search_scope, candidates, result, research_job_id)
        await self._discover_from_trusted_providers(company, scope, candidates, result)
        await self._discover_from_history(company, candidates)

        result.candidates = sorted(
            candidates.values(),
            key=lambda candidate: (
                -(candidate.relevance_score or 0.0),
                self._DISCOVERY_PRIORITY.get(candidate.discovered_via, 0) * -1,
                candidate.normalized_url,
            ),
        )
        if not result.candidates:
            result.warnings.append("NO_SOURCE_CANDIDATES")
        return result

    async def select_sources(
        self,
        company: CompanyProfile,
        candidates: Sequence[SourceDiscoveryCandidate | Mapping[str, Any]],
    ) -> SelectionResult:
        """Apply URL/entity policy and persist selected or rejected source metadata."""
        selected: list[dict[str, Any]] = []
        rejected: list[dict[str, str]] = []
        seen: set[str] = set()

        for raw_candidate in candidates:
            candidate = self._coerce_candidate(raw_candidate)
            normalized = candidate.normalized_url or normalize_url(candidate.url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)

            safe, safety_reason = validate_url_safety(candidate.url)
            parsed = urlparse(normalized)
            domain = (parsed.hostname or "").lower()
            if not domain:
                rejected.append({"url": candidate.url, "reason": "INVALID_HOST"})
                continue

            source_type, classified_tier = classify_source_type(domain, normalized)
            source_type = candidate.source_type or source_type
            authority_map = dict(candidate.authority_by_field)
            authority_tier = candidate.authority_tier or classified_tier
            if not authority_map:
                authority_map = {"*": authority_tier}
            match_score = candidate.entity_match_score
            if match_score is None:
                match_score = (
                    1.0
                    if candidate.provided
                    else calculate_entity_match_score(
                        company.company_name,
                        company.tax_id,
                        f"{candidate.title} {candidate.snippet}".strip(),
                    )
                )

            selection_reason = candidate.selection_reason or self._selection_reason(candidate)
            rejection_reason: str | None = None
            if not safe:
                rejection_reason = f"UNSAFE_URL:{safety_reason}"
            elif classify_and_rank_url(
                normalized,
                title=candidate.title,
                snippet=candidate.snippet,
                discovered_via=candidate.discovered_via,
                crawl_depth=candidate.crawl_depth,
            ).excluded:
                rejection_reason = "EXCLUDED_URL_TOKEN"
            elif match_score < 0.3:
                rejection_reason = f"LOW_ENTITY_MATCH:{match_score}"
            elif candidate.discovered_via == "search_provider" and match_score < 0.75:
                rejection_reason = "ENTITY_MATCH_REVIEW_REQUIRED"

            source = await self._get_source(company, normalized)
            if rejection_reason is not None:
                rejected.append({"url": candidate.url, "reason": rejection_reason})
                if source is None:
                    source = Source(
                        workspace_id=company.workspace_id,
                        company_id=company.id,
                        canonical_url=candidate.url,
                        normalized_url=normalized,
                        domain=domain,
                        source_type=source_type,
                        authority_tier=authority_tier,
                        status="rejected",
                        entity_match_score=match_score,
                    )
                    self.session.add(source)
                self._update_source_metadata(
                    source,
                    candidate=candidate,
                    source_type=source_type,
                    authority_tier=authority_tier,
                    authority_map=authority_map,
                    match_score=match_score,
                    selection_reason=selection_reason,
                    rejection_reason=rejection_reason,
                )
                await self.session.flush()
                continue

            if source is None:
                source = Source(
                    workspace_id=company.workspace_id,
                    company_id=company.id,
                    canonical_url=candidate.url,
                    normalized_url=normalized,
                    domain=domain,
                    source_type=source_type,
                    authority_tier=authority_tier,
                    status="discovered",
                    entity_match_score=match_score,
                )
                self.session.add(source)
            self._update_source_metadata(
                source,
                candidate=candidate,
                source_type=source_type,
                authority_tier=authority_tier,
                authority_map=authority_map,
                match_score=match_score,
                selection_reason=selection_reason,
                rejection_reason=None,
            )
            if source.status == "rejected":
                source.status = "discovered"
            await self.session.flush()
            selected.append(
                {
                    "source_id": str(source.id),
                    "url": candidate.url,
                    "normalized_url": normalized,
                    "discovered_via": source.discovered_via,
                    "discovery_provenance": list(source.discovery_provenance or []),
                    "provider": source.provider,
                    "source_type": source_type,
                    "authority_tier": authority_tier,
                    "authority_by_field": dict(source.authority_by_field or {}),
                    "entity_match_score": match_score,
                    "selection_reason": selection_reason,
                }
            )

        return SelectionResult(selected=selected, rejected=rejected)

    async def _discover_from_search(
        self,
        company: CompanyProfile,
        scope: Mapping[str, Any],
        candidates: dict[str, SourceDiscoveryCandidate],
        result: DiscoveryResult,
        research_job_id: uuid.UUID | None,
    ) -> None:
        """Collect search metadata without treating snippets as evidence."""
        if self.search_provider is None:
            if bool(scope.get("include_search_results", False)):
                result.warnings.append("SEARCH_PROVIDER_UNAVAILABLE:NOT_CONFIGURED")
                result.provider_outcomes.append(
                    ProviderOutcomeRecord(
                        "search_provider",
                        "search",
                        ProviderOutcome.UNAVAILABLE,
                        "NOT_CONFIGURED",
                    )
                )
            return
        if candidates and not bool(scope.get("include_search_results", False)):
            return

        queries = self.query_builder.build(company, scope, default_locale=self.locale)
        provider_name = str(
            getattr(self.search_provider, "provider_name", type(self.search_provider).__name__)
        )
        successful_queries = 0
        total_items = 0
        for query_spec in queries:
            query_state = self._query_state(query_spec, provider_name)
            query_id: str | None = None
            if research_job_id is not None:
                query_id = str(
                    await self._persist_search_query(
                        company,
                        research_job_id,
                        query_spec,
                        provider_name,
                    )
                )
                query_state["query_id"] = query_id
            try:
                items = list(
                    await self.search_provider.search(
                        query_spec.query,
                        locale=query_spec.language_code,
                        language=query_spec.language_code,
                        requested_section=query_spec.requested_section,
                    )
                )
            except Exception as exc:  # provider outage is non-critical
                reason = f"{type(exc).__name__}"
                result.warnings.append(f"SEARCH_PROVIDER_UNAVAILABLE:{reason}")
                query_state["error"] = reason
                result.search_queries.append(query_state)
                continue

            successful_queries += 1
            total_items += len(items)
            result.search_queries.append(query_state)
            for rank, item in enumerate(items, start=1):
                self._add_search_result(
                    company,
                    query_spec,
                    provider_name,
                    rank,
                    item,
                    candidates,
                    query_state.get("query_id"),
                )

        if successful_queries == 0:
            outcome = ProviderOutcome.UNAVAILABLE
            reason = "NO_QUERY_SUCCEEDED"
        elif total_items == 0:
            outcome = ProviderOutcome.NOT_FOUND
            reason = "NO_RESULTS"
        else:
            outcome = ProviderOutcome.SUCCESS
            reason = f"QUERIES:{successful_queries};RESULTS:{total_items}"
        result.provider_outcomes.append(
            ProviderOutcomeRecord("search_provider", "search", outcome, reason)
        )

    async def _discover_from_official_website(
        self,
        url: str,
        scope: Mapping[str, Any],
        candidates: dict[str, SourceDiscoveryCandidate],
        result: DiscoveryResult,
        company: CompanyProfile,
    ) -> None:
        """Run the bounded official website adapter and merge its candidates."""
        if self.website_discoverer is None:
            return
        try:
            website_result = await self.website_discoverer.discover(url, scope=scope)
        except Exception as exc:  # one website adapter failure must not stop discovery
            reason = type(exc).__name__
            result.provider_outcomes.append(
                ProviderOutcomeRecord(
                    "official_website",
                    "website_discovery",
                    ProviderOutcome.UNAVAILABLE,
                    reason,
                )
            )
            result.warnings.append(f"OFFICIAL_WEBSITE_UNAVAILABLE:{reason}")
            return
        robots_key = website_result.robots.decision if website_result.robots else "unknown"
        outcome = {
            "allowed": ProviderOutcome.SUCCESS,
            "blocked": ProviderOutcome.BLOCKED,
            "unknown": ProviderOutcome.UNAVAILABLE,
        }.get(robots_key, ProviderOutcome.UNAVAILABLE)
        result.provider_outcomes.append(
            ProviderOutcomeRecord(
                "official_website",
                "website_discovery",
                outcome,
                website_result.robots.reason if website_result.robots else "NO_ROBOTS_DECISION",
            )
        )
        result.warnings.extend(website_result.warnings)
        for candidate in website_result.candidates:
            self._add_candidate(candidates, candidate, company)

    async def _persist_search_query(
        self,
        company: CompanyProfile,
        research_job_id: uuid.UUID,
        query_spec: DiscoveryQuery,
        provider_name: str,
    ) -> uuid.UUID:
        """Persist the query envelope before its result metadata."""
        from company_profile.db.models.search import ResearchQuery

        query = ResearchQuery(
            workspace_id=company.workspace_id,
            research_job_id=research_job_id,
            query_text=query_spec.query,
            language_code=query_spec.language_code,
            purpose=query_spec.purpose,
            requested_section=query_spec.requested_section,
            provider=provider_name,
            generated_by=query_spec.generated_by,
        )
        self.session.add(query)
        await self.session.flush()
        return query.id

    @staticmethod
    def _query_state(
        query_spec: DiscoveryQuery,
        provider_name: str,
        *,
        reason: str = "",
    ) -> dict[str, Any]:
        """Return query metadata safe for durable research state."""
        return {
            "query": query_spec.query,
            "language_code": query_spec.language_code,
            "purpose": query_spec.purpose,
            "requested_section": query_spec.requested_section,
            "provider": provider_name,
            "generated_by": query_spec.generated_by,
            "error": reason,
        }

    def _add_search_result(
        self,
        company: CompanyProfile,
        query_spec: DiscoveryQuery,
        provider_name: str,
        rank: int,
        item: Any,
        candidates: dict[str, SourceDiscoveryCandidate],
        query_id: str | None,
    ) -> None:
        """Rank provider metadata, persist it, then expose it as a candidate."""
        url = str(self._item_value(item, "url") or "").strip()
        if not url:
            return
        title = str(self._item_value(item, "title") or "")
        snippet = str(self._item_value(item, "snippet") or "")
        normalized = normalize_url(url)
        ranking = classify_and_rank_url(
            normalized,
            title=title,
            snippet=snippet,
            discovered_via="search_provider",
            crawl_depth=0,
        )
        safe, safety_reason = validate_url_safety(url)
        parsed_domain = urlparse(normalized).hostname or ""
        classified_source_type, _ = classify_source_type(parsed_domain, normalized)
        match_score = self._item_value(item, "entity_match_score")
        if not isinstance(match_score, (float, int)):
            match_score = calculate_entity_match_score(
                company.company_name,
                company.tax_id,
                f"{title} {snippet}".strip(),
            )
        match_score = float(match_score)
        if not safe:
            status = "rejected"
            selection_reason = f"UNSAFE_URL:{safety_reason}"
        elif ranking.excluded:
            status = "rejected"
            selection_reason = "EXCLUDED_URL_TOKEN"
        elif match_score < 0.3:
            status = "rejected"
            selection_reason = f"LOW_ENTITY_MATCH:{match_score}"
        elif match_score < 0.75:
            status = "review"
            selection_reason = "ENTITY_MATCH_REVIEW_REQUIRED"
        else:
            status = "candidate"
            selection_reason = ranking.reason

        candidate = SourceDiscoveryCandidate(
            url=url,
            discovered_via="search_provider",
            provider=provider_name,
            title=title,
            snippet=snippet,
            entity_match_score=match_score,
            selection_reason=selection_reason,
            normalized_url=normalized,
            relevance_score=ranking.relevance_score,
            page_group=ranking.page_group,
            rank=rank,
            search_query=query_spec.query,
        )
        self._add_candidate(candidates, candidate, company)
        if query_id is not None:
            self.session.add(
                self._search_result_model(
                    company=company,
                    query_id=uuid.UUID(query_id),
                    provider_name=provider_name,
                    url=normalized,
                    title=title,
                    snippet=snippet,
                    rank=rank,
                    status=status,
                    selection_reason=selection_reason,
                    match_score=match_score,
                    source_type=classified_source_type,
                    item=item,
                )
            )

    @staticmethod
    def _search_result_model(
        *,
        company: CompanyProfile,
        query_id: uuid.UUID,
        provider_name: str,
        url: str,
        title: str,
        snippet: str,
        rank: int,
        status: str,
        selection_reason: str,
        match_score: float,
        source_type: str,
        item: Any,
    ) -> Any:
        """Build a durable search-result row without treating snippets as evidence."""
        from company_profile.db.models.search import SearchResult

        metadata = SourceDiscoveryService._item_value(item, "metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        result_timestamp = SourceDiscoveryService._item_value(item, "timestamp")
        if not isinstance(result_timestamp, datetime):
            result_timestamp = datetime.now(UTC)
        return SearchResult(
            workspace_id=company.workspace_id,
            research_query_id=query_id,
            provider=provider_name,
            normalized_url=url,
            final_url=url,
            title=title,
            snippet=snippet,
            rank=rank,
            provider_metadata=metadata,
            selection_status=status,
            selection_reason=selection_reason,
            entity_match_score=match_score,
            source_type=source_type,
            result_timestamp=result_timestamp,
        )

    async def _discover_from_trusted_providers(
        self,
        company: CompanyProfile,
        scope: Mapping[str, Any],
        candidates: dict[str, SourceDiscoveryCandidate],
        result: DiscoveryResult,
    ) -> None:
        """Call configured trusted adapters and retain typed, non-fabricated outcomes."""
        for provider in self.trusted_registry.providers:
            definition = provider.definition
            try:
                lookup = await provider.discover(company=company, scope=scope)
            except Exception as exc:  # one trusted provider must not stop discovery
                reason = type(exc).__name__
                result.provider_outcomes.append(
                    ProviderOutcomeRecord(
                        definition.key,
                        definition.provider_type,
                        ProviderOutcome.UNAVAILABLE,
                        reason,
                    )
                )
                result.warnings.append(
                    f"TRUSTED_PROVIDER_{ProviderOutcome.UNAVAILABLE.value.upper()}:{definition.key}:{reason}"
                )
                continue

            result.provider_outcomes.append(
                ProviderOutcomeRecord(
                    definition.key,
                    definition.provider_type,
                    lookup.outcome,
                    lookup.reason,
                )
            )
            if lookup.outcome in {
                ProviderOutcome.BLOCKED,
                ProviderOutcome.MANUAL_REQUIRED,
                ProviderOutcome.UNAVAILABLE,
            }:
                reason = lookup.reason or "NO_DETAILS"
                result.warnings.append(
                    f"TRUSTED_PROVIDER_{lookup.outcome.value.upper()}:{definition.key}:{reason}"
                )
            for candidate in lookup.candidates:
                self._add_candidate(candidates, candidate, company)

    async def _discover_from_history(
        self,
        company: CompanyProfile,
        candidates: dict[str, SourceDiscoveryCandidate],
    ) -> None:
        """Reuse prior research source URLs as a bounded discovery input."""
        statement = select(Source).where(
            Source.workspace_id == company.workspace_id,
            Source.company_id == company.id,
        )
        rows = (await self.session.execute(statement)).scalars().all()
        for source in rows:
            if source.status == "rejected":
                continue
            self._add_candidate(
                candidates,
                SourceDiscoveryCandidate(
                    url=source.canonical_url,
                    discovered_via="source_history",
                    provider=source.provider,
                    source_type=source.source_type,
                    authority_tier=source.authority_tier,
                    authority_by_field=dict(source.authority_by_field or {}),
                    entity_match_score=source.entity_match_score or 1.0,
                    provided=True,
                    selection_reason="source_history",
                    provenance=["source_history"],
                ),
                company,
            )

    async def _get_source(self, company: CompanyProfile, normalized_url: str) -> Source | None:
        """Load a source within the company/workspace tenant boundary."""
        statement = select(Source).where(
            Source.workspace_id == company.workspace_id,
            Source.company_id == company.id,
            Source.normalized_url == normalized_url,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    def _add_candidate(
        self,
        candidates: dict[str, SourceDiscoveryCandidate],
        candidate: SourceDiscoveryCandidate,
        company: CompanyProfile,
    ) -> None:
        """Canonicalize one candidate and merge duplicate provenance deterministically."""
        normalized = normalize_url(candidate.url)
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return

        source_type, classified_tier = classify_source_type(parsed.hostname.lower(), normalized)
        enriched = replace(
            candidate,
            normalized_url=normalized,
            source_type=candidate.source_type or source_type,
            authority_tier=candidate.authority_tier or classified_tier,
            authority_by_field=dict(candidate.authority_by_field)
            or {"*": candidate.authority_tier or classified_tier},
        )
        if enriched.entity_match_score is None:
            enriched.entity_match_score = (
                1.0
                if enriched.provided
                else calculate_entity_match_score(
                    company.company_name,
                    company.tax_id,
                    f"{enriched.title} {enriched.snippet}".strip(),
                )
            )

        existing = candidates.get(normalized)
        if existing is None:
            candidates[normalized] = enriched
            return

        merged_provenance = list(dict.fromkeys(existing.provenance + enriched.provenance))
        preferred = existing
        if self._DISCOVERY_PRIORITY.get(enriched.discovered_via, 0) > self._DISCOVERY_PRIORITY.get(
            existing.discovered_via, 0
        ):
            preferred = enriched
        authority_map = dict(existing.authority_by_field)
        for field_key, tier in enriched.authority_by_field.items():
            current = authority_map.get(field_key)
            authority_map[field_key] = tier if current is None else min(current, tier)
        candidates[normalized] = replace(
            preferred,
            url=existing.url,
            normalized_url=normalized,
            authority_tier=min(
                value for value in (existing.authority_tier or 4, enriched.authority_tier or 4)
            ),
            authority_by_field=authority_map,
            entity_match_score=max(
                existing.entity_match_score or 0.0, enriched.entity_match_score or 0.0
            ),
            title=existing.title or enriched.title,
            snippet=existing.snippet or enriched.snippet,
            provided=existing.provided or enriched.provided,
            provider=preferred.provider or existing.provider or enriched.provider,
            provenance=merged_provenance,
            relevance_score=max(existing.relevance_score, enriched.relevance_score),
            crawl_depth=min(existing.crawl_depth, enriched.crawl_depth),
            page_group=existing.page_group or enriched.page_group,
            rank=existing.rank or enriched.rank,
            search_query=existing.search_query or enriched.search_query,
        )

    def _update_source_metadata(
        self,
        source: Source,
        *,
        candidate: SourceDiscoveryCandidate,
        source_type: str,
        authority_tier: int,
        authority_map: dict[str, int],
        match_score: float,
        selection_reason: str,
        rejection_reason: str | None,
    ) -> None:
        """Copy explainable discovery metadata onto a durable Source record."""
        source.source_type = source_type
        source.authority_tier = authority_tier
        source.authority_by_field = authority_map
        source.entity_match_score = match_score
        source.discovered_via = candidate.discovered_via
        source.provider = candidate.provider
        source.discovery_provenance = list(dict.fromkeys(candidate.provenance))
        source.selection_reason = selection_reason
        source.rejection_reason = rejection_reason

    @staticmethod
    def _coerce_candidate(
        candidate: SourceDiscoveryCandidate | Mapping[str, Any],
    ) -> SourceDiscoveryCandidate:
        """Coerce durable JSON state back into a candidate object."""
        if isinstance(candidate, SourceDiscoveryCandidate):
            return candidate
        return SourceDiscoveryCandidate(
            url=str(candidate.get("url", "")),
            discovered_via=str(candidate.get("discovered_via", "manual_url")),
            provider=candidate.get("provider"),
            source_type=candidate.get("source_type"),
            authority_tier=candidate.get("authority_tier"),
            authority_by_field=dict(candidate.get("authority_by_field") or {}),
            entity_match_score=candidate.get("entity_match_score"),
            title=str(candidate.get("title", "")),
            snippet=str(candidate.get("snippet", "")),
            provided=bool(candidate.get("provided", False)),
            selection_reason=candidate.get("selection_reason"),
            normalized_url=str(candidate.get("normalized_url", "")),
            provenance=list(
                candidate.get("discovery_provenance")
                or [str(candidate.get("discovered_via", "manual_url"))]
            ),
            relevance_score=float(candidate.get("relevance_score") or 0.0),
            crawl_depth=int(candidate.get("crawl_depth") or 0),
            page_group=candidate.get("page_group"),
            rank=candidate.get("rank"),
            search_query=candidate.get("search_query"),
        )

    @staticmethod
    def _selection_reason(candidate: SourceDiscoveryCandidate) -> str:
        """Explain why a candidate was accepted by deterministic policy."""
        if candidate.selection_reason:
            return candidate.selection_reason
        if candidate.provided:
            return "provided_url"
        if candidate.discovered_via == "trusted_provider":
            return "trusted_provider"
        if candidate.discovered_via == "source_history":
            return "source_history"
        return "entity_match"

    @staticmethod
    def _candidate_from_item(item: Any, discovered_via: str) -> SourceDiscoveryCandidate:
        """Build a candidate from a URL string or pre-crawled link metadata."""
        if isinstance(item, str):
            return SourceDiscoveryCandidate(url=item, discovered_via=discovered_via, provided=True)
        if isinstance(item, dict):
            return SourceDiscoveryCandidate(
                url=str(item.get("url", "")),
                discovered_via=discovered_via,
                title=str(item.get("title", "")),
                snippet=str(item.get("snippet", "")),
                provided=bool(item.get("provided", True)),
            )
        return SourceDiscoveryCandidate(url="", discovered_via=discovered_via)

    @staticmethod
    def _items(scope: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
        """Read string/list link values from a scope without trusting arbitrary objects."""
        values: list[Any] = []
        for key in keys:
            value = scope.get(key)
            if isinstance(value, (str, dict)):
                values.append(value)
            elif isinstance(value, list):
                values.extend(value)
        return values

    @staticmethod
    def _string_values(scope: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
        """Read direct string URL values from scope."""
        return [
            value for value in SourceDiscoveryService._items(scope, keys) if isinstance(value, str)
        ]

    @staticmethod
    def _item_value(item: Any, key: str) -> Any:
        """Read an attribute or mapping key from a provider result."""
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    @staticmethod
    def _ensure_url_scheme(value: str) -> str:
        """Make a verified host URL explicit while leaving full URLs unchanged."""
        return value if "://" in value else f"https://{value}"
