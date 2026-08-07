"""Deterministic fixture fetch adapter for local testing."""

from __future__ import annotations

from typing import Any


class FixtureFetchResponse:
    """Fixture fetch response mock."""

    def __init__(
        self,
        url: str,
        status_code: int = 200,
        content: str = "<html><body><h1>Fixture Company</h1></body></html>",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}


class FixtureFetcher:
    """Deterministic offline fetcher using predefined fixture responses."""

    def __init__(self, fixtures: dict[str, FixtureFetchResponse] | None = None) -> None:
        self.fixtures = fixtures or {}

    def register_fixture(self, url: str, response: FixtureFetchResponse) -> None:
        """Register a fixture response for a specific URL."""
        self.fixtures[url] = response

    async def fetch(self, url: str, **_kwargs: Any) -> FixtureFetchResponse:
        """Fetch content for a URL from registered fixtures or return default."""
        if url in self.fixtures:
            return self.fixtures[url]

        return FixtureFetchResponse(
            url=url,
            status_code=200,
            content=f"<html><body><h1>Fixture Page for {url}</h1></body></html>",
        )
