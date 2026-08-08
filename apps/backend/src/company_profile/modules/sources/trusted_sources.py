"""Country-configured trusted source providers and extensible registries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from company_profile.modules.sources.discovery import (
    ProviderOutcome,
    SourceDiscoveryCandidate,
    TrustedSourceDefinition,
    TrustedSourceLookup,
    TrustedSourceProvider,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from company_profile.db.models.company import CompanyProfile


class ConfiguredTrustedSourceProvider:
    """Adapter for a configured structured/public response supplied by an integration.

    The default adapter deliberately performs no live scraping. A real adapter must
    provide a public structured response or an explicit URL and must enforce the
    source's robots, terms, and access controls before returning candidates.
    """

    def __init__(self, definition: TrustedSourceDefinition) -> None:
        self.definition = definition

    async def discover(
        self, *, company: CompanyProfile, scope: Mapping[str, Any]
    ) -> TrustedSourceLookup:
        """Read only an explicit structured result; never invent a source URL."""
        del company
        payload = scope.get("trusted_source_results") or scope.get("trusted_sources")
        if not isinstance(payload, dict):
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.MANUAL_REQUIRED,
                reason="NO_STRUCTURED_PROVIDER_RESULT",
            )

        raw = payload.get(self.definition.key) or payload.get(self.definition.provider_type)
        if raw is None:
            return TrustedSourceLookup(
                self.definition.key,
                ProviderOutcome.MANUAL_REQUIRED,
                reason="NO_STRUCTURED_PROVIDER_RESULT",
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
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
        configured = self.definition.domain.lower().rstrip(".")
        return hostname == configured or hostname.endswith(f".{configured}")

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


def vietnam_source_registry() -> CountrySourceRegistry:
    """Create the default Vietnam registry from provider configuration."""
    return CountrySourceRegistry(
        country_code="VN",
        providers=tuple(
            ConfiguredTrustedSourceProvider(definition)
            for definition in VIETNAM_TRUSTED_SOURCE_DEFINITIONS
        ),
    )
