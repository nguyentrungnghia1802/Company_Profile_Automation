"""Unit tests for URL normalization, content hashing, search providers, and web fetcher."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from httpx import Request, Response
from sqlalchemy import select

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.source import DocumentBlock, calculate_content_hash, normalize_url
from company_profile.integrations.search.fixture_search import FixtureSearchProvider
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.sources.fetcher import WebFetcher
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def test_url_normalization_helper() -> None:
    """Verify URL normalization logic."""
    assert normalize_url("https://EXAMPLE.com/path/") == "https://example.com/path"
    assert normalize_url("http://example.com:80/") == "http://example.com"
    assert normalize_url("https://company.vn/about/") == "https://company.vn/about"


def test_content_hashing_helper() -> None:
    """Verify SHA-256 content hashing helper."""
    data = b"<html><body>Company Info</body></html>"
    hash_val = calculate_content_hash(data)
    assert len(hash_val) == 64
    assert hash_val == calculate_content_hash(data)


@pytest.mark.asyncio
async def test_fixture_search_provider() -> None:
    """Verify search provider returns structured search results."""
    provider = FixtureSearchProvider()
    results = await provider.search("AI Riser Viet Nam", locale="vi", num_results=5)
    assert len(results) > 0
    assert hasattr(results[0], "url")
    assert hasattr(results[0], "title")


@pytest.mark.asyncio
async def test_web_fetcher_fetch_and_store(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify WebFetcher fetches HTML, computes SHA256, scans malware, and stores snapshot."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Source WS", slug="source-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Source Test Corp",
            normalized_name="source test corp",
            status="published",
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalObjectStorage(temp_dir)
        fetcher = WebFetcher(db_session, storage=storage)

        # Mock httpx GET response
        mock_html = b"<html><body><h1>Source Test Corp Official Site</h1></body></html>"

        async def mock_get(_self: object, _url: str, **_kwargs: object) -> Response:
            return Response(
                status_code=200,
                content=mock_html,
                headers={"content-type": "text/html; charset=utf-8"},
                request=Request("GET", _url),
            )

        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

        res = await fetcher.fetch_and_store_source(
            workspace_id=ws.id,
            company_id=company.id,
            url="https://sourcetest.example.com/about",
        )

        assert res.status_code == 200
        assert res.source.status == "fetched"
        assert res.snapshot is not None
        assert res.snapshot.byte_size == len(mock_html)
        assert res.snapshot.content_hash == calculate_content_hash(mock_html)

        # Verify object stored in LocalObjectStorage
        stored_bytes = await storage.get_object(res.snapshot.object_key)
        assert stored_bytes == mock_html

        # Verify DocumentBlocks extracted
        block_stmt = select(DocumentBlock).where(
            DocumentBlock.source_snapshot_id == res.snapshot.id
        )
        block_res = await db_session.execute(block_stmt)
        blocks = block_res.scalars().all()
        assert len(blocks) == 1
        assert blocks[0].block_type == "heading"
        assert "Source Test Corp" in blocks[0].text_content
