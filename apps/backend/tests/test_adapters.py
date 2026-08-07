"""Unit and integration tests for mock adapters, storage, and transaction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from company_profile.db.transaction import transactional
from company_profile.integrations.ai.mock_ai import MockAiProvider
from company_profile.integrations.auth.mock_auth import MockActor, MockAuthProvider
from company_profile.integrations.fetch.fixture_fetcher import FixtureFetcher, FixtureFetchResponse
from company_profile.integrations.search.fixture_search import FixtureSearchProvider
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.integrations.storage.mock_malware import MockMalwareScanner

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_mock_auth_provider() -> None:
    """Verify mock auth provider token verification."""
    provider = MockAuthProvider(default_actor=MockActor(user_id="usr_001"))
    actor = await provider.verify_token("valid_token")
    assert actor.user_id == "usr_001"

    with pytest.raises(ValueError, match="AUTH_INVALID_TOKEN"):
        await provider.verify_token("invalid")


@pytest.mark.asyncio
async def test_fixture_fetcher() -> None:
    """Verify fixture fetcher response registration and fallback."""
    fetcher = FixtureFetcher()
    fetcher.register_fixture(
        "https://test.com", FixtureFetchResponse("https://test.com", 200, "Custom")
    )

    resp1 = await fetcher.fetch("https://test.com")
    assert resp1.content == "Custom"

    resp2 = await fetcher.fetch("https://unknown.com")
    assert resp2.status_code == 200
    assert "unknown.com" in resp2.content


@pytest.mark.asyncio
async def test_fixture_search_provider() -> None:
    """Verify fixture search provider returns candidates."""
    provider = FixtureSearchProvider()
    results = await provider.search("Example Company")
    assert len(results) > 0
    assert results[0].domain == "example.com"


@pytest.mark.asyncio
async def test_mock_ai_provider() -> None:
    """Verify mock AI provider extraction and translation."""
    ai = MockAiProvider()
    res = await ai.extract_facts([{"block_id": "blk_123"}])
    assert "facts" in res
    assert res["facts"][0]["evidence_block_id"] == "blk_123"

    tr = await ai.translate_text("Xin chào", "en")
    assert "en" in tr


@pytest.mark.asyncio
async def test_local_object_storage(tmp_path: Path) -> None:
    """Verify local filesystem object storage read/write."""
    storage = LocalObjectStorage(storage_root=str(tmp_path))
    key = "docs/snapshot_001.txt"
    data = b"Hello Storage"

    stored_path = await storage.put_object(key, data)
    assert stored_path is not None

    retrieved = await storage.get_object(key)
    assert retrieved == data

    url = await storage.generate_signed_url(key)
    assert "key=" in url


@pytest.mark.asyncio
async def test_mock_malware_scanner() -> None:
    """Verify mock malware scanner cleanly approves normal bytes and detects fixture EICAR."""
    scanner = MockMalwareScanner()
    clean_ok, clean_msg = await scanner.scan_bytes(b"Normal document content")
    assert clean_ok is True
    assert clean_msg == "CLEAN"

    eicar_ok, eicar_msg = await scanner.scan_bytes(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE")
    assert eicar_ok is False
    assert "INFECTED" in eicar_msg


@pytest.mark.asyncio
async def test_correlation_id_middleware(async_client: AsyncClient) -> None:
    """Verify correlation ID header is assigned or preserved."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers

    custom_id = "test-correlation-123"
    response2 = await async_client.get("/api/v1/health", headers={"X-Correlation-ID": custom_id})
    assert response2.headers["X-Correlation-ID"] == custom_id


@pytest.mark.asyncio
async def test_transactional_helper(db_session: AsyncSession) -> None:
    """Verify transactional context manager."""
    async with transactional(db_session) as s:
        assert s is not None
