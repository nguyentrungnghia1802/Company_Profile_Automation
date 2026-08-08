"""Regression tests for AI-independent source discovery and trusted providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from sqlalchemy import select

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.source import Source
from company_profile.integrations.search.fixture_search import SearchResultItem
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.sources.discovery import (
    ProviderOutcome,
    SourceDiscoveryCandidate,
    SourceDiscoveryService,
    TrustedSourceDefinition,
    TrustedSourceLookup,
)
from company_profile.modules.sources.trusted_sources import (
    CountrySourceRegistry,
    vietnam_source_registry,
)
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession


class FixtureSearchProvider:
    """Deterministic search provider for source discovery tests."""

    async def search(self, _query: str, **_kwargs: Any) -> list[SearchResultItem]:
        """Return one company-matching result."""
        return [
            SearchResultItem(
                title="Example Company overview",
                url="https://example.vn/about/",
                snippet="Example Company official overview",
                domain="example.vn",
            )
        ]


class CustomTrustedProvider:
    """Provider double proving registry extension does not require core edits."""

    definition = TrustedSourceDefinition(
        key="companies_house",
        domain="find-and-update.company-information.service.gov.uk",
        provider_type="companies_house_registry",
        source_type="registry",
        default_authority_tier=1,
        authority_by_field={"identity.legal_name": 1, "*": 2},
    )

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Return a real-looking fixture URL supplied by this adapter itself."""
        del company, scope
        return TrustedSourceLookup(
            provider=self.definition.key,
            outcome=ProviderOutcome.SUCCESS,
            candidates=(
                SourceDiscoveryCandidate(
                    url="https://find-and-update.company-information.service.gov.uk/company/123",
                    discovered_via="trusted_provider",
                    provider=self.definition.key,
                    source_type="registry",
                    authority_tier=1,
                    authority_by_field={"identity.legal_name": 1, "*": 2},
                    entity_match_score=1.0,
                ),
            ),
        )


async def _company(db_session: AsyncSession) -> CompanyProfile:
    """Create a deterministic company fixture."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(id=DEV_WORKSPACE_ID, name="Discovery WS", slug="discovery-ws")
    )
    return await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Example Company",
            normalized_name="example company",
            tax_id="0312345678",
            status="published",
        )
    )


@pytest.mark.asyncio
async def test_discovery_canonicalizes_and_merges_all_local_candidate_origins(
    db_session: AsyncSession,
) -> None:
    """Official, manual, sitemap, internal, search, and trusted inputs are deduplicated."""
    company = await _company(db_session)
    service = SourceDiscoveryService(
        db_session,
        search_provider=FixtureSearchProvider(),
        trusted_registry=vietnam_source_registry(),
    )

    result = await service.discover(
        company,
        {
            "website_url": "https://EXAMPLE.vn/",
            "verified_official_domain": "example.vn",
            "manual_urls": [
                "https://example.vn/",
                "https://example.vn/about/",
                "https://manual.example.vn/",
            ],
            "sitemap_urls": ["https://example.vn/about"],
            "internal_links": ["https://example.vn/about"],
            "include_search_results": True,
            "trusted_source_results": {
                "wikipedia": {
                    "outcome": "success",
                    "candidates": [
                        {
                            "url": "https://en.wikipedia.org/wiki/Example_Company",
                            "title": "Example Company",
                            "snippet": "Example Company overview and history",
                        }
                    ],
                }
            },
        },
    )

    by_url = {candidate.normalized_url: candidate for candidate in result.candidates}
    assert "https://example.vn" in by_url
    assert by_url["https://example.vn"].provenance == [
        "official_website",
        "verified_official_domain",
        "manual_url",
    ]
    assert "https://example.vn/about" in by_url
    assert "sitemap" in by_url["https://example.vn/about"].provenance
    assert "internal_link" in by_url["https://example.vn/about"].provenance
    assert "https://en.wikipedia.org/wiki/Example_Company" in by_url

    outcomes = {item.provider: item.outcome for item in result.provider_outcomes}
    assert outcomes["wikipedia"] == ProviderOutcome.SUCCESS
    assert outcomes["dangkykinhdoanh"] == ProviderOutcome.MANUAL_REQUIRED
    assert len(result.candidates) == len(by_url)


@pytest.mark.asyncio
async def test_trusted_registry_is_extensible_and_blocked_payload_has_no_fake_candidate(
    db_session: AsyncSession,
) -> None:
    """A new provider is registered through configuration, and blocked data stays empty."""
    company = await _company(db_session)
    registry = CountrySourceRegistry.for_country("VN")
    assert len(registry.providers) == 5
    assert {provider.definition.domain for provider in registry.providers} == {
        "dangkykinhdoanh.gov.vn",
        "tracuunnt.gdt.gov.vn",
        "wikipedia.org",
        "finance.vietstock.vn",
        "cafef.vn",
    }
    registry.register(CustomTrustedProvider())
    service = SourceDiscoveryService(db_session, trusted_registry=registry)

    result = await service.discover(
        company,
        {
            "trusted_source_results": {
                "dangkykinhdoanh": {
                    "outcome": "blocked",
                    "reason": "ROBOTS_DISALLOWED",
                }
            }
        },
    )

    outcomes = {item.provider: item for item in result.provider_outcomes}
    assert outcomes["dangkykinhdoanh"].outcome == ProviderOutcome.BLOCKED
    assert outcomes["dangkykinhdoanh"].reason == "ROBOTS_DISALLOWED"
    assert outcomes["companies_house"].outcome == ProviderOutcome.SUCCESS
    assert any(candidate.provider == "companies_house" for candidate in result.candidates)
    assert not any("dangkykinhdoanh.gov.vn" in candidate.url for candidate in result.candidates)


@pytest.mark.asyncio
async def test_source_history_and_field_authority_survive_selection(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """History is reused and Vietnam provider authority remains field-specific."""
    monkeypatch.setattr(
        "company_profile.modules.sources.discovery.validate_url_safety",
        lambda _url: (True, "SAFE"),
    )
    company = await _company(db_session)
    history = Source(
        workspace_id=company.workspace_id,
        company_id=company.id,
        canonical_url="https://history.example.vn/profile/",
        normalized_url="https://history.example.vn/profile",
        domain="history.example.vn",
        source_type="official_site",
        authority_tier=2,
        authority_by_field={"overview.description": 2, "identity.legal_name": 4},
        discovery_provenance=["official_website"],
        discovered_via="official_website",
        entity_match_score=1.0,
        status="discovered",
    )
    db_session.add(history)
    await db_session.flush()

    service = SourceDiscoveryService(db_session, trusted_registry=vietnam_source_registry())
    result = await service.discover(
        company,
        {
            "trusted_source_results": {
                "dangkykinhdoanh": {
                    "outcome": "success",
                    "candidates": [
                        {
                            "url": "https://dangkykinhdoanh.gov.vn/company/123",
                            "entity_match_score": 1.0,
                        }
                    ],
                },
                "wikipedia": {
                    "outcome": "success",
                    "candidates": [
                        {
                            "url": "https://en.wikipedia.org/wiki/Example_Company",
                            "title": "Example Company",
                            "snippet": "Example Company overview",
                        }
                    ],
                },
            }
        },
    )

    history_candidate = next(
        candidate
        for candidate in result.candidates
        if candidate.normalized_url == "https://history.example.vn/profile"
    )
    assert history_candidate.selection_reason == "source_history"
    assert "source_history" in history_candidate.provenance

    selection = await service.select_sources(company, result.candidates)
    assert selection.selected
    sources = (await db_session.execute(select(Source))).scalars().all()
    government = next(source for source in sources if "dangkykinhdoanh.gov.vn" in source.domain)
    wikipedia = next(source for source in sources if source.domain == "en.wikipedia.org")
    assert government.authority_for_field("identity.legal_name") == 1
    assert wikipedia.authority_for_field("identity.legal_name") == 4
    assert government.authority_for_field("identity.legal_name") < wikipedia.authority_for_field(
        "identity.legal_name"
    )
    assert government.selection_reason == "trusted_provider"
    assert wikipedia.selection_reason == "trusted_provider"


@pytest.mark.asyncio
async def test_rejected_candidate_persists_reason_and_provenance(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate rejected by deterministic entity policy remains auditable."""
    monkeypatch.setattr(
        "company_profile.modules.sources.discovery.validate_url_safety",
        lambda _url: (True, "SAFE"),
    )
    company = await _company(db_session)
    service = SourceDiscoveryService(db_session, trusted_registry=CountrySourceRegistry("VN"))
    candidate = SourceDiscoveryCandidate(
        url="https://unrelated.example.vn/profile",
        discovered_via="search_provider",
        provider="search_provider",
        title="Unrelated organisation",
        snippet="A different legal entity",
    )

    selection = await service.select_sources(company, [candidate])

    assert selection.selected == []
    assert selection.rejected == [
        {
            "url": "https://unrelated.example.vn/profile",
            "reason": "LOW_ENTITY_MATCH:0.0",
        }
    ]
    source = (
        await db_session.execute(
            select(Source).where(Source.normalized_url == "https://unrelated.example.vn/profile")
        )
    ).scalar_one()
    assert source.status == "rejected"
    assert source.discovered_via == "search_provider"
    assert source.provider == "search_provider"
    assert source.rejection_reason == "LOW_ENTITY_MATCH:0.0"
    assert source.selection_reason == "entity_match"
