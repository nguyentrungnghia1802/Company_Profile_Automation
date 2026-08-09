"""Acceptance tests for bounded official website and search discovery."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from sqlalchemy import select

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.research import ResearchJob
from company_profile.db.models.search import ResearchQuery, SearchResult
from company_profile.integrations.search.fixture_search import SearchResultItem
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.sources.discovery import SourceDiscoveryService
from company_profile.modules.sources.official_discovery import (
    OfficialWebsiteDiscovery,
    WebsiteFetchResponse,
)
from company_profile.modules.sources.ranking import classify_and_rank_url
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession


class FixtureWebsiteFetcher:
    """In-memory public website fixture with a complete request audit."""

    def __init__(self, responses: Mapping[str, WebsiteFetchResponse]) -> None:
        self.responses = dict(responses)
        self.calls: list[str] = []

    async def fetch(self, url: str) -> WebsiteFetchResponse:
        """Return a deterministic response without live network access."""
        self.calls.append(url)
        return self.responses.get(
            url,
            WebsiteFetchResponse(url, url, 404, content="", content_type="text/plain"),
        )


class RecordingSearchProvider:
    """Provider-neutral search double that records generated query templates."""

    provider_name = "fixture-recording"

    def __init__(self, results: list[SearchResultItem]) -> None:
        self.results = results
        self.queries: list[tuple[str, dict[str, Any]]] = []

    async def search(self, query: str, **kwargs: Any) -> list[SearchResultItem]:
        """Return metadata while retaining query/provider call details."""
        self.queries.append((query, kwargs))
        return self.results


def _website_fixture() -> tuple[FixtureWebsiteFetcher, OfficialWebsiteDiscovery]:
    """Create a robots/homepage/sitemap fixture with irrelevant and external links."""
    root = "https://fixture.example"
    sitemap = f"{root}/sitemap.xml"
    sitemap_urls = "".join(
        f"<url><loc>{root}/news/story-{index}</loc></url>" for index in range(50)
    )
    fetcher = FixtureWebsiteFetcher(
        {
            f"{root}/robots.txt": WebsiteFetchResponse(
                f"{root}/robots.txt",
                f"{root}/robots.txt",
                200,
                content=(f"User-agent: *\nAllow: /\nDisallow: /login\nSitemap: {sitemap}\n"),
                content_type="text/plain",
            ),
            root: WebsiteFetchResponse(
                root,
                root,
                200,
                content=(
                    '<html><head><link rel="canonical" href="https://fixture.example/" /></head>'
                    "<body>"
                    '<a href="/about-us/">About company history</a>'
                    '<a href="/san-pham/?utm_source=fixture">Sản phẩm</a>'
                    '<a href="/login">Login</a>'
                    '<a href="https://other.example/">External</a>'
                    "</body></html>"
                ),
            ),
            f"{root}/about-us": WebsiteFetchResponse(
                f"{root}/about-us",
                f"{root}/about-us",
                200,
                content="<html><body><h1>About</h1></body></html>",
            ),
            f"{root}/san-pham": WebsiteFetchResponse(
                f"{root}/san-pham",
                f"{root}/san-pham",
                200,
                content="<html><body><h1>Products</h1></body></html>",
            ),
            sitemap: WebsiteFetchResponse(
                sitemap,
                sitemap,
                200,
                content=f"<urlset>{sitemap_urls}</urlset>",
                content_type="application/xml",
            ),
        }
    )
    return fetcher, OfficialWebsiteDiscovery(
        fetcher,
        user_agent="VCPS-Bot/0.1",
        max_depth=1,
        max_pages_per_domain=4,
        max_pages_per_job=4,
        max_sitemaps=1,
        max_sitemap_urls=5,
    )


async def _company(db_session: AsyncSession) -> CompanyProfile:
    """Create a stable company fixture for discovery persistence tests."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(id=DEV_WORKSPACE_ID, name="Official Discovery WS", slug="official-discovery-ws")
    )
    return await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Example Company",
            normalized_name="example company",
            tax_id="0312345678",
            registration_number="REG-123",
            status="published",
        )
    )


def test_url_ranking_supports_multilingual_groups_and_excludes_sensitive_paths() -> None:
    """Vietnamese/English tokens rank pages without an exact-path allowlist."""
    about = classify_and_rank_url(
        "https://fixture.example/ve-chung-toi/lich-su",
        title="Giới thiệu và lịch sử công ty",
        official_domain="fixture.example",
        discovered_via="internal_link",
    )
    excluded = classify_and_rank_url("https://fixture.example/account/privacy?next=/cart")

    assert about.page_group == "about_company_history"
    assert about.relevance_score > 0.5
    assert excluded.excluded is True
    assert excluded.relevance_score == 0.0
    assert "account" in excluded.reason


@pytest.mark.asyncio
async def test_official_discovery_is_robots_aware_canonical_and_bounded() -> None:
    """Homepage links and sitemap URLs are safe, deduplicated, and budgeted."""
    fetcher, discovery = _website_fixture()

    result = await discovery.discover("https://FIXTURE.example/")
    urls = {candidate.normalized_url for candidate in result.candidates}

    assert result.robots is not None
    assert result.robots.decision == "allowed"
    assert result.sitemap_documents_fetched == 1
    assert result.pages_fetched <= 4
    assert len(result.candidates) <= 4
    assert "https://fixture.example" in urls
    assert "https://fixture.example/about-us" in urls
    assert "https://fixture.example/san-pham" in urls
    assert not any("login" in url or "other.example" in url for url in urls)
    assert all("utm_" not in url for url in urls)
    assert fetcher.calls.count("https://fixture.example/robots.txt") == 1


@pytest.mark.asyncio
async def test_robots_disallow_stops_homepage_and_sitemap_fetch() -> None:
    """A disallow decision fails closed before any page or sitemap retrieval."""
    root = "https://blocked.example"
    fetcher = FixtureWebsiteFetcher(
        {
            f"{root}/robots.txt": WebsiteFetchResponse(
                f"{root}/robots.txt",
                f"{root}/robots.txt",
                200,
                content="User-agent: *\nDisallow: /\n",
            )
        }
    )
    discovery = OfficialWebsiteDiscovery(fetcher)

    result = await discovery.discover(root)

    assert result.robots is not None
    assert result.robots.decision == "blocked"
    assert result.candidates == []
    assert fetcher.calls == [f"{root}/robots.txt"]


@pytest.mark.asyncio
async def test_robots_404_means_not_published_and_allows_homepage() -> None:
    """A missing robots file is not evidence that the site blocks crawlers."""
    root = "https://no-robots.example"
    fetcher = FixtureWebsiteFetcher(
        {
            f"{root}/robots.txt": WebsiteFetchResponse(
                f"{root}/robots.txt", f"{root}/robots.txt", 404
            ),
            root: WebsiteFetchResponse(root, root, 200, content="<h1>Public page</h1>"),
        }
    )

    result = await OfficialWebsiteDiscovery(fetcher, max_depth=0).discover(root)

    assert result.robots is not None
    assert result.robots.decision == "allowed"
    assert result.robots.reason == "ROBOTS_NOT_PUBLISHED_HTTP_404"
    assert root in fetcher.calls
    assert result.candidates


@pytest.mark.asyncio
async def test_robots_server_failure_is_unavailable_not_access_blocked() -> None:
    """A transient robots failure fails closed without claiming an explicit block."""
    root = "https://robots-down.example"
    fetcher = FixtureWebsiteFetcher(
        {
            f"{root}/robots.txt": WebsiteFetchResponse(
                f"{root}/robots.txt", f"{root}/robots.txt", 503
            )
        }
    )

    result = await OfficialWebsiteDiscovery(fetcher).discover(root)

    assert result.robots is not None
    assert result.robots.decision == "unknown"
    assert result.robots.reason == "ROBOTS_UNAVAILABLE_HTTP_503"
    assert result.candidates == []
    assert fetcher.calls == [f"{root}/robots.txt"]


@pytest.mark.asyncio
async def test_website_without_search_provider_still_discovers_public_pages() -> None:
    """Official discovery is independent from AI and SearchProvider availability."""
    _fetcher, discovery = _website_fixture()
    result = await discovery.discover("https://fixture.example")

    assert result.candidates
    assert result.robots is not None


@pytest.mark.asyncio
async def test_search_queries_and_results_are_deterministic_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Queries contain canonical identity signals and results remain metadata only."""
    company = await _company(db_session)
    job = ResearchJob(
        workspace_id=company.workspace_id,
        company_id=company.id,
        scope="{}",
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()
    provider = RecordingSearchProvider(
        [
            SearchResultItem(
                title="Example Company",
                url="https://same-name.example/about",
                snippet="Example Company overview in another market",
                domain="same-name.example",
            ),
            SearchResultItem(
                title="Example Company official",
                url="https://example.vn/about",
                snippet="Example Company tax 0312345678",
                domain="example.vn",
                timestamp=datetime(2026, 8, 8, tzinfo=UTC),
            ),
        ]
    )
    service = SourceDiscoveryService(db_session, search_provider=provider)

    result = await service.discover(
        company,
        {
            "include_search_results": True,
            "country": "Vietnam",
            "website_url": "https://example.vn",
            "requested_sections": ["about", "annual_reports"],
        },
        research_job_id=job.id,
    )

    query_rows = (await db_session.execute(select(ResearchQuery))).scalars().all()
    search_rows = (await db_session.execute(select(SearchResult))).scalars().all()
    assert len(query_rows) == 4
    assert len(search_rows) == 8
    assert any("Example Company" in query.query_text for query in query_rows)
    assert any("Vietnam" in query.query_text for query in query_rows)
    assert any("site:example.vn" in query.query_text for query in query_rows)
    assert {query.language_code for query in query_rows} == {"vi", "en"}
    assert all(row.provider == "fixture-recording" for row in search_rows)
    assert all(row.title and row.snippet and row.result_timestamp for row in search_rows)
    same_name = [row for row in search_rows if "same-name.example" in row.normalized_url]
    assert same_name
    assert {row.selection_status for row in same_name} == {"review"}
    assert all("ENTITY_MATCH_REVIEW_REQUIRED" in row.selection_reason for row in same_name)
    assert result.search_queries
    assert len(provider.queries) == 4
    selection = await service.select_sources(company, result.candidates)
    assert any(
        "same-name.example" in item["url"] and item["reason"] == "ENTITY_MATCH_REVIEW_REQUIRED"
        for item in selection.rejected
    )
