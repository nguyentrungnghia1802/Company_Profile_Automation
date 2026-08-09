"""Bounded, robots-aware official website discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from company_profile.modules.sources.ranking import (
    classify_and_rank_url,
    normalize_domain,
)
from company_profile.modules.sources.validator import validate_url_safety

if TYPE_CHECKING:
    from collections.abc import Mapping

    from company_profile.modules.sources.discovery import SourceDiscoveryCandidate


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "dclid", "msclkid"}


@dataclass(frozen=True, slots=True)
class WebsiteFetchResponse:
    """Small provider-neutral response used by website discovery."""

    requested_url: str
    final_url: str
    status_code: int
    content: str = ""
    content_type: str = "text/html"
    error: str | None = None


class WebsiteFetchProvider(Protocol):
    """Public HTTP/fixture provider boundary for discovery-only fetches."""

    async def fetch(self, url: str) -> WebsiteFetchResponse:
        """Fetch one public URL without turning content into evidence."""


@dataclass(frozen=True, slots=True)
class RobotsDecision:
    """Recorded robots policy decision for one official domain."""

    status_code: int | None
    decision: str
    reason: str
    sitemap_urls: tuple[str, ...] = ()


@dataclass(slots=True)
class OfficialWebsiteDiscoveryResult:
    """Bounded discovery output and policy/audit metadata."""

    candidates: list[SourceDiscoveryCandidate] = field(default_factory=list)
    robots: RobotsDecision | None = None
    fetched_urls: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pages_fetched: int = 0
    sitemap_documents_fetched: int = 0


class _HomepageLinkParser(HTMLParser):
    """Extract anchor links and same-document canonical metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.canonical_urls: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._anchor_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a" and self._anchor_href is None:
            self._anchor_href = attributes.get("href", "")
            self._anchor_text = []
            self._anchor_depth = 1
        elif self._anchor_href is not None:
            self._anchor_depth += 1
        if tag.lower() == "link" and "canonical" in attributes.get("rel", "").lower():
            canonical = attributes.get("href", "").strip()
            if canonical:
                self.canonical_urls.append(canonical)

    def handle_data(self, data: str) -> None:
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._anchor_href is None:
            return
        if tag.lower() == "a":
            href = self._anchor_href
            label = " ".join("".join(self._anchor_text).split())
            self.links.append((href, label))
            self._anchor_href = None
            self._anchor_text = []
            self._anchor_depth = 0
        elif self._anchor_depth > 0:
            self._anchor_depth -= 1


def canonicalize_discovery_url(url: str, *, base_url: str | None = None) -> str:
    """Resolve and canonicalize a public discovery URL.

    Fragments and common analytics parameters are removed, while meaningful
    query parameters remain part of the URL identity.
    """
    candidate = urljoin(base_url or "", url.strip())
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not any(key.lower().startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)
    ]
    netloc = parsed.hostname.lower().rstrip(".")
    if parsed.port is not None and not (
        (parsed.scheme.lower() == "http" and parsed.port == 80)
        or (parsed.scheme.lower() == "https" and parsed.port == 443)
    ):
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path or ""
    path = "" if path == "/" else path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            path,
            "",
            urlencode(query_pairs, doseq=True),
            "",
        )
    )


def _extract_sitemap_locations(content: str, *, limit: int) -> list[str]:
    """Read bounded ``loc`` values without resolving external XML entities."""
    if limit <= 0:
        return []
    locations = re.findall(r"<loc\b[^>]*>(.*?)</loc\s*>", content, flags=re.IGNORECASE | re.DOTALL)
    return [unescape(value).strip() for value in locations[:limit] if value.strip()]


class OfficialWebsiteDiscovery:
    """Discover an official site with explicit depth and page budgets."""

    def __init__(
        self,
        fetcher: WebsiteFetchProvider,
        *,
        user_agent: str = "VCPS-Bot/0.1",
        max_response_bytes: int = 10_000_000,
        max_depth: int = 1,
        max_pages_per_domain: int = 25,
        max_pages_per_job: int = 50,
        max_sitemaps: int = 3,
        max_sitemap_urls: int = 100,
    ) -> None:
        self.fetcher = fetcher
        self.user_agent = user_agent
        self.max_response_bytes = max_response_bytes
        self.max_depth = max_depth
        self.max_pages_per_domain = max_pages_per_domain
        self.max_pages_per_job = max_pages_per_job
        self.max_sitemaps = max_sitemaps
        self.max_sitemap_urls = max_sitemap_urls

    async def discover(
        self,
        website_url: str,
        *,
        scope: Mapping[str, object] | None = None,
    ) -> OfficialWebsiteDiscoveryResult:
        """Fetch robots/homepage and return bounded canonical candidates."""
        options = scope or {}
        root_url = canonicalize_discovery_url(website_url)
        result = OfficialWebsiteDiscoveryResult()
        if not root_url:
            result.warnings.append("OFFICIAL_WEBSITE_INVALID_URL")
            return result
        safe, safety_reason = validate_url_safety(root_url)
        if not safe:
            result.warnings.append(f"OFFICIAL_WEBSITE_UNSAFE:{safety_reason}")
            return result

        official_domain = normalize_domain(urlparse(root_url).hostname or "")
        origin = f"{urlparse(root_url).scheme}://{urlparse(root_url).netloc}"
        robots_url = canonicalize_discovery_url(f"{origin}/robots.txt")
        robots_response = await self._fetch(robots_url, result)
        robots_parser, robots_decision = self._robots_policy(robots_url, robots_response, root_url)
        result.robots = robots_decision
        if robots_decision.decision != "allowed":
            result.warnings.append(
                f"ROBOTS_{robots_decision.decision.upper()}:{robots_decision.reason}"
            )
            return result

        max_depth = self._budget(options, "crawl_depth", self.max_depth, minimum=0, maximum=5)
        max_pages = min(
            self._budget(
                options,
                "max_pages_per_domain",
                self.max_pages_per_domain,
                minimum=1,
                maximum=500,
            ),
            self._budget(
                options,
                "max_pages_per_job",
                self.max_pages_per_job,
                minimum=1,
                maximum=500,
            ),
        )
        max_sitemaps = self._budget(options, "max_sitemaps", self.max_sitemaps, 0, 20)
        max_sitemap_urls = self._budget(options, "max_sitemap_urls", self.max_sitemap_urls, 0, 1000)
        candidates: dict[str, SourceDiscoveryCandidate] = {}
        page_queue: list[tuple[str, int, str]] = [(root_url, 0, "official_website")]
        queued: set[str] = {root_url}
        fetched_pages: set[str] = set()

        while page_queue and len(fetched_pages) < max_pages:
            page_url, depth, discovered_via = page_queue.pop(0)
            if page_url in fetched_pages or depth > max_depth:
                continue
            if not self._allowed_by_robots(robots_parser, page_url):
                result.warnings.append(f"ROBOTS_DISALLOWED:{page_url}")
                continue
            if normalize_domain(urlparse(page_url).hostname or "") != official_domain:
                continue
            self._add_candidate(
                candidates,
                page_url,
                discovered_via=discovered_via,
                depth=depth,
                official_domain=official_domain,
            )
            response = await self._fetch(page_url, result)
            fetched_pages.add(page_url)
            result.pages_fetched += 1
            if response.status_code != 200 or response.error:
                result.warnings.append(
                    f"WEBSITE_PAGE_UNAVAILABLE:{page_url}:{response.status_code or response.error}"
                )
                continue
            final_url = canonicalize_discovery_url(response.final_url or page_url)
            if (
                not final_url
                or normalize_domain(urlparse(final_url).hostname or "") != official_domain
            ):
                result.warnings.append(f"REDIRECT_OUTSIDE_OFFICIAL_DOMAIN:{page_url}")
                continue
            if depth == 0 or depth < max_depth:
                self._extract_homepage_links(
                    response.content,
                    final_url,
                    official_domain,
                    robots_parser,
                    max_depth,
                    depth,
                    page_queue,
                    queued,
                    candidates,
                )

        sitemap_urls = list(robots_decision.sitemap_urls)
        default_sitemap = canonicalize_discovery_url(f"{origin}/sitemap.xml")
        if default_sitemap and default_sitemap not in sitemap_urls:
            sitemap_urls.append(default_sitemap)
        sitemap_queue = [
            canonicalize_discovery_url(value, base_url=origin) for value in sitemap_urls
        ]
        sitemap_queue = [
            value
            for value in dict.fromkeys(sitemap_queue)
            if value and normalize_domain(urlparse(value).hostname or "") == official_domain
        ]
        sitemap_locations_seen: set[str] = set()
        sitemap_documents = 0
        while sitemap_queue and sitemap_documents < max_sitemaps:
            sitemap_url = sitemap_queue.pop(0)
            if sitemap_url in sitemap_locations_seen or not self._allowed_by_robots(
                robots_parser, sitemap_url
            ):
                continue
            sitemap_locations_seen.add(sitemap_url)
            response = await self._fetch(sitemap_url, result)
            sitemap_documents += 1
            result.sitemap_documents_fetched += 1
            if response.status_code != 200 or response.error:
                result.warnings.append(
                    f"SITEMAP_UNAVAILABLE:{sitemap_url}:{response.status_code or response.error}"
                )
                continue
            locations = _extract_sitemap_locations(response.content, limit=max_sitemap_urls)
            is_index = "<sitemapindex" in response.content.lower()
            for location in locations:
                canonical = canonicalize_discovery_url(location, base_url=origin)
                if not canonical or canonical in sitemap_locations_seen:
                    continue
                if normalize_domain(urlparse(canonical).hostname or "") != official_domain:
                    continue
                if canonical.lower().endswith((".xml", ".xml.gz")) or is_index:
                    if len(sitemap_queue) + sitemap_documents < max_sitemaps:
                        sitemap_queue.append(canonical)
                    continue
                if len(candidates) >= max_pages:
                    break
                if self._allowed_by_robots(robots_parser, canonical):
                    self._add_candidate(
                        candidates,
                        canonical,
                        discovered_via="sitemap",
                        depth=1,
                        official_domain=official_domain,
                    )
        result.candidates = sorted(
            candidates.values(),
            key=lambda candidate: (
                -(candidate.relevance_score or 0.0),
                candidate.crawl_depth,
                candidate.normalized_url,
            ),
        )[:max_pages]
        return result

    async def _fetch(
        self,
        url: str,
        result: OfficialWebsiteDiscoveryResult,
    ) -> WebsiteFetchResponse:
        """Apply an SSRF check before every provider call."""
        safe, reason = validate_url_safety(url)
        if not safe:
            return WebsiteFetchResponse(url, url, 400, error=f"SSRF_BLOCKED:{reason}")
        result.fetched_urls.append(url)
        try:
            response = await self.fetcher.fetch(url)
        except Exception as exc:  # discovery is non-critical and auditable
            return WebsiteFetchResponse(url, url, 0, error=type(exc).__name__)
        if response.final_url:
            final_safe, final_reason = validate_url_safety(response.final_url)
            if not final_safe:
                return WebsiteFetchResponse(
                    response.requested_url,
                    response.final_url,
                    400,
                    error=f"SSRF_REDIRECT_BLOCKED:{final_reason}",
                )
        if len(response.content.encode("utf-8")) > self.max_response_bytes:
            return WebsiteFetchResponse(
                response.requested_url,
                response.final_url,
                413,
                error="SIZE_EXCEEDED",
            )
        return response

    def _robots_policy(
        self,
        robots_url: str,
        response: WebsiteFetchResponse,
        homepage_url: str,
    ) -> tuple[RobotFileParser, RobotsDecision]:
        """Convert robots response into an explicit fail-closed decision."""
        parser = RobotFileParser(robots_url)
        if response.error:
            return parser, RobotsDecision(None, "unknown", response.error)
        if response.status_code in {401, 403}:
            return parser, RobotsDecision(
                response.status_code,
                "blocked",
                f"ROBOTS_ACCESS_CONTROL_HTTP_{response.status_code}",
            )
        if 400 <= response.status_code < 500:
            parser.parse([])
            return parser, RobotsDecision(
                response.status_code,
                "allowed",
                f"ROBOTS_NOT_PUBLISHED_HTTP_{response.status_code}",
            )
        if response.status_code != 200:
            return parser, RobotsDecision(
                response.status_code,
                "unknown",
                f"ROBOTS_UNAVAILABLE_HTTP_{response.status_code}",
            )
        parser.parse(response.content.splitlines())
        sitemap_urls = tuple(parser.site_maps() or ())
        if not parser.can_fetch(self.user_agent, homepage_url):
            return parser, RobotsDecision(200, "blocked", "ROBOTS_DISALLOWED", sitemap_urls)
        return parser, RobotsDecision(200, "allowed", "ROBOTS_ALLOWED", sitemap_urls)

    def _extract_homepage_links(
        self,
        content: str,
        base_url: str,
        official_domain: str,
        robots_parser: RobotFileParser,
        max_depth: int,
        depth: int,
        page_queue: list[tuple[str, int, str]],
        queued: set[str],
        candidates: dict[str, SourceDiscoveryCandidate],
    ) -> None:
        """Extract only same-domain HTTP links and canonical metadata."""
        parser = _HomepageLinkParser()
        try:
            parser.feed(content)
        except Exception:
            return
        for canonical_href in parser.canonical_urls:
            canonical = self._same_domain_url(
                canonical_href, base_url, official_domain, robots_parser
            )
            if canonical:
                self._add_candidate(
                    candidates,
                    canonical,
                    discovered_via="official_website",
                    depth=depth,
                    official_domain=official_domain,
                    selection_reason="homepage_canonical",
                )
        if depth >= max_depth:
            return
        for href, label in parser.links:
            canonical = self._same_domain_url(href, base_url, official_domain, robots_parser)
            if not canonical:
                continue
            self._add_candidate(
                candidates,
                canonical,
                discovered_via="internal_link",
                depth=depth + 1,
                official_domain=official_domain,
                title=label,
            )
            if canonical not in queued:
                queued.add(canonical)
                page_queue.append((canonical, depth + 1, "internal_link"))

    def _same_domain_url(
        self,
        raw_url: str,
        base_url: str,
        official_domain: str,
        robots_parser: RobotFileParser,
    ) -> str:
        """Resolve one link and enforce scheme, host, and robots policy."""
        canonical = canonicalize_discovery_url(raw_url, base_url=base_url)
        if not canonical:
            return ""
        safe, _ = validate_url_safety(canonical)
        if not safe or normalize_domain(urlparse(canonical).hostname or "") != official_domain:
            return ""
        return canonical if robots_parser.can_fetch(self.user_agent, canonical) else ""

    def _add_candidate(
        self,
        candidates: dict[str, SourceDiscoveryCandidate],
        url: str,
        *,
        discovered_via: str,
        depth: int,
        official_domain: str,
        title: str = "",
        selection_reason: str | None = None,
    ) -> None:
        """Create one candidate while merging canonical duplicates."""
        canonical = canonicalize_discovery_url(url)
        if not canonical:
            return
        ranking = classify_and_rank_url(
            canonical,
            title=title,
            official_domain=official_domain,
            discovered_via=discovered_via,
            crawl_depth=depth,
        )
        if ranking.excluded:
            return
        from company_profile.modules.sources.discovery import SourceDiscoveryCandidate

        candidate = SourceDiscoveryCandidate(
            url=canonical,
            discovered_via=discovered_via,
            source_type="official_site",
            entity_match_score=1.0,
            title=title,
            provided=True,
            selection_reason=selection_reason
            or (
                "provided_url"
                if discovered_via == "official_website" and depth == 0
                else ranking.reason
            ),
            normalized_url=canonical,
            relevance_score=ranking.relevance_score,
            crawl_depth=depth,
            page_group=ranking.page_group,
        )
        existing = candidates.get(canonical)
        if existing is None or candidate.relevance_score > existing.relevance_score:
            candidates[canonical] = candidate

    def _allowed_by_robots(self, parser: RobotFileParser, url: str) -> bool:
        """Use the configured bot identity consistently for every URL."""
        return parser.can_fetch(self.user_agent, url)

    @staticmethod
    def _budget(
        scope: Mapping[str, object],
        key: str,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        """Read an integer budget and clamp unsafe/unbounded caller input."""
        value = scope.get(key, default)
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = int(value)
            except ValueError:
                parsed = default
        else:
            parsed = default
        return max(minimum, min(maximum, parsed))
