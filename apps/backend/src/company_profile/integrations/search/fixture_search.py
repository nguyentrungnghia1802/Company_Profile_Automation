"""Fixture SearchProvider implementation for local testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SearchResultItem:
    """Item in search result list."""

    title: str
    url: str
    snippet: str
    domain: str
    rank: int = 0
    provider: str = "fixture"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_type: str = "web_page"
    entity_match_score: float | None = None
    selection_reason: str | None = None
    metadata: dict[str, Any] | None = None


class FixtureSearchProvider:
    """Fixture search provider returning mock web search results."""

    def __init__(self, default_results: list[SearchResultItem] | None = None) -> None:
        self.default_results = default_results or [
            SearchResultItem(
                title="Example Company — Official Site",
                url="https://example.com",
                snippet="Official homepage of Example Company.",
                domain="example.com",
            ),
        ]

    async def search(self, _query: str, **_kwargs: Any) -> list[SearchResultItem]:
        """Return search results for query."""
        return self.default_results
