"""Country-configured trusted source providers and extensible registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlencode, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from company_profile.config.settings import Settings, get_settings
from company_profile.integrations.fetch.http_transport import (
    SecureHttpTransport,
    TransportFailure,
    TransportFailureCode,
    TransportResponse,
)
from company_profile.modules.sources.discovery import (
    ProviderOutcome,
    SourceDiscoveryCandidate,
    TrustedSourceDefinition,
    TrustedSourceLookup,
    TrustedSourceProvider,
)
from company_profile.modules.sources.policy import calculate_entity_match_score

if TYPE_CHECKING:
    from collections.abc import Mapping

    from company_profile.db.models.company import CompanyProfile


class ConfiguredTrustedSourceProvider:
    """Adapter for a configured structured/public response supplied by an integration.

    The default adapter deliberately performs no live scraping. A real adapter must
    provide a public structured response or an explicit URL and must enforce the
    source's robots, terms, and access controls before returning candidates.
    """

    def __init__(
        self,
        definition: TrustedSourceDefinition,
        *,
        live_provider: TrustedSourceProvider | None = None,
        manual_reason: str = "NO_STRUCTURED_PROVIDER_RESULT",
    ) -> None:
        self.definition = definition
        self.live_provider = live_provider
        self.manual_reason = manual_reason

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Read only an explicit structured result; never invent a source URL."""
        payload = scope.get("trusted_source_results") or scope.get("trusted_sources")
        raw = None
        if isinstance(payload, dict):
            raw = payload.get(self.definition.key) or payload.get(self.definition.provider_type)
        if raw is None:
            if self.live_provider is not None:
                return await self.live_provider.discover(company=company, scope=scope)
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.MANUAL_REQUIRED,
                reason=self.manual_reason,
            )

        if isinstance(raw, dict):
            outcome_name = str(raw.get("outcome", "success")).strip().lower()
            raw_candidates = raw.get("candidates") or raw.get("urls") or []
            reason = str(raw.get("reason", ""))
        elif isinstance(raw, list):
            outcome_name = "success"
            raw_candidates = raw
            reason = ""
        else:
            outcome_name = "unavailable"
            raw_candidates = []
            reason = "INVALID_STRUCTURED_PROVIDER_RESULT"

        try:
            outcome = ProviderOutcome(outcome_name)
        except ValueError:
            outcome = ProviderOutcome.UNAVAILABLE
            reason = "INVALID_PROVIDER_OUTCOME"

        if outcome != ProviderOutcome.SUCCESS:
            return TrustedSourceLookup(self.definition.key, outcome, reason=reason)

        candidates: list[SourceDiscoveryCandidate] = []
        for item in raw_candidates if isinstance(raw_candidates, list) else []:
            url, title, snippet, match_score = self._candidate_values(item)
            if not self._allowed_domain(url):
                continue
            candidates.append(
                SourceDiscoveryCandidate(
                    url=url,
                    discovered_via="trusted_provider",
                    provider=self.definition.key,
                    source_type=self.definition.source_type,
                    authority_tier=self.definition.default_authority_tier,
                    authority_by_field=dict(self.definition.authority_by_field),
                    entity_match_score=match_score,
                    title=title,
                    snippet=snippet,
                )
            )

        if not candidates:
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.NOT_FOUND,
                reason=reason or "NO_ALLOWED_MATCHING_SOURCE",
            )
        return TrustedSourceLookup(
            self.definition.key,
            ProviderOutcome.SUCCESS,
            candidates=tuple(candidates),
            reason=reason,
        )

    def _allowed_domain(self, url: str) -> bool:
        """Reject provider payloads that point outside the configured source domain."""
        return _allowed_provider_domain(self.definition, url)

    @staticmethod
    def _candidate_values(item: Any) -> tuple[str, str, str, float | None]:
        """Extract only explicit URL and metadata values from a structured payload."""
        if isinstance(item, str):
            return item.strip(), "", "", None
        if not isinstance(item, dict):
            return "", "", "", None
        raw_score = item.get("entity_match_score")
        score = float(raw_score) if isinstance(raw_score, (int, float)) else None
        return (
            str(item.get("url", "")).strip(),
            str(item.get("title", "")),
            str(item.get("snippet", "")),
            score,
        )


class TrustedHttpTransport(Protocol):
    """Minimal safe transport boundary consumed by live trusted providers."""

    async def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> TransportResponse | TransportFailure:
        """Fetch one SSRF-validated URL without following redirects."""


class WikipediaTrustedSourceProvider:
    """Discover bounded article candidates through the official MediaWiki API."""

    def __init__(
        self,
        definition: TrustedSourceDefinition,
        transport: TrustedHttpTransport,
        *,
        user_agent: str,
    ) -> None:
        self.definition = definition
        self.transport = transport
        self.user_agent = user_agent

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Query public structured page metadata and retain response-provided URLs only."""
        locale = str(scope.get("locale") or scope.get("requested_locale") or "vi").lower()
        language = "en" if locale.startswith("en") else "vi"
        query = (company.legal_name or company.company_name).strip()
        if not query:
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.NOT_FOUND,
                reason="COMPANY_NAME_MISSING",
            )
        params = urlencode(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": "0",
                "gsrlimit": "5",
                "prop": "info|description",
                "inprop": "url",
                "format": "json",
                "formatversion": "2",
            }
        )
        api_url = f"https://{language}.wikipedia.org/w/api.php?{params}"
        response = await _get_with_safe_redirects(
            self.transport,
            api_url,
            user_agent=self.user_agent,
        )
        failure = _provider_failure(self.definition.key, response)
        if failure is not None:
            return failure
        assert isinstance(response, TransportResponse)
        try:
            payload = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.UNAVAILABLE,
                reason="INVALID_STRUCTURED_RESPONSE",
            )

        pages = payload.get("query", {}).get("pages", []) if isinstance(payload, dict) else []
        candidates: list[SourceDiscoveryCandidate] = []
        for page in pages if isinstance(pages, list) else []:
            if not isinstance(page, dict):
                continue
            url = str(page.get("canonicalurl") or page.get("fullurl") or "").strip()
            if not _allowed_provider_domain(self.definition, url):
                continue
            title = str(page.get("title") or "").strip()
            description = str(page.get("description") or "").strip()
            candidates.append(
                _trusted_candidate(
                    self.definition,
                    url=url,
                    title=title,
                    snippet=description,
                    entity_match_score=calculate_entity_match_score(
                        company.company_name,
                        company.tax_id,
                        f"{title} {description}",
                    ),
                )
            )
        return _candidate_lookup(self.definition.key, candidates)


class CafeFTrustedSourceProvider:
    """Discover bounded company-related articles from CafeF public HTML search."""

    def __init__(
        self,
        definition: TrustedSourceDefinition,
        transport: TrustedHttpTransport,
        *,
        user_agent: str,
    ) -> None:
        self.definition = definition
        self.transport = transport
        self.user_agent = user_agent

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Use the robots-allowed public search page and parse response-owned links."""
        del scope
        query = (company.legal_name or company.company_name).strip()
        if not query:
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.NOT_FOUND,
                reason="COMPANY_NAME_MISSING",
            )
        search_url = f"https://cafef.vn/tim-kiem.chn?{urlencode({'keywords': query})}"
        robots = await _robots_allows(
            self.transport,
            "https://cafef.vn/robots.txt",
            search_url,
            self.user_agent,
        )
        if robots is not None:
            return TrustedSourceLookup(self.definition.key, robots[0], reason=robots[1])
        response = await _get_with_safe_redirects(
            self.transport,
            search_url,
            user_agent=self.user_agent,
        )
        failure = _provider_failure(self.definition.key, response)
        if failure is not None:
            return failure
        assert isinstance(response, TransportResponse)
        parser = _CafeFSearchParser()
        try:
            parser.feed(response.content.decode("utf-8", errors="replace"))
        except Exception:
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.UNAVAILABLE,
                reason="INVALID_HTML_RESPONSE",
            )

        candidates: list[SourceDiscoveryCandidate] = []
        seen: set[str] = set()
        for href, label in parser.links:
            url = urljoin(response.url, href)
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.path.lower().endswith(".chn"):
                continue
            if not _allowed_provider_domain(self.definition, url):
                continue
            if parsed.path.lower() == "/tim-kiem.chn" or url in seen:
                continue
            match_score = calculate_entity_match_score(
                company.company_name,
                company.tax_id,
                label,
            )
            if match_score < 0.3:
                continue
            seen.add(url)
            candidates.append(
                _trusted_candidate(
                    self.definition,
                    url=url,
                    title=label,
                    entity_match_score=match_score,
                )
            )
            if len(candidates) >= 5:
                break
        return _candidate_lookup(self.definition.key, candidates)


class _CafeFSearchParser(HTMLParser):
    """Extract links and visible labels without executing page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._label: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        attributes = {key.lower(): value or "" for key, value in attrs}
        self._href = attributes.get("href", "").strip()
        self._label = [attributes.get("title", "")]

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        label = " ".join(unescape(" ".join(self._label)).split())
        self.links.append((self._href, label))
        self._href = None
        self._label = []


async def _get_with_safe_redirects(
    transport: TrustedHttpTransport,
    url: str,
    *,
    user_agent: str,
    max_redirects: int = 3,
) -> TransportResponse | TransportFailure:
    """Follow only explicitly revalidated public redirects."""
    current_url = url
    for _ in range(max_redirects + 1):
        response = await transport.get(current_url, headers={"User-Agent": user_agent})
        if isinstance(response, TransportFailure):
            return response
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        location = response.headers.get("location")
        if not location:
            return TransportFailure(
                TransportFailureCode.HTTP_CLIENT,
                "PROVIDER_REDIRECT_NO_LOCATION",
            )
        current_url = urljoin(response.url, location)
    return TransportFailure(
        TransportFailureCode.HTTP_CLIENT,
        "PROVIDER_REDIRECT_LIMIT_EXCEEDED",
    )


async def _robots_allows(
    transport: TrustedHttpTransport,
    robots_url: str,
    target_url: str,
    user_agent: str,
) -> tuple[ProviderOutcome, str] | None:
    """Apply fail-closed robots semantics while treating 404 as not published."""
    response = await _get_with_safe_redirects(
        transport,
        robots_url,
        user_agent=user_agent,
    )
    if isinstance(response, TransportFailure):
        return ProviderOutcome.UNAVAILABLE, f"ROBOTS_UNAVAILABLE:{response.code.value.upper()}"
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        return ProviderOutcome.UNAVAILABLE, f"ROBOTS_HTTP_{response.status_code}"
    parser = RobotFileParser(robots_url)
    parser.parse(response.content.decode("utf-8-sig", errors="replace").splitlines())
    if not parser.can_fetch(user_agent, target_url):
        return ProviderOutcome.BLOCKED, "ROBOTS_DISALLOWED"
    return None


def _provider_failure(
    provider: str,
    response: TransportResponse | TransportFailure,
) -> TrustedSourceLookup | None:
    """Map public transport/HTTP failures to stable provider outcomes."""
    if isinstance(response, TransportFailure):
        outcome = (
            ProviderOutcome.BLOCKED
            if response.code == TransportFailureCode.SSRF_BLOCKED
            else ProviderOutcome.UNAVAILABLE
        )
        return TrustedSourceLookup(provider, outcome, reason=response.code.value.upper())
    if response.status_code == 404:
        return TrustedSourceLookup(provider, ProviderOutcome.NOT_FOUND, reason="HTTP_404")
    if response.status_code in {401, 403, 407}:
        return TrustedSourceLookup(
            provider,
            ProviderOutcome.BLOCKED,
            reason=f"ACCESS_CONTROL_HTTP_{response.status_code}",
        )
    if response.status_code == 429:
        return TrustedSourceLookup(provider, ProviderOutcome.UNAVAILABLE, reason="RATE_LIMITED")
    if response.status_code != 200:
        return TrustedSourceLookup(
            provider,
            ProviderOutcome.UNAVAILABLE,
            reason=f"HTTP_{response.status_code}",
        )
    return None


def _trusted_candidate(
    definition: TrustedSourceDefinition,
    *,
    url: str,
    title: str = "",
    snippet: str = "",
    entity_match_score: float | None = None,
) -> SourceDiscoveryCandidate:
    return SourceDiscoveryCandidate(
        url=url,
        discovered_via="trusted_provider",
        provider=definition.key,
        source_type=definition.source_type,
        authority_tier=definition.default_authority_tier,
        authority_by_field=dict(definition.authority_by_field),
        entity_match_score=entity_match_score,
        title=title,
        snippet=snippet,
    )


def _candidate_lookup(
    provider: str,
    candidates: list[SourceDiscoveryCandidate],
) -> TrustedSourceLookup:
    if not candidates:
        return TrustedSourceLookup(provider, ProviderOutcome.NOT_FOUND, reason="NO_MATCHING_RESULT")
    return TrustedSourceLookup(
        provider,
        ProviderOutcome.SUCCESS,
        candidates=tuple(candidates),
    )


def _allowed_provider_domain(definition: TrustedSourceDefinition, url: str) -> bool:
    """Require an HTTP(S) URL within the provider's configured domain boundary."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    expected = definition.domain.lower().rstrip(".")
    return parsed.scheme in {"http", "https"} and (
        host == expected or host.endswith(f".{expected}")
    )


@dataclass
class CountrySourceRegistry:
    """Runtime registry that can accept a new country/provider without core changes."""

    country_code: str
    providers: tuple[TrustedSourceProvider, ...] = ()

    def register(self, provider: TrustedSourceProvider) -> None:
        """Register or replace an adapter by its configured provider key."""
        retained = tuple(
            item for item in self.providers if item.definition.key != provider.definition.key
        )
        self.providers = (*retained, provider)

    @classmethod
    def for_country(cls, country_code: str) -> CountrySourceRegistry:
        """Build the configured registry for a country code."""
        if country_code.upper() != "VN":
            return cls(country_code=country_code.upper())
        return vietnam_source_registry()


VIETNAM_TRUSTED_SOURCE_DEFINITIONS: tuple[TrustedSourceDefinition, ...] = (
    TrustedSourceDefinition(
        key="dangkykinhdoanh",
        domain="dangkykinhdoanh.gov.vn",
        provider_type="government_registry",
        source_type="registry",
        default_authority_tier=1,
        authority_by_field={
            "identity.legal_name": 1,
            "identity.registration_number": 1,
            "identity.tax_id": 2,
            "*": 2,
        },
    ),
    TrustedSourceDefinition(
        key="tracuunnt_gdt",
        domain="tracuunnt.gdt.gov.vn",
        provider_type="government_tax_registry",
        source_type="registry",
        default_authority_tier=1,
        authority_by_field={
            "identity.tax_id": 1,
            "identity.legal_name": 2,
            "identity.registration_number": 2,
            "*": 2,
        },
    ),
    TrustedSourceDefinition(
        key="wikipedia",
        domain="wikipedia.org",
        provider_type="reference_encyclopedia",
        source_type="web_page",
        default_authority_tier=3,
        authority_by_field={
            "overview.description": 3,
            "identity.aliases": 3,
            "identity.legal_name": 4,
            "identity.tax_id": 4,
            "identity.registration_number": 4,
            "*": 3,
        },
    ),
    TrustedSourceDefinition(
        key="vietstock",
        domain="finance.vietstock.vn",
        provider_type="financial_database",
        source_type="news",
        default_authority_tier=3,
        authority_by_field={
            "leadership.members": 3,
            "ownership.structure": 3,
            "finance.revenue": 3,
            "identity.legal_name": 4,
            "identity.tax_id": 4,
            "identity.registration_number": 4,
            "*": 3,
        },
    ),
    TrustedSourceDefinition(
        key="cafef",
        domain="cafef.vn",
        provider_type="financial_media_database",
        source_type="news",
        default_authority_tier=3,
        authority_by_field={
            "leadership.members": 3,
            "ownership.structure": 3,
            "finance.revenue": 3,
            "identity.legal_name": 4,
            "identity.tax_id": 4,
            "identity.registration_number": 4,
            "*": 3,
        },
    ),
)


def vietnam_source_registry(settings: Settings | None = None) -> CountrySourceRegistry:
    """Create Vietnam providers with live adapters only for approved public access paths."""
    resolved_settings = settings or get_settings()
    transport = SecureHttpTransport(
        timeout=resolved_settings.fetch_timeout,
        legacy_tls_fallback_enabled=resolved_settings.fetch_legacy_tls_fallback_enabled,
        legacy_tls_security_level=resolved_settings.fetch_legacy_tls_security_level,
        max_response_bytes=resolved_settings.fetch_max_response_bytes,
        rate_limit_seconds=resolved_settings.fetch_rate_limit_seconds,
        max_concurrency_per_domain=resolved_settings.fetch_max_concurrency_per_domain,
    )
    definitions = {item.key: item for item in VIETNAM_TRUSTED_SOURCE_DEFINITIONS}
    live_providers: dict[str, TrustedSourceProvider] = {}
    if resolved_settings.trusted_source_live_enabled:
        live_providers = {
            "wikipedia": WikipediaTrustedSourceProvider(
                definitions["wikipedia"],
                transport,
                user_agent=resolved_settings.fetch_user_agent,
            ),
            "cafef": CafeFTrustedSourceProvider(
                definitions["cafef"],
                transport,
                user_agent=resolved_settings.fetch_user_agent,
            ),
        }
    manual_reasons = {
        "dangkykinhdoanh": "NO_STABLE_PUBLIC_STRUCTURED_ENDPOINT",
        "tracuunnt_gdt": "CAPTCHA_REQUIRED",
        "vietstock": "NO_DOCUMENTED_PUBLIC_COMPANY_SEARCH_ENDPOINT",
        "wikipedia": "LIVE_PROVIDER_DISABLED",
        "cafef": "LIVE_PROVIDER_DISABLED",
    }
    return CountrySourceRegistry(
        country_code="VN",
        providers=tuple(
            ConfiguredTrustedSourceProvider(
                definition,
                live_provider=live_providers.get(definition.key),
                manual_reason=manual_reasons.get(
                    definition.key,
                    "NO_STRUCTURED_PROVIDER_RESULT",
                ),
            )
            for definition in VIETNAM_TRUSTED_SOURCE_DEFINITIONS
        ),
    )
