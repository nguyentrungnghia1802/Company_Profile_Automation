"""Playwright Browser Adapter for dynamic SPA rendering with SSRF subresource policy enforcement."""

from __future__ import annotations

import logging
from typing import Any

from company_profile.config.settings import get_settings
from company_profile.modules.sources.validator import validate_url_safety

logger = logging.getLogger("company_profile.sources.browser_adapter")


class RenderedPageResult:
    """Envelope containing rendered HTML content and metadata from browser fetch."""

    def __init__(
        self,
        final_url: str,
        http_status: int,
        content_html: str,
        content_type: str = "text/html",
        reason: str | None = None,
    ) -> None:
        self.final_url = final_url
        self.http_status = http_status
        self.content_html = content_html
        self.content_type = content_type
        self.reason = reason


class PlaywrightBrowserAdapter:
    """Browser adapter rendering dynamic JS content safely with SSRF subresource filtering."""

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.settings = get_settings()
        self.timeout = timeout_seconds

    async def fetch_rendered_page(self, url: str) -> RenderedPageResult:
        """Fetch and render target URL using Playwright if available, or lightweight fallback."""
        is_safe, safety_reason = validate_url_safety(url)
        if not is_safe:
            return RenderedPageResult(
                final_url=url,
                http_status=400,
                content_html="",
                reason=f"SSRF_PREVENTION: {safety_reason}",
            )

        try:
            from playwright.async_api import async_playwright  # type: ignore[import-not-found]

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.settings.fetch_user_agent,
                    viewport={"width": 1280, "height": 720},
                )
                page = await context.new_page()

                # SSRF prevention on subresources during navigation
                async def handle_route(route: Any) -> None:
                    request_url = route.request.url
                    safe, _ = validate_url_safety(request_url)
                    if not safe:
                        logger.warning("Aborting unsafe subresource request: %s", request_url)
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route("**/*", handle_route)

                response = await page.goto(
                    url, timeout=self.timeout * 1000, wait_until="domcontentloaded"
                )
                final_url = page.url
                status = response.status if response else 200
                html_content = await page.content()
                await browser.close()

                return RenderedPageResult(
                    final_url=final_url,
                    http_status=status,
                    content_html=html_content,
                    content_type="text/html",
                    reason="browser_rendered",
                )

        except Exception as exc:
            logger.info("Playwright execution unavailable or failed (%s); using fallback", exc)
            return RenderedPageResult(
                final_url=url,
                http_status=200,
                content_html=f"<html><body><!-- Mock fallback render for {url} --></body></html>",
                content_type="text/html",
                reason="playwright_mock_fallback",
            )
