"""Deterministic tests for the official Google search adapter and provider selection."""

from __future__ import annotations

import pytest
from httpx import Request, Response

from company_profile.config.settings import Settings
from company_profile.integrations.search.google_search import (
    GoogleSearchProvider,
    GoogleSearchProviderError,
)
from company_profile.modules.research.pipeline import ResearchPipelineExecutor


@pytest.mark.asyncio
async def test_google_search_maps_only_structured_http_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search results come from the JSON API and invalid links are discarded."""

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        return Response(
            status_code=200,
            json={
                "items": [
                    {
                        "title": "Acme official website",
                        "link": "https://acme.example/about",
                        "snippet": "Public company information.",
                    },
                    {"title": "Invalid result", "link": "javascript:alert(1)"},
                ]
            },
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    provider = GoogleSearchProvider("key", "engine")

    results = await provider.search("Acme", locale="en", num_results=5)

    assert len(results) == 1
    assert results[0].provider == "google"
    assert results[0].domain == "acme.example"
    assert results[0].url == "https://acme.example/about"


@pytest.mark.asyncio
async def test_google_search_rate_limit_is_safe_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upstream details are converted to a stable safe error code."""

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        return Response(status_code=429, request=Request("GET", url))

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    with pytest.raises(GoogleSearchProviderError, match="GOOGLE_SEARCH_RATE_LIMITED"):
        await GoogleSearchProvider("key", "engine").search("Acme")


def test_search_provider_requires_real_google_configuration() -> None:
    """The application never silently falls back to a fixture provider."""
    provider, warning = ResearchPipelineExecutor.build_search_provider(
        Settings(search_provider="google", search_api_key="", search_engine_id="")
    )
    assert provider is None
    assert warning == "SEARCH_PROVIDER_UNAVAILABLE:GOOGLE_CONFIGURATION_MISSING"

    provider, warning = ResearchPipelineExecutor.build_search_provider(
        Settings(search_provider="disabled")
    )
    assert provider is None
    assert warning == "SEARCH_PROVIDER_UNAVAILABLE:DISABLED"

    provider, warning = ResearchPipelineExecutor.build_search_provider(
        Settings(search_provider="fixture")
    )
    assert provider is None
    assert warning == "SEARCH_PROVIDER_UNAVAILABLE:FIXTURE_DISABLED_IN_RUNTIME"

    provider, warning = ResearchPipelineExecutor.build_search_provider(
        Settings(search_provider="google", search_api_key="key", search_engine_id="engine")
    )
    assert isinstance(provider, GoogleSearchProvider)
    assert warning is None
