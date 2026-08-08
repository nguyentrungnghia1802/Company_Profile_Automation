"""Web fetcher service for acquiring web source documents safely."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING
from urllib.parse import urlparse

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
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.integrations.storage.mock_malware import MockMalwareScanner
from company_profile.modules.sources.browser_adapter import PlaywrightBrowserAdapter
from company_profile.modules.sources.parser import DocumentParser, PDFDocumentParser
from company_profile.modules.sources.validator import validate_url_safety

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("company_profile.sources.fetcher")


class FetchResult:
    """Result envelope of a web source fetch operation."""

    def __init__(
        self,
        source: Source,
        snapshot: SourceSnapshot | None,
        status_code: int,
        content_type: str = "text/html",
        adapter_used: str = "httpx",
        error_message: str | None = None,
    ) -> None:
        self.source = source
        self.snapshot = snapshot
        self.status_code = status_code
        self.content_type = content_type
        self.adapter_used = adapter_used
        self.error_message = error_message


class WebFetcher:
    """Web source fetcher service enforcing timeouts, size limits, and security scans."""

    def __init__(
        self,
        session: AsyncSession,
        storage: LocalObjectStorage | None = None,
        malware_scanner: MockMalwareScanner | None = None,
    ) -> None:
        self.session = session
        settings = get_settings()
        self.settings = settings
        self.storage = storage or LocalObjectStorage(settings.local_storage_root)
        self.malware_scanner = malware_scanner or MockMalwareScanner()
        self.parser = DocumentParser()
        self.browser_adapter = PlaywrightBrowserAdapter(timeout_seconds=settings.fetch_timeout)
        self.user_agent = settings.fetch_user_agent
        self.timeout = settings.fetch_timeout
        self.max_bytes = settings.fetch_max_response_bytes

    async def fetch_and_store_source(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        url: str,
        source_type: str = "web_page",
        research_job_id: uuid.UUID | None = None,
        parse_content: bool = True,
    ) -> FetchResult:
        """Fetch a source idempotently and persist its immutable snapshot.

        ``parse_content`` remains enabled by default for the public fetcher API.
        The research pipeline disables it so fetch and document parsing are
        separate durable steps.
        """
        is_safe, safety_reason = validate_url_safety(url)

        norm_url = (
            normalize_url(url) if is_safe or "UNSUPPORTED_SCHEME" not in safety_reason else url
        )
        try:
            parsed = urlparse(norm_url)
            domain = parsed.netloc or "unknown"
        except Exception:
            domain = "unknown"

        async with transactional(self.session):
            # Reuse the canonical source record on retries. The unique URL
            # boundary is intentionally resolved before network I/O.
            source_stmt = select(Source).where(
                Source.workspace_id == workspace_id,
                Source.company_id == company_id,
                Source.normalized_url == norm_url,
            )
            source_result = await self.session.execute(source_stmt)
            source = source_result.scalar_one_or_none()
            if source is None:
                source = Source(
                    workspace_id=workspace_id,
                    company_id=company_id,
                    canonical_url=url,
                    normalized_url=norm_url,
                    domain=domain,
                    source_type=source_type,
                    status="discovered",
                )
                self.session.add(source)
                await self.session.flush()

            attempt = SourceFetchAttempt(
                workspace_id=workspace_id,
                source_id=source.id,
                research_job_id=research_job_id,
                adapter="httpx",
                requested_url=url,
            )
            self.session.add(attempt)
            await self.session.flush()

            if not is_safe:
                source.status = "rejected"
                attempt.outcome_code = "malware_detected"
                attempt.error_message = safety_reason
                return FetchResult(
                    source=source,
                    snapshot=None,
                    status_code=400,
                    error_message=f"SSRF_PREVENTION: {safety_reason}",
                )

            # A completed snapshot is the idempotency result for duplicate
            # delivery. A new attempt is still recorded for auditability.
            snapshot_stmt = (
                select(SourceSnapshot)
                .where(SourceSnapshot.source_id == source.id)
                .order_by(SourceSnapshot.retrieved_at.desc())
            )
            snapshot_result = await self.session.execute(snapshot_stmt)
            existing_snapshot = snapshot_result.scalars().first()
            if existing_snapshot is not None:
                if parse_content:
                    await self.parse_snapshot(existing_snapshot)
                source.status = "fetched"
                attempt.outcome_code = "success"
                attempt.final_url = source.canonical_url
                attempt.http_status = 200
                attempt.content_type = existing_snapshot.content_type
                attempt.byte_count = existing_snapshot.byte_size
                return FetchResult(
                    source=source,
                    snapshot=existing_snapshot,
                    status_code=200,
                    content_type=existing_snapshot.content_type,
                )

            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    headers = {"User-Agent": self.user_agent}
                    response = await client.get(url, headers=headers)

                attempt.final_url = str(response.url)
                attempt.http_status = response.status_code
                attempt.content_type = response.headers.get("content-type", "text/html")
                attempt.byte_count = len(response.content)

                content_bytes = response.content
                adapter_used = "httpx"

                response_status = response.status_code
                response_content_type = response.headers.get("content-type", "text/html")

                if (
                    response_status != 200 or len(content_bytes) < 100
                ) and self.settings.fetch_browser_fallback_enabled:
                    rendered = await self.browser_adapter.fetch_rendered_page(url)
                    if rendered.http_status == 200 and rendered.content_html:
                        content_bytes = rendered.content_html.encode("utf-8")
                        attempt.adapter = "playwright"
                        adapter_used = "playwright"
                        response_status = rendered.http_status
                        response_content_type = rendered.content_type
                        attempt.http_status = rendered.http_status
                        attempt.final_url = rendered.final_url
                        attempt.byte_count = len(content_bytes)
                        logger.info(
                            "Used browser fallback for %s (reason: %s)", url, rendered.reason
                        )

                if response_status != 200 and adapter_used == "httpx":
                    attempt.outcome_code = "http_error"
                    source.status = "failed"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=response_status,
                        adapter_used=adapter_used,
                        error_message=f"HTTP {response.status_code}",
                    )

                if len(content_bytes) > self.max_bytes:
                    attempt.outcome_code = "size_exceeded"
                    source.status = "failed"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=200,
                        adapter_used=adapter_used,
                        error_message="Response exceeded max byte limit.",
                    )

                content_hash = calculate_content_hash(content_bytes)
                content_type = response_content_type.split(";")[0].lower()

                # A retry can download the same immutable body after a worker
                # crash. Reuse its snapshot rather than creating a duplicate.
                same_hash_stmt = select(SourceSnapshot).where(
                    SourceSnapshot.source_id == source.id,
                    SourceSnapshot.content_hash == content_hash,
                )
                same_hash_result = await self.session.execute(same_hash_stmt)
                same_hash_snapshot = same_hash_result.scalar_one_or_none()
                if same_hash_snapshot is not None:
                    if parse_content:
                        await self.parse_snapshot(same_hash_snapshot)
                    source.status = "fetched"
                    attempt.outcome_code = "success"
                    attempt.final_url = str(response.url)
                    attempt.http_status = response_status
                    attempt.content_type = content_type
                    attempt.byte_count = len(content_bytes)
                    return FetchResult(
                        source=source,
                        snapshot=same_hash_snapshot,
                        status_code=response_status,
                        content_type=content_type,
                        adapter_used=adapter_used,
                    )

                # Malware scan
                is_clean, scan_desc = await self.malware_scanner.scan_bytes(content_bytes)
                if not is_clean:
                    attempt.outcome_code = "malware_detected"
                    source.status = "rejected"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=200,
                        adapter_used=adapter_used,
                        error_message=f"Malware scan failed: {scan_desc}",
                    )

                # Store object in ObjectStorage
                object_key = f"{workspace_id}/{company_id}/{content_hash}.html"
                await self.storage.put_object(object_key, content_bytes, content_type=content_type)

                # Create SourceSnapshot record
                snapshot = SourceSnapshot(
                    workspace_id=workspace_id,
                    source_id=source.id,
                    content_hash=content_hash,
                    storage_provider="local",
                    object_key=object_key,
                    content_type=content_type,
                    byte_size=len(content_bytes),
                    malware_scan_status="clean",
                )
                self.session.add(snapshot)
                await self.session.flush()

                # Parsing is optional here so the durable research pipeline can
                # record fetch and parse as separate steps.
                blocks: list[DocumentBlock] = []
                if parse_content:
                    blocks = await self.parse_snapshot(snapshot)

                source.status = "fetched"
                attempt.outcome_code = "success"
                await self.session.flush()

                logger.info(
                    "Fetched and stored source snapshot with document blocks",
                    extra={
                        "source_id": str(source.id),
                        "content_hash": content_hash,
                        "byte_size": len(content_bytes),
                        "blocks_count": len(blocks),
                    },
                )
                return FetchResult(
                    source=source,
                    snapshot=snapshot,
                    status_code=200,
                    content_type=content_type,
                    adapter_used=adapter_used,
                )

            except Exception as exc:
                source.status = "failed"
                logger.error("Web fetcher failed for URL %s: %s", url, exc, exc_info=True)
                return FetchResult(
                    source=source, snapshot=None, status_code=500, error_message=str(exc)
                )

    async def parse_snapshot(self, snapshot: SourceSnapshot) -> list[DocumentBlock]:
        """Parse a stored snapshot exactly once and return stable document blocks."""
        existing_stmt = select(DocumentBlock).where(DocumentBlock.source_snapshot_id == snapshot.id)
        existing_result = await self.session.execute(existing_stmt)
        existing_blocks = list(existing_result.scalars().all())
        if existing_blocks:
            return existing_blocks

        content = await self.storage.get_object(snapshot.object_key)
        source = await self.session.get(Source, snapshot.source_id)
        source_url = source.normalized_url if source else ""
        is_pdf = snapshot.content_type == "application/pdf" or source_url.lower().endswith(".pdf")
        if is_pdf:
            blocks = PDFDocumentParser().parse_pdf_to_blocks(
                snapshot.workspace_id, snapshot.id, content
            )
        else:
            html_content = content.decode("utf-8", errors="replace")
            blocks = self.parser.parse_html_to_blocks(
                snapshot.workspace_id, snapshot.id, html_content
            )

        for block in blocks:
            self.session.add(block)
        await self.session.flush()
        return blocks
