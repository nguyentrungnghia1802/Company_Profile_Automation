"""Web fetcher service for acquiring web source documents safely."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from company_profile.config.settings import get_settings
from company_profile.db.models.source import (
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
    calculate_content_hash,
    normalize_url,
)
from company_profile.db.transaction import transactional
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.integrations.storage.mock_malware import MockMalwareScanner
from company_profile.modules.sources.parser import DocumentParser

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
        error_message: str | None = None,
    ) -> None:
        self.source = source
        self.snapshot = snapshot
        self.status_code = status_code
        self.content_type = content_type
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
        self.storage = storage or LocalObjectStorage(settings.local_storage_root)
        self.malware_scanner = malware_scanner or MockMalwareScanner()
        self.parser = DocumentParser()
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
    ) -> FetchResult:
        """Fetch web document from URL, scan for malware, store in storage, and persist snapshot."""
        norm_url = normalize_url(url)
        parsed = urlparse(norm_url)
        domain = parsed.netloc

        async with transactional(self.session):
            # Create or retrieve Source record
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

            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    headers = {"User-Agent": self.user_agent}
                    response = await client.get(url, headers=headers)

                attempt.final_url = str(response.url)
                attempt.http_status = response.status_code
                attempt.content_type = response.headers.get("content-type", "text/html")
                attempt.byte_count = len(response.content)

                if response.status_code != 200:
                    attempt.outcome_code = "http_error"
                    source.status = "failed"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=response.status_code,
                        error_message=f"HTTP {response.status_code}",
                    )

                content_bytes = response.content
                if len(content_bytes) > self.max_bytes:
                    attempt.outcome_code = "size_exceeded"
                    source.status = "failed"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=200,
                        error_message="Response exceeded max byte limit.",
                    )

                content_hash = calculate_content_hash(content_bytes)
                content_type = response.headers.get("content-type", "text/html").split(";")[0]

                # Malware scan
                is_clean, scan_desc = await self.malware_scanner.scan_bytes(content_bytes)
                if not is_clean:
                    attempt.outcome_code = "malware_detected"
                    source.status = "rejected"
                    return FetchResult(
                        source=source,
                        snapshot=None,
                        status_code=200,
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

                # Extract HTML text blocks into DocumentBlock records
                html_str = content_bytes.decode("utf-8", errors="replace")
                blocks = self.parser.parse_html_to_blocks(workspace_id, snapshot.id, html_str)
                for b in blocks:
                    self.session.add(b)

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
                )

            except Exception as exc:
                source.status = "failed"
                logger.error("Web fetcher failed for URL %s: %s", url, exc, exc_info=True)
                return FetchResult(
                    source=source, snapshot=None, status_code=500, error_message=str(exc)
                )
