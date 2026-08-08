"""Direct HTTP adapter for bounded official website discovery."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx

from company_profile.modules.sources.official_discovery import WebsiteFetchResponse
from company_profile.modules.sources.validator import validate_url_safety


class HttpxWebsiteFetchProvider:
    """Fetch public robots, sitemap, and HTML documents with safe redirects."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 30.0,
        max_response_bytes: int = 10_000_000,
        max_redirects: int = 5,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> WebsiteFetchResponse:
        """Fetch one URL, validating every redirect before following it."""
        current_url = url
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                for _ in range(self.max_redirects + 1):
                    safe, reason = validate_url_safety(current_url)
                    if not safe:
                        return WebsiteFetchResponse(
                            url, current_url, 400, error=f"SSRF_BLOCKED:{reason}"
                        )
                    response = await client.get(
                        current_url,
                        headers={
                            "User-Agent": self.user_agent,
                            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain",
                        },
                    )
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            return WebsiteFetchResponse(
                                url,
                                str(response.url),
                                response.status_code,
                                error="REDIRECT_NO_LOCATION",
                            )
                        next_url = urljoin(str(response.url), location)
                        next_safe, next_reason = validate_url_safety(next_url)
                        if not next_safe:
                            return WebsiteFetchResponse(
                                url,
                                next_url,
                                400,
                                error=f"SSRF_REDIRECT_BLOCKED:{next_reason}",
                            )
                        current_url = next_url
                        continue
                    content = response.content
                    if len(content) > self.max_response_bytes:
                        return WebsiteFetchResponse(
                            url, str(response.url), 413, error="SIZE_EXCEEDED"
                        )
                    return WebsiteFetchResponse(
                        requested_url=url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content=response.text,
                        content_type=response.headers.get("content-type", ""),
                    )
                return WebsiteFetchResponse(url, current_url, 508, error="MAX_REDIRECTS_EXCEEDED")
        except httpx.HTTPError as exc:
            return WebsiteFetchResponse(url, current_url, 0, error=type(exc).__name__)
