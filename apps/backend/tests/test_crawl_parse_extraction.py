"""Regression tests for bounded crawling, parser metadata, and direct facts."""

from __future__ import annotations

import tempfile
import uuid
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
from httpx import Request, Response
from pypdf import PdfWriter
from pypdf._page import PageObject
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import select

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import Evidence, FactCandidate
from company_profile.db.models.identity import Workspace
from company_profile.db.models.research import ResearchJob
from company_profile.db.models.source import (
    DocumentBlock,
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
)
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.facts.deterministic import DeterministicFactExtractor
from company_profile.modules.sources.fetcher import CrawlCoordinator, WebFetcher
from company_profile.modules.sources.parser import DocumentParser, PDFDocumentParser
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def test_html_parser_preserves_metadata_sections_links_and_language() -> None:
    """HTML output is stable and contains source-addressable semantic metadata."""
    parser = DocumentParser()
    workspace_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    html = """
    <html lang="vi"><head>
      <title>Hồ sơ chính thức</title>
      <meta property="og:title" content="Công ty Structured" />
      <script type="application/ld+json">
        {"@type":"Organization","name":"Structured Corp","taxID":"0312345678"}
      </script>
    </head><body>
      <h1>Giới thiệu</h1>
      <p>Thông tin công ty chính thức.</p>
      <h2>Sản phẩm</h2>
      <ul><li>Dịch vụ phần mềm</li></ul>
      <table><tr><td>Tax ID</td><td>0312345678</td></tr></table>
      <a href="/contact">Liên hệ</a>
    </body></html>
    """

    first = parser.parse_html_to_blocks(
        workspace_id,
        snapshot_id,
        html,
        source_url="https://structured.example.com/",
    )
    second = parser.parse_html_to_blocks(
        workspace_id,
        snapshot_id,
        html,
        source_url="https://structured.example.com/",
    )

    assert [(block.block_key, block.block_hash) for block in first] == [
        (block.block_key, block.block_hash) for block in second
    ]
    assert any(block.block_type == "title" and "Hồ sơ" in block.text_content for block in first)
    assert any(
        block.block_type == "metadata" and block.block_metadata.get("kind") == "opengraph"
        for block in first
    )
    structured = next(block for block in first if block.block_type == "table")
    assert structured.block_metadata["format"] == "json-ld"
    assert "$.taxID" in structured.block_metadata["field_paths"]
    assert structured.language == "vi"
    assert structured.parser_version == "html-1.0"
    paragraph = next(block for block in first if block.block_type == "paragraph")
    assert paragraph.section_path == ["Giới thiệu"]
    link = next(block for block in first if block.block_type == "link")
    assert link.block_metadata["href"] == "https://structured.example.com/contact"


def test_structured_parser_preserves_paths_and_provenance() -> None:
    """Structured/API payloads retain field paths and an evidence location."""
    parser = DocumentParser()
    blocks = parser.parse_json_to_blocks(
        uuid.uuid4(),
        uuid.uuid4(),
        {"company": {"name": "API Corp", "tax_id": "123"}, "items": [{"name": "A"}]},
        source_url="https://registry.example/api/company/1",
        provenance={"provider": "fixture-registry", "record_id": "1"},
    )

    assert len(blocks) == 1
    block = blocks[0]
    assert block.block_type == "structured"
    assert "$.company.name" in block.block_metadata["field_paths"]
    assert block.block_metadata["provenance"] == {
        "source_url": "https://registry.example/api/company/1",
        "evidence_location": "$",
        "provider": "fixture-registry",
        "record_id": "1",
    }


def test_pdf_parser_keeps_page_evidence_and_rejects_malformed_pdf() -> None:
    """PDF parsing is page-addressable and malformed input fails closed."""
    page = PageObject.create_blank_page(width=300, height=300)
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 200 Td (Page one evidence) Tj ET")
    page[NameObject("/Contents")] = stream
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    writer = PdfWriter()
    writer.add_page(page)
    output = BytesIO()
    writer.write(output)

    parser = PDFDocumentParser(max_bytes=10_000)
    blocks = parser.parse_pdf_to_blocks(
        uuid.uuid4(),
        uuid.uuid4(),
        output.getvalue(),
    )
    assert len(blocks) == 1
    assert blocks[0].block_key == "p1_b1"
    assert blocks[0].page_number == 1
    assert blocks[0].location == {"kind": "pdf", "page": 1, "block": 1}
    assert "Page one evidence" in blocks[0].text_content
    assert parser.parse_pdf_to_blocks(uuid.uuid4(), uuid.uuid4(), b"%PDF-bad") == []
    assert parser.parse_pdf_to_blocks(uuid.uuid4(), uuid.uuid4(), b"%PDF" + b"x" * 10_000) == []


@pytest.mark.asyncio
async def test_crawl_coordinator_is_bounded_and_same_domain(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Crawler follows one same-domain link but never crosses the domain/budget."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(name="Crawler WS", slug="crawler-ws")
    )
    company = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Crawler Corp",
            normalized_name="crawler corp",
        )
    )
    pages = {
        "": b'<h1>Crawler Corp</h1><a href="/about">About</a><a href="https://other.example/about">Other</a>',
        "/about": b"<h1>About Crawler Corp</h1><p>Public company information.</p>",
    }

    async def mock_get(_self: object, url: str, **_kwargs: object) -> Response:
        path = urlparse(url).path
        return Response(
            status_code=200,
            content=pages.get(path, b"<p>not found</p>"),
            headers={"content-type": "text/html; charset=utf-8"},
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        coordinator = CrawlCoordinator(
            fetcher,
            max_depth=1,
            max_pages_per_domain=2,
            max_pages_per_job=2,
        )
        crawled = await coordinator.crawl(
            workspace.id,
            company.id,
            ["https://crawl.example.com"],
            parse_content=False,
        )

    assert [page.url for page in crawled] == [
        "https://crawl.example.com",
        "https://crawl.example.com/about",
    ]
    assert len((await db_session.execute(select(SourceSnapshot))).scalars().all()) == 2


@pytest.mark.asyncio
async def test_fetcher_revalidates_redirect_and_retries_with_limits(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redirect SSRF is blocked before its second request and retries are bounded."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(name="Safety WS", slug="safety-crawl-ws")
    )
    company = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Safety Corp",
            normalized_name="safety corp",
        )
    )
    calls: list[str] = []

    async def redirect_get(_self: object, url: str, **_kwargs: object) -> Response:
        calls.append(url)
        return Response(
            status_code=302,
            headers={"location": "http://127.0.0.1/private"},
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", redirect_get)
    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        result = await fetcher.fetch_and_store_source(
            workspace.id,
            company.id,
            "https://safety.example.com/",
        )

    assert result.snapshot is None
    assert result.status_code == 400
    assert calls == ["https://safety.example.com/"]
    attempt = (await db_session.execute(select(SourceFetchAttempt))).scalar_one()
    assert attempt.outcome_code == "redirect_blocked"
    assert attempt.redirect_count == 1


@pytest.mark.asyncio
async def test_fetcher_retry_and_mime_limits_are_audited(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transient responses retry only within budget and unsupported MIME is rejected."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(name="Retry MIME WS", slug="retry-mime-ws")
    )
    company = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Retry Corp",
            normalized_name="retry corp",
        )
    )
    call_count = 0

    async def retry_get(_self: object, url: str, **_kwargs: object) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return Response(503, content=b"busy", request=Request("GET", url))
        return Response(
            200,
            content=b"<h1>Retry Corp</h1>",
            headers={"content-type": "text/html"},
            request=Request("GET", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.get", retry_get)
    with tempfile.TemporaryDirectory() as temp_dir:
        fetcher = WebFetcher(db_session, storage=LocalObjectStorage(temp_dir))
        fetcher.max_retries = 2
        success = await fetcher.fetch_and_store_source(
            workspace.id,
            company.id,
            "https://retry.example.com/",
        )
        assert success.snapshot is not None

        async def mime_get(_self: object, url: str, **_kwargs: object) -> Response:
            return Response(
                200,
                content=b"binary",
                headers={"content-type": "application/octet-stream"},
                request=Request("GET", url),
            )

        monkeypatch.setattr("httpx.AsyncClient.get", mime_get)
        rejected = await fetcher.fetch_and_store_source(
            workspace.id,
            company.id,
            "https://mime.example.com/",
        )

    assert call_count == 3
    assert rejected.snapshot is None
    attempts = (await db_session.execute(select(SourceFetchAttempt))).scalars().all()
    assert any(
        attempt.retry_count == 2 and attempt.outcome_code == "success" for attempt in attempts
    )
    assert any(attempt.outcome_code == "mime_rejected" for attempt in attempts)


@pytest.mark.asyncio
async def test_structured_facts_have_document_block_evidence(db_session: AsyncSession) -> None:
    """Deterministic structured fields create candidates linked to exact blocks."""
    workspace = await WorkspaceRepository(db_session).create(
        Workspace(name="Facts WS", slug="structured-facts-ws")
    )
    company = await CompanyRepository(db_session).create(
        CompanyProfile(
            workspace_id=workspace.id,
            company_name="Structured Corp",
            normalized_name="structured corp",
        )
    )
    job = ResearchJob(
        workspace_id=workspace.id,
        company_id=company.id,
        job_type="initial",
        scope="{}",
        status="running",
    )
    source = Source(
        workspace_id=workspace.id,
        company_id=company.id,
        canonical_url="https://structured.example/",
        normalized_url="https://structured.example",
        domain="structured.example",
        source_type="official_site",
        authority_tier=2,
    )
    snapshot = SourceSnapshot(
        workspace_id=workspace.id,
        source=source,
        content_hash="a" * 64,
        object_key="structured.json",
        content_type="application/json",
        byte_size=100,
    )
    block = DocumentBlock(
        workspace_id=workspace.id,
        snapshot=snapshot,
        block_key="structured_0001",
        block_type="structured",
        text_content='{"name":"Structured Corp","taxID":"0312345678","url":"https://structured.example"}',
        block_hash="b" * 64,
        block_metadata={
            "format": "json",
            "field_paths": ["$.name", "$.taxID", "$.url"],
            "provenance": {"provider": "fixture"},
        },
    )
    db_session.add_all([job, source, snapshot, block])
    await db_session.flush()

    summary = await DeterministicFactExtractor(db_session).extract(
        workspace.id,
        company.id,
        job.id,
        [snapshot.id],
    )
    candidates = (await db_session.execute(select(FactCandidate))).scalars().all()
    evidence = (await db_session.execute(select(Evidence))).scalars().all()

    assert summary.fact_count == 3
    assert {candidate.field_key for candidate in candidates} == {
        "identity.legal_name",
        "identity.tax_id",
        "identity.website",
    }
    assert len(evidence) == 3
    assert {item.document_block_id for item in evidence} == {block.id}
