"""Unit tests for Playwright browser adapter and browser fallback in WebFetcher."""

from __future__ import annotations

import builtins

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.source import SourceFetchAttempt
from company_profile.integrations.fetch.http_transport import TransportResponse
from company_profile.modules.sources.browser_adapter import (
    PlaywrightBrowserAdapter,
    RenderedPageResult,
)
from company_profile.modules.sources.fetcher import WebFetcher


class FixtureBrowserAdapter:
    """Browser fixture returning one controlled rendered outcome."""

    def __init__(self, result: RenderedPageResult) -> None:
        self.result = result
        self.calls: list[str] = []

    async def fetch_rendered_page(self, url: str) -> RenderedPageResult:
        self.calls.append(url)
        return self.result


@pytest.mark.anyio
async def test_browser_adapter_ssrf_rejection() -> None:
    """Verify browser adapter rejects unsafe SSRF target URLs."""
    adapter = PlaywrightBrowserAdapter(timeout_seconds=5)
    res = await adapter.fetch_rendered_page("http://169.254.169.254/latest/meta-data")

    assert res.http_status == 400
    assert "SSRF_PREVENTION" in (res.reason or "")
    assert res.content_html == ""


@pytest.mark.anyio
async def test_browser_adapter_reports_unavailable_without_fabricated_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing browser runtime remains typed unavailable and never creates fake data."""
    real_import = builtins.__import__

    def reject_playwright(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("playwright"):
            raise ImportError("playwright unavailable")
        return real_import(name, *args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(builtins, "__import__", reject_playwright)
    adapter = PlaywrightBrowserAdapter(timeout_seconds=5)
    res = await adapter.fetch_rendered_page("https://example.com")

    assert res.http_status == 0
    assert res.content_html == ""
    assert res.reason == "BROWSER_UNAVAILABLE:ImportError"


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

    browser = FixtureBrowserAdapter(
        RenderedPageResult(
            "https://public.example/spa",
            200,
            "<html><body><h1>Rendered company profile</h1></body></html>",
            reason="browser_rendered",
        )
    )
    fetcher = WebFetcher(session=db_session, browser_adapter=browser)  # type: ignore[arg-type]
    monkeypatch.setattr(fetcher.settings, "fetch_browser_fallback_enabled", True)
    monkeypatch.setattr(fetcher, "max_retries", 0)
    monkeypatch.setattr(
        "company_profile.modules.sources.fetcher.validate_url_safety",
        lambda _url: (True, "SAFE"),
    )
    monkeypatch.setattr(
        "company_profile.modules.sources.fetcher.evaluate_robots_policy",
        lambda _url, _agent: "allowed",
    )

    async def js_shell(request_url: str, **_kwargs: object) -> TransportResponse:
        if request_url.endswith("/robots.txt"):
            return TransportResponse(404, request_url, httpx.Headers(), b"")
        return TransportResponse(
            200,
            "https://public.example/spa",
            httpx.Headers({"content-type": "text/html"}),
            b'<html><script src="/app.js"></script><div id="root"></div></html>',
        )

    monkeypatch.setattr(fetcher.http_transport, "get", js_shell)

    result = await fetcher.fetch_and_store_source(
        workspace_id=ws.id,
        company_id=company.id,
        url="https://public.example/spa",
        parse_content=False,
    )

    assert result.status_code == 200
    assert result.snapshot is not None
    assert result.adapter_used == "playwright"
    assert browser.calls == ["https://public.example/spa"]


@pytest.mark.anyio
async def test_web_fetcher_persists_browser_unavailable_outcome(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Browser runtime failures stop the pipeline with a durable typed outcome."""
    ws = Workspace(name="Unavailable Browser WS", slug="unavailable-browser-ws")
    db_session.add(ws)
    await db_session.flush()
    company = CompanyProfile(
        workspace_id=ws.id,
        company_name="Browser Unavailable Corp",
        normalized_name="browser unavailable corp",
    )
    db_session.add(company)
    await db_session.flush()
    browser = FixtureBrowserAdapter(
        RenderedPageResult(
            "https://browser-down.example/spa",
            0,
            "",
            reason="BROWSER_UNAVAILABLE:RuntimeError",
        )
    )
    fetcher = WebFetcher(session=db_session, browser_adapter=browser)  # type: ignore[arg-type]
    monkeypatch.setattr(fetcher.settings, "fetch_browser_fallback_enabled", True)
    monkeypatch.setattr(fetcher, "max_retries", 0)
    monkeypatch.setattr(
        "company_profile.modules.sources.fetcher.validate_url_safety",
        lambda _url: (True, "SAFE"),
    )
    monkeypatch.setattr(
        "company_profile.modules.sources.fetcher.evaluate_robots_policy",
        lambda _url, _agent: "allowed",
    )

    async def js_shell(request_url: str, **_kwargs: object) -> TransportResponse:
        if request_url.endswith("/robots.txt"):
            return TransportResponse(404, request_url, httpx.Headers(), b"")
        return TransportResponse(
            200,
            "https://browser-down.example/spa",
            httpx.Headers({"content-type": "text/html"}),
            b'<html><script src="/app.js"></script><div id="root"></div></html>',
        )

    monkeypatch.setattr(fetcher.http_transport, "get", js_shell)

    result = await fetcher.fetch_and_store_source(
        workspace_id=ws.id,
        company_id=company.id,
        url="https://browser-down.example/spa",
        parse_content=False,
    )

    attempt = (await db_session.execute(select(SourceFetchAttempt))).scalars().one()
    assert result.snapshot is None
    assert result.error_message == "BROWSER_UNAVAILABLE:RuntimeError"
    assert attempt.adapter == "playwright"
    assert attempt.outcome_code == "browser_unavailable"
