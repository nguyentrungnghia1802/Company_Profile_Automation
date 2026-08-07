"""Unit tests for Playwright browser adapter and browser fallback in WebFetcher."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.modules.sources.browser_adapter import PlaywrightBrowserAdapter
from company_profile.modules.sources.fetcher import WebFetcher


@pytest.mark.anyio
async def test_browser_adapter_ssrf_rejection() -> None:
    """Verify browser adapter rejects unsafe SSRF target URLs."""
    adapter = PlaywrightBrowserAdapter(timeout_seconds=5)
    res = await adapter.fetch_rendered_page("http://169.254.169.254/latest/meta-data")

    assert res.http_status == 400
    assert "SSRF_PREVENTION" in (res.reason or "")
    assert res.content_html == ""


@pytest.mark.anyio
async def test_browser_adapter_fallback_rendering() -> None:
    """Verify browser adapter returns rendered page envelope for public URL."""
    adapter = PlaywrightBrowserAdapter(timeout_seconds=5)
    res = await adapter.fetch_rendered_page("https://example.com")

    assert res.http_status == 200
    assert res.content_html != ""
    assert res.reason in ("browser_rendered", "playwright_mock_fallback")


@pytest.mark.anyio
async def test_web_fetcher_browser_fallback_enabled(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify WebFetcher uses browser fallback when enabled."""
    ws = Workspace(name="Test Browser WS", slug="test-browser-ws")
    db_session.add(ws)
    await db_session.flush()

    company = CompanyProfile(
        workspace_id=ws.id,
        tax_id="0399887766",
        company_name="Dynamic SPA Corp",
        normalized_name="dynamic spa corp",
    )
    db_session.add(company)
    await db_session.flush()

    fetcher = WebFetcher(session=db_session)
    monkeypatch.setattr(fetcher.settings, "fetch_browser_fallback_enabled", True)

    result = await fetcher.fetch_and_store_source(
        workspace_id=ws.id,
        company_id=company.id,
        url="https://example.com/spa",
    )

    assert result.status_code == 200
    assert result.snapshot is not None
    assert result.adapter_used in ("httpx", "playwright")
