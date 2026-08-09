"""Bounded HTTP-first source fetching and crawl coordination."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import select

from company_profile.config.settings import get_settings
from company_profile.db.models.source import (
    DocumentBlock,
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
    calculate_content_hash,
    normalize_url,
)
from company_profile.db.transaction import transactional
from company_profile.integrations.fetch.http_transport import (
    SecureHttpTransport,
    TransportFailure,
    TransportFailureCode,
)
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.integrations.storage.mock_malware import MockMalwareScanner
from company_profile.modules.sources.browser_adapter import PlaywrightBrowserAdapter
from company_profile.modules.sources.parser import (
    HTML_PARSER_VERSION,
    PDF_PARSER_VERSION,
    STRUCTURED_PARSER_VERSION,
    DocumentParser,
    PDFDocumentParser,
)
from company_profile.modules.sources.policy import evaluate_robots_policy
from company_profile.modules.sources.validator import validate_url_safety

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("company_profile.sources.fetcher")

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_ALLOWED_MIME_TYPES = {
    "application/json",
    "application/ld+json",
    "application/pdf",
    "application/xhtml+xml",
    "application/xml",
    "text/html",
    "text/plain",
    "text/xml",
}


class _DomainLimiter:
    """Enforce per-domain concurrency and a minimum request interval."""

    def __init__(self, max_concurrency: int, interval_seconds: float) -> None:
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self.last_request: dict[str, float] = {}
        self.lock = asyncio.Lock()
        self._max_concurrency = max(1, max_concurrency)
        self.interval_seconds = max(0.0, interval_seconds)

    async def __aenter__(self) -> None:
        raise RuntimeError("Use acquire(domain) as an async context manager.")

    def acquire(self, domain: str) -> _DomainLease:
        """Return a lease for one hostname."""
        semaphore = self._semaphores.setdefault(domain, asyncio.Semaphore(self._max_concurrency))
        return _DomainLease(self, domain, semaphore)


class _DomainLease:
    """Async context manager for one domain limiter slot."""

    def __init__(self, limiter: _DomainLimiter, domain: str, semaphore: asyncio.Semaphore) -> None:
        self._limiter = limiter
        self._domain = domain
        self._semaphore = semaphore

    async def __aenter__(self) -> None:
        await self._semaphore.acquire()
        async with self._limiter.lock:
            now = time.monotonic()
            elapsed = now - self._limiter.last_request.get(self._domain, 0.0)
            wait_for = self._limiter.interval_seconds - elapsed
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._limiter.last_request[self._domain] = time.monotonic()

    async def __aexit__(self, *_exc_info: object) -> None:
        self._semaphore.release()


@dataclass(slots=True)
class _HttpResponse:
    """Validated direct HTTP response envelope."""

    status_code: int
    final_url: str
    content_type: str
    content: bytes
    headers: httpx.Headers
    redirect_count: int
    adapter: str = "httpx"


@dataclass(slots=True)
class _FetchFailure:
    """Typed, sanitized failure from the direct HTTP adapter."""

    status_code: int
    final_url: str
    outcome_code: str
    message: str
    retryable: bool = False
    redirect_count: int = 0


@dataclass(slots=True)
class FetchResult:
    """Result envelope of a web source fetch operation."""

    source: Source
    snapshot: SourceSnapshot | None
    status_code: int
    content_type: str = "text/html"
    adapter_used: str = "httpx"
    error_message: str | None = None
    final_url: str | None = None
    redirect_count: int = 0
    retry_count: int = 0


class WebFetcher:
    """HTTP-first source fetcher with bounded fallback and parser persistence."""

    def __init__(
        self,
        session: AsyncSession,
        storage: LocalObjectStorage | None = None,
        malware_scanner: MockMalwareScanner | None = None,
        browser_adapter: PlaywrightBrowserAdapter | None = None,
    ) -> None:
        self.session = session
        settings = get_settings()
        self.settings = settings
        self.storage = storage or LocalObjectStorage(settings.local_storage_root)
        self.malware_scanner = malware_scanner or MockMalwareScanner()
        self.parser = DocumentParser()
        self.browser_adapter = browser_adapter or PlaywrightBrowserAdapter(
            timeout_seconds=settings.fetch_timeout
        )
        self.user_agent = settings.fetch_user_agent
        self.timeout = settings.fetch_timeout
        self.max_bytes = settings.fetch_max_response_bytes
        self.max_decompressed_bytes = settings.fetch_max_decompressed_bytes
        self.max_redirects = max(0, settings.fetch_max_redirects)
        self.max_retries = max(0, settings.fetch_max_retries)
        self.http_transport = SecureHttpTransport(
            timeout=self.timeout,
            legacy_tls_fallback_enabled=settings.fetch_legacy_tls_fallback_enabled,
            legacy_tls_security_level=settings.fetch_legacy_tls_security_level,
            max_response_bytes=min(self.max_bytes, self.max_decompressed_bytes),
        )
        self._domain_limiter = _DomainLimiter(
            settings.fetch_max_concurrency_per_domain,
            settings.fetch_rate_limit_seconds,
        )
        self._browser_fallbacks_used = 0

    async def fetch_and_store_source(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        url: str,
        source_type: str = "web_page",
        research_job_id: uuid.UUID | None = None,
        parse_content: bool = True,
    ) -> FetchResult:
        """Fetch one source and persist an immutable snapshot.

        Direct HTTP is always attempted first. Browser rendering is considered
        only for a JS-like/404 page, when enabled and policy-allowed, and while
        the instance fallback budget remains. Redirect targets are validated
        before each request and are never delegated to httpx automatically.
        """
        is_safe, safety_reason = validate_url_safety(url)
        norm_url = (
            normalize_url(url) if is_safe or "UNSUPPORTED_SCHEME" not in safety_reason else url
        )
        try:
            domain = (urlparse(norm_url).hostname or "unknown").lower()
        except ValueError:
            domain = "unknown"

        async with transactional(self.session):
            source = await self._get_or_create_source(
                workspace_id, company_id, url, norm_url, domain, source_type
            )
            attempt = SourceFetchAttempt(
                workspace_id=workspace_id,
                source_id=source.id,
                research_job_id=research_job_id,
                adapter="httpx",
                requested_url=url,
                policy_result="allowed" if is_safe else safety_reason,
            )
            self.session.add(attempt)
            await self.session.flush()

            if not is_safe:
                source.status = "rejected"
                return await self._failure_result(
                    source,
                    attempt,
                    status_code=400,
                    outcome_code="redirect_blocked",
                    message=f"SSRF_PREVENTION: {safety_reason}",
                )

            existing_snapshot = await self._latest_snapshot(source.id)
            if existing_snapshot is not None:
                if parse_content:
                    await self.parse_snapshot(existing_snapshot)
                source.status = "fetched"
                attempt.final_url = source.canonical_url
                attempt.http_status = 200
                attempt.content_type = existing_snapshot.content_type
                attempt.byte_count = existing_snapshot.byte_size
                attempt.outcome_code = "success"
                attempt.completed_at = datetime.now(UTC)
                return FetchResult(
                    source=source,
                    snapshot=existing_snapshot,
                    status_code=200,
                    content_type=existing_snapshot.content_type,
                    final_url=source.canonical_url,
                )

            try:
                direct = await self._fetch_with_retries(url, attempt)
                if isinstance(direct, _FetchFailure):
                    source.status = "failed"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=direct.status_code,
                        outcome_code=direct.outcome_code,
                        message=direct.message,
                        final_url=direct.final_url,
                        redirect_count=direct.redirect_count,
                    )
                adapter_used = direct.adapter
                content = direct.content
                response_status = direct.status_code
                final_url = direct.final_url
                response_content_type = direct.content_type
                redirect_count = direct.redirect_count

                if self._should_use_browser(
                    response_status, response_content_type, content, final_url
                ):
                    rendered = await self._fetch_browser_fallback(url, attempt, redirect_count)
                    if isinstance(rendered, _HttpResponse):
                        content = rendered.content
                        response_status = rendered.status_code
                        final_url = rendered.final_url
                        response_content_type = rendered.content_type
                        redirect_count = rendered.redirect_count
                        adapter_used = "playwright"
                    else:
                        source.status = "failed"
                        return await self._failure_result(
                            source,
                            attempt,
                            status_code=rendered.status_code,
                            outcome_code=rendered.outcome_code,
                            message=rendered.message,
                            final_url=rendered.final_url,
                            redirect_count=rendered.redirect_count,
                            adapter="playwright",
                        )

                if content is None:
                    source.status = "failed"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=response_status,
                        outcome_code="http_error",
                        message=f"HTTP {response_status}",
                        final_url=final_url,
                        redirect_count=redirect_count,
                    )

                if response_status != 200:
                    source.status = "failed"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=response_status,
                        outcome_code="http_error",
                        message=f"HTTP {response_status}",
                        final_url=final_url,
                        redirect_count=redirect_count,
                        adapter=adapter_used,
                    )

                content_type = self._normalized_content_type(response_content_type, final_url)
                mime_error = self._validate_mime(content_type, final_url, content)
                if mime_error is not None:
                    source.status = "failed"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=200,
                        outcome_code="mime_rejected",
                        message=mime_error,
                        final_url=final_url,
                        redirect_count=redirect_count,
                        adapter=adapter_used,
                    )

                if len(content) > self.max_bytes:
                    source.status = "failed"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=200,
                        outcome_code="size_exceeded",
                        message="Response exceeded max byte limit.",
                        final_url=final_url,
                        redirect_count=redirect_count,
                        adapter=adapter_used,
                    )

                content_hash = calculate_content_hash(content)
                same_hash = await self._snapshot_by_hash(source.id, content_hash)
                if same_hash is not None:
                    if parse_content:
                        await self.parse_snapshot(same_hash)
                    source.status = "fetched"
                    attempt.final_url = final_url
                    attempt.http_status = 200
                    attempt.content_type = content_type
                    attempt.byte_count = len(content)
                    attempt.redirect_count = redirect_count
                    attempt.outcome_code = "success"
                    attempt.completed_at = datetime.now(UTC)
                    return FetchResult(
                        source=source,
                        snapshot=same_hash,
                        status_code=200,
                        content_type=content_type,
                        adapter_used=adapter_used,
                        final_url=final_url,
                        redirect_count=redirect_count,
                        retry_count=attempt.retry_count,
                    )

                is_clean, scan_desc = await self.malware_scanner.scan_bytes(content)
                if not is_clean:
                    source.status = "rejected"
                    return await self._failure_result(
                        source,
                        attempt,
                        status_code=200,
                        outcome_code="malware_detected",
                        message=f"Malware scan failed: {scan_desc}",
                        final_url=final_url,
                        redirect_count=redirect_count,
                        adapter=adapter_used,
                    )

                object_key = (
                    f"{workspace_id}/{company_id}/{content_hash}"
                    f"{self._storage_suffix(content_type)}"
                )
                await self.storage.put_object(object_key, content, content_type=content_type)
                snapshot = SourceSnapshot(
                    workspace_id=workspace_id,
                    source_id=source.id,
                    content_hash=content_hash,
                    storage_provider="local",
                    object_key=object_key,
                    content_type=content_type,
                    byte_size=len(content),
                    language=self._initial_language(content_type, content),
                    parser_version=self._parser_version(content_type, final_url),
                    parser_status="pending",
                    malware_scan_status="clean",
                )
                self.session.add(snapshot)
                await self.session.flush()

                blocks: list[DocumentBlock] = []
                if parse_content:
                    blocks = await self.parse_snapshot(snapshot)

                source.status = "fetched"
                attempt.final_url = final_url
                attempt.http_status = 200
                attempt.content_type = content_type
                attempt.byte_count = len(content)
                attempt.redirect_count = redirect_count
                attempt.outcome_code = "success"
                attempt.completed_at = datetime.now(UTC)
                await self.session.flush()
                logger.info(
                    "Fetched source snapshot",
                    extra={
                        "source_id": str(source.id),
                        "content_hash": content_hash,
                        "byte_size": len(content),
                        "blocks_count": len(blocks),
                        "adapter": adapter_used,
                    },
                )
                return FetchResult(
                    source=source,
                    snapshot=snapshot,
                    status_code=200,
                    content_type=content_type,
                    adapter_used=adapter_used,
                    final_url=final_url,
                    redirect_count=redirect_count,
                    retry_count=attempt.retry_count,
                )
            except Exception as exc:
                source.status = "failed"
                logger.error("Web fetcher failed for URL %s: %s", url, exc, exc_info=True)
                return await self._failure_result(
                    source,
                    attempt,
                    status_code=500,
                    outcome_code="http_error",
                    message=f"FETCH_FAILED:{type(exc).__name__}",
                )

    async def parse_snapshot(self, snapshot: SourceSnapshot) -> list[DocumentBlock]:
        """Parse one immutable snapshot idempotently and record parser status."""
        existing_stmt = select(DocumentBlock).where(DocumentBlock.source_snapshot_id == snapshot.id)
        existing_result = await self.session.execute(existing_stmt)
        existing_blocks = list(existing_result.scalars().all())
        if existing_blocks:
            snapshot.parser_status = "success"
            snapshot.parser_version = existing_blocks[0].parser_version
            snapshot.language = existing_blocks[0].language
            return existing_blocks

        try:
            content = await self.storage.get_object(snapshot.object_key)
            source = await self.session.get(Source, snapshot.source_id)
            source_url = source.normalized_url if source else ""
            content_type = self._normalized_content_type(snapshot.content_type, source_url)
            if content_type == "application/pdf" or source_url.lower().endswith(".pdf"):
                blocks = PDFDocumentParser(
                    max_bytes=self.max_bytes,
                    max_decompressed_bytes=self.max_decompressed_bytes,
                ).parse_pdf_to_blocks(snapshot.workspace_id, snapshot.id, content)
            elif content_type in {
                "application/json",
                "application/ld+json",
            } or content_type.endswith("+json"):
                try:
                    payload = json_loads_bytes(content)
                except (UnicodeDecodeError, ValueError, TypeError):
                    blocks = []
                else:
                    blocks = self.parser.parse_json_to_blocks(
                        snapshot.workspace_id,
                        snapshot.id,
                        payload,
                        source_url=source_url,
                        provenance={"source_type": source.source_type if source else "unknown"},
                    )
            else:
                html_content = content.decode("utf-8", errors="replace")
                blocks = self.parser.parse_html_to_blocks(
                    snapshot.workspace_id,
                    snapshot.id,
                    html_content,
                    source_url=source_url,
                )

            for block in blocks:
                self.session.add(block)
            snapshot.parser_status = "success"
            snapshot.parser_version = (
                blocks[0].parser_version
                if blocks
                else self._parser_version(content_type, source_url)
            )
            snapshot.language = (
                blocks[0].language if blocks else self._initial_language(content_type, content)
            )
            snapshot.parser_error = None
            await self.session.flush()
            return blocks
        except Exception as exc:
            snapshot.parser_status = "failed"
            snapshot.parser_error = f"{type(exc).__name__}:{str(exc)[:240]}"
            await self.session.flush()
            logger.warning("Document parsing failed for snapshot %s", snapshot.id)
            return []

    async def discover_links(self, snapshot: SourceSnapshot) -> list[str]:
        """Read same-document link blocks for bounded coordinator expansion."""
        source = await self.session.get(Source, snapshot.source_id)
        source_url = source.normalized_url if source else ""
        content = await self.storage.get_object(snapshot.object_key)
        if snapshot.content_type not in {"text/html", "application/xhtml+xml"}:
            return []
        blocks = self.parser.parse_html_to_blocks(
            snapshot.workspace_id,
            snapshot.id,
            content.decode("utf-8", errors="replace"),
            source_url=source_url,
        )
        return [
            str(block.block_metadata["href"])
            for block in blocks
            if block.block_type == "link" and block.block_metadata.get("href")
        ]

    async def _fetch_with_retries(
        self, url: str, attempt: SourceFetchAttempt
    ) -> _HttpResponse | _FetchFailure:
        for retry_index in range(self.max_retries + 1):
            response = await self._fetch_http_once(url, attempt)
            if not isinstance(response, _FetchFailure) or not response.retryable:
                return response
            if retry_index >= self.max_retries:
                response.outcome_code = "retry_exhausted"
                response.message = "Retry limit exhausted."
                response.retryable = False
                return response
            attempt.retry_count = retry_index + 1
            await asyncio.sleep(min(1.0, 0.1 * (2**retry_index)))
        return _FetchFailure(500, url, "retry_exhausted", "Retry limit exhausted.")

    async def _fetch_http_once(
        self, url: str, attempt: SourceFetchAttempt
    ) -> _HttpResponse | _FetchFailure:
        current_url = url
        redirect_count = 0
        while True:
            safe, safety_reason = validate_url_safety(current_url)
            attempt.policy_result = "allowed" if safe else safety_reason
            if not safe:
                return _FetchFailure(
                    400,
                    current_url,
                    "redirect_blocked",
                    f"SSRF_REDIRECT_BLOCKED:{safety_reason}",
                    redirect_count=redirect_count,
                )
            domain = (urlparse(current_url).hostname or "unknown").lower()
            async with self._domain_limiter.acquire(domain):
                response = await self.http_transport.get(
                    current_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": ", ".join(sorted(_ALLOWED_MIME_TYPES)),
                    },
                )
            if isinstance(response, TransportFailure):
                return self._transport_failure(response, current_url, redirect_count)
            adapter = "httpx_legacy_tls" if response.tls_mode == "legacy" else "httpx"
            attempt.adapter = adapter
            attempt.http_status = response.status_code
            attempt.final_url = response.url
            attempt.redirect_count = redirect_count
            if response.status_code in _REDIRECT_STATUSES:
                if redirect_count >= self.max_redirects:
                    return _FetchFailure(
                        response.status_code,
                        current_url,
                        "max_redirects",
                        "Maximum redirect count exceeded.",
                        redirect_count=redirect_count,
                    )
                location = response.headers.get("location")
                if not location:
                    return _FetchFailure(
                        response.status_code,
                        current_url,
                        "http_error",
                        "Redirect response did not include a location.",
                        redirect_count=redirect_count,
                    )
                next_url = urljoin(response.url or current_url, location)
                next_safe, next_reason = validate_url_safety(next_url)
                if not next_safe:
                    return _FetchFailure(
                        400,
                        next_url,
                        "redirect_blocked",
                        f"SSRF_REDIRECT_BLOCKED:{next_reason}",
                        redirect_count=redirect_count + 1,
                    )
                current_url = next_url
                redirect_count += 1
                continue

            content_type = self._normalized_content_type(
                response.headers.get("content-type", ""), response.url or current_url
            )
            content = response.content
            attempt.content_type = content_type
            attempt.byte_count = len(content)
            if len(content) > self.max_decompressed_bytes:
                return _FetchFailure(
                    response.status_code,
                    response.url or current_url,
                    "decompression_exceeded"
                    if response.headers.get("content-encoding")
                    else "size_exceeded",
                    "Decoded response exceeded the configured byte limit.",
                    redirect_count=redirect_count,
                )
            if response.status_code in _RETRYABLE_STATUSES:
                return _FetchFailure(
                    response.status_code,
                    response.url or current_url,
                    "http_error",
                    f"HTTP {response.status_code}",
                    retryable=True,
                    redirect_count=redirect_count,
                )
            return _HttpResponse(
                status_code=response.status_code,
                final_url=response.url or current_url,
                content_type=content_type,
                content=content,
                headers=response.headers,
                redirect_count=redirect_count,
                adapter=adapter,
            )

    @staticmethod
    def _transport_failure(
        failure: TransportFailure, current_url: str, redirect_count: int
    ) -> _FetchFailure:
        outcome_code = failure.code.value
        if failure.code == TransportFailureCode.SSRF_BLOCKED:
            outcome_code = "redirect_blocked"
        elif failure.code == TransportFailureCode.HTTP_CLIENT:
            outcome_code = "http_error"
        status_code = 408 if failure.code == TransportFailureCode.TIMEOUT else 0
        return _FetchFailure(
            status_code,
            current_url,
            outcome_code,
            failure.message,
            retryable=failure.retryable,
            redirect_count=redirect_count,
        )

    async def _fetch_browser_fallback(
        self, url: str, attempt: SourceFetchAttempt, redirect_count: int
    ) -> _HttpResponse | _FetchFailure:
        if not self.settings.fetch_browser_fallback_enabled:
            return _FetchFailure(0, url, "policy_blocked", "Browser fallback is disabled.")
        if self._browser_fallbacks_used >= max(0, self.settings.fetch_browser_fallback_max_pages):
            return _FetchFailure(429, url, "policy_blocked", "Browser fallback budget exhausted.")
        if evaluate_robots_policy(url, self.user_agent) != "allowed":
            return _FetchFailure(
                403,
                url,
                "policy_blocked",
                "Browser fallback policy disallows URL.",
            )
        robots_decision, robots_reason = await self._browser_robots_policy(url)
        if robots_decision != "allowed":
            return _FetchFailure(
                403 if robots_decision == "blocked" else 0,
                url,
                "policy_blocked",
                robots_reason,
            )
        safe, reason = validate_url_safety(url)
        if not safe:
            return _FetchFailure(400, url, "redirect_blocked", f"SSRF_PREVENTION:{reason}")

        self._browser_fallbacks_used += 1
        rendered = await self.browser_adapter.fetch_rendered_page(url)
        if rendered.http_status == 0 or rendered.reason != "browser_rendered":
            return _FetchFailure(
                rendered.http_status,
                rendered.final_url,
                "browser_unavailable",
                rendered.reason or "BROWSER_UNAVAILABLE",
                redirect_count=redirect_count,
            )
        final_safe, final_reason = validate_url_safety(rendered.final_url)
        if not final_safe:
            return _FetchFailure(
                400,
                rendered.final_url,
                "redirect_blocked",
                f"SSRF_BROWSER_FINAL_URL_BLOCKED:{final_reason}",
                redirect_count=redirect_count,
            )
        content = rendered.content_html.encode("utf-8")
        if len(content) > self.max_decompressed_bytes:
            return _FetchFailure(
                rendered.http_status,
                rendered.final_url,
                "decompression_exceeded",
                "Browser response exceeded the decoded byte limit.",
                redirect_count=redirect_count,
            )
        content_type = self._normalized_content_type(rendered.content_type, rendered.final_url)
        mime_error = self._validate_mime(content_type, rendered.final_url, content)
        if mime_error is not None:
            return _FetchFailure(
                rendered.http_status,
                rendered.final_url,
                "mime_rejected",
                mime_error,
                redirect_count=redirect_count,
            )
        attempt.adapter = "playwright"
        attempt.policy_result = "browser_allowed"
        return _HttpResponse(
            status_code=rendered.http_status,
            final_url=rendered.final_url,
            content_type=content_type,
            content=content,
            headers=httpx.Headers({"content-type": content_type}),
            redirect_count=redirect_count,
        )

    async def _browser_robots_policy(self, url: str) -> tuple[str, str]:
        """Resolve robots policy before browser rendering without bypassing access controls."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = await self.http_transport.get(
            robots_url,
            headers={"User-Agent": self.user_agent, "Accept": "text/plain"},
        )
        if isinstance(response, TransportFailure):
            return "unknown", f"BROWSER_ROBOTS_UNAVAILABLE:{response.code.value.upper()}"
        if response.status_code in {401, 403}:
            return "blocked", f"BROWSER_ROBOTS_ACCESS_CONTROL_HTTP_{response.status_code}"
        if 400 <= response.status_code < 500:
            return "allowed", f"BROWSER_ROBOTS_NOT_PUBLISHED_HTTP_{response.status_code}"
        if response.status_code != 200:
            return "unknown", f"BROWSER_ROBOTS_UNAVAILABLE_HTTP_{response.status_code}"
        parser = RobotFileParser(robots_url)
        parser.parse(response.content.decode("utf-8-sig", errors="replace").splitlines())
        if not parser.can_fetch(self.user_agent, url):
            return "blocked", "BROWSER_ROBOTS_DISALLOWED"
        return "allowed", "BROWSER_ROBOTS_ALLOWED"

    def _should_use_browser(
        self, status_code: int, content_type: str, content: bytes, url: str
    ) -> bool:
        """Detect a JS-like page without using browser mode as an access bypass."""
        if not self.settings.fetch_browser_fallback_enabled:
            return False
        if evaluate_robots_policy(url, self.user_agent) != "allowed":
            return False
        if status_code in {401, 403, 407, 429}:
            return False
        if status_code in {404, 410}:
            return True
        if status_code != 200 or not content_type.startswith(("text/html", "application/xhtml")):
            return False
        text = re.sub(r"<[^>]+>", " ", content.decode("utf-8", errors="ignore"))
        return len(" ".join(text.split())) < 80 and (
            b"<script" in content.lower() or b'id="root"' in content.lower()
        )

    async def _get_or_create_source(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        url: str,
        normalized_url: str,
        domain: str,
        source_type: str,
    ) -> Source:
        source_stmt = select(Source).where(
            Source.workspace_id == workspace_id,
            Source.company_id == company_id,
            Source.normalized_url == normalized_url,
        )
        source_result = await self.session.execute(source_stmt)
        source = source_result.scalar_one_or_none()
        if source is None:
            source = Source(
                workspace_id=workspace_id,
                company_id=company_id,
                canonical_url=url,
                normalized_url=normalized_url,
                domain=domain,
                source_type=source_type,
                status="discovered",
            )
            self.session.add(source)
            await self.session.flush()
        return source

    async def _latest_snapshot(self, source_id: uuid.UUID) -> SourceSnapshot | None:
        stmt = (
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.retrieved_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _snapshot_by_hash(
        self, source_id: uuid.UUID, content_hash: str
    ) -> SourceSnapshot | None:
        stmt = select(SourceSnapshot).where(
            SourceSnapshot.source_id == source_id,
            SourceSnapshot.content_hash == content_hash,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _failure_result(
        self,
        source: Source,
        attempt: SourceFetchAttempt,
        *,
        status_code: int,
        outcome_code: str,
        message: str,
        final_url: str | None = None,
        redirect_count: int = 0,
        adapter: str = "httpx",
    ) -> FetchResult:
        """Persist only sanitized failure metadata and return a typed result."""
        attempt.adapter = adapter
        attempt.final_url = final_url
        attempt.http_status = status_code or None
        attempt.redirect_count = redirect_count
        attempt.outcome_code = outcome_code
        attempt.error_message = message[:500]
        attempt.retryable = outcome_code in {
            "timeout",
            "connect_error",
            "http_error",
            "retry_exhausted",
        }
        attempt.completed_at = datetime.now(UTC)
        await self.session.flush()
        return FetchResult(
            source=source,
            snapshot=None,
            status_code=status_code,
            adapter_used=adapter,
            error_message=message[:500],
            final_url=final_url,
            redirect_count=redirect_count,
            retry_count=attempt.retry_count,
        )

    @staticmethod
    def _normalized_content_type(content_type: str, url: str) -> str:
        normalized = (content_type or "").split(";", 1)[0].strip().lower()
        if normalized:
            return normalized
        path = urlparse(url).path.lower()
        if path.endswith(".pdf"):
            return "application/pdf"
        if path.endswith((".json", ".jsonld")):
            return "application/json"
        return "text/html"

    @staticmethod
    def _validate_mime(content_type: str, url: str, content: bytes) -> str | None:
        if content_type not in _ALLOWED_MIME_TYPES and not content_type.endswith(("+json", "+xml")):
            return f"Unsupported MIME type: {content_type or 'missing'}."
        path = urlparse(url).path.lower()
        if path.endswith(".pdf") and content_type != "application/pdf":
            return "PDF extension does not match response MIME type."
        if content.lstrip().startswith(b"%PDF") and content_type != "application/pdf":
            return "PDF signature does not match response MIME type."
        if content_type == "application/pdf" and not content.lstrip().startswith(b"%PDF"):
            return "PDF MIME type does not contain a valid PDF signature."
        return None

    @staticmethod
    def _storage_suffix(content_type: str) -> str:
        return {
            "application/pdf": ".pdf",
            "application/json": ".json",
            "application/ld+json": ".json",
        }.get(content_type, ".json" if content_type.endswith("+json") else ".html")

    @staticmethod
    def _parser_version(content_type: str, url: str) -> str:
        if content_type == "application/pdf" or url.lower().endswith(".pdf"):
            return PDF_PARSER_VERSION
        if content_type in {"application/json", "application/ld+json"} or content_type.endswith(
            "+json"
        ):
            return STRUCTURED_PARSER_VERSION
        return HTML_PARSER_VERSION

    @staticmethod
    def _initial_language(content_type: str, content: bytes) -> str:
        if content_type in {"text/html", "application/xhtml+xml", "text/plain"}:
            return DocumentParser.detect_language(content.decode("utf-8", errors="replace"))
        return "und"


def json_loads_bytes(content: bytes) -> Any:
    """Decode JSON with a bounded, explicit UTF-8 contract."""
    return json.loads(content.decode("utf-8"))


@dataclass(slots=True)
class CrawledPage:
    """One page result returned by ``CrawlCoordinator``."""

    url: str
    depth: int
    result: FetchResult


class CrawlCoordinator:
    """Run a finite same-domain crawl using the HTTP-first ``WebFetcher``."""

    def __init__(
        self,
        fetcher: WebFetcher,
        *,
        max_depth: int = 1,
        max_pages_per_domain: int = 25,
        max_pages_per_job: int = 50,
    ) -> None:
        self.fetcher = fetcher
        self.max_depth = max(0, min(max_depth, 5))
        self.max_pages_per_domain = max(1, min(max_pages_per_domain, 500))
        self.max_pages_per_job = max(1, min(max_pages_per_job, 500))

    async def crawl(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        urls: Sequence[str],
        *,
        research_job_id: uuid.UUID | None = None,
        source_type: str = "web_page",
        source_type_by_url: Mapping[str, str] | None = None,
        parse_content: bool = False,
    ) -> list[CrawledPage]:
        """Fetch seed URLs and safe same-domain links within explicit budgets."""
        queue: list[tuple[str, int, str]] = []
        seen: set[str] = set()
        for raw_url in urls:
            safe, _ = validate_url_safety(raw_url)
            canonical = normalize_url(raw_url) if safe else raw_url
            if canonical and canonical not in seen:
                queue.append((canonical, 0, source_type))
                seen.add(canonical)

        pages: list[CrawledPage] = []
        domain_counts: dict[str, int] = {}
        while queue and len(pages) < self.max_pages_per_job:
            current_url, depth, discovered_type = queue.pop(0)
            domain = (urlparse(current_url).hostname or "").lower()
            if domain_counts.get(domain, 0) >= self.max_pages_per_domain:
                continue
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            result = await self.fetcher.fetch_and_store_source(
                workspace_id=workspace_id,
                company_id=company_id,
                url=current_url,
                source_type=(source_type_by_url or {}).get(current_url, discovered_type),
                research_job_id=research_job_id,
                parse_content=parse_content,
            )
            pages.append(CrawledPage(url=current_url, depth=depth, result=result))
            if result.snapshot is None or depth >= self.max_depth:
                continue
            try:
                links = await self.fetcher.discover_links(result.snapshot)
            except Exception:
                continue
            root_domain = domain
            for link in links:
                safe, _ = validate_url_safety(link)
                if not safe:
                    continue
                canonical_link = normalize_url(link)
                link_domain = (urlparse(canonical_link).hostname or "").lower()
                if link_domain != root_domain or canonical_link in seen:
                    continue
                seen.add(canonical_link)
                queue.append((canonical_link, depth + 1, "official_site"))
        return pages
