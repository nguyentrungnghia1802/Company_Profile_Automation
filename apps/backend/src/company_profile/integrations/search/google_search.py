"""Google Programmable Search adapter for public-source discovery."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from company_profile.integrations.search.fixture_search import SearchResultItem


class GoogleSearchProviderError(RuntimeError):
    """Safe, provider-neutral error raised by the Google search adapter."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class GoogleSearchProvider:
    """Use Google's official JSON API instead of scraping search-result HTML."""

    provider_name = "google"
    endpoint = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, engine_id: str, *, timeout: float = 15.0) -> None:
        self.api_key = api_key
        self.engine_id = engine_id
        self.timeout = timeout

    async def search(self, query: str, **kwargs: Any) -> list[SearchResultItem]:
        """Return only structured public result metadata from the official API."""
        locale = str(kwargs.get("locale") or kwargs.get("language") or "en")
        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": min(max(int(kwargs.get("num_results", 10)), 1), 10),
            "hl": locale,
        }
        language = str(kwargs.get("language") or "").strip().lower()
        if language in {"vi", "en"}:
            params["lr"] = f"lang_{language}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.endpoint, params=params)
        except httpx.TimeoutException as exc:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_TIMEOUT") from exc
        except httpx.RequestError as exc:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_NETWORK_ERROR") from exc

        if response.status_code == 429:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_RATE_LIMITED")
        if response.status_code >= 500:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_UPSTREAM_UNAVAILABLE")
        if response.status_code != 200:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_API_REJECTED")

        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleSearchProviderError("GOOGLE_SEARCH_INVALID_RESPONSE") from exc
        if not isinstance(payload, dict):
            raise GoogleSearchProviderError("GOOGLE_SEARCH_INVALID_RESPONSE")
        if payload.get("error"):
            raise GoogleSearchProviderError("GOOGLE_SEARCH_API_ERROR")

        items = payload.get("items")
        if not isinstance(items, list):
            return []

        results: list[SearchResultItem] = []
        for rank, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            url = str(item.get("link") or "").strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                continue
            title = " ".join(str(item.get("title") or "").split())
            snippet = " ".join(str(item.get("snippet") or "").split())
            if not title:
                continue
            results.append(
                SearchResultItem(
                    title=title,
                    url=url,
                    snippet=snippet,
                    domain=parsed.hostname.lower().removeprefix("www."),
                    rank=rank,
                    provider=self.provider_name,
                )
            )
        return results
