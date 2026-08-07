"""Unit tests for URL safety validator and SSRF prevention boundary."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.integrations.storage.local_storage import LocalObjectStorage
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.sources.fetcher import WebFetcher
from company_profile.modules.sources.validator import validate_url_safety
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def test_url_safety_validator_allowed_urls() -> None:
    """Verify public HTTP/HTTPS URLs pass safety validation."""
    valid_urls = [
        "https://example.com/about",
        "http://dangkykinhdoanh.gov.vn",
        "https://sub.domain.co.uk/page?id=123",
    ]
    for url in valid_urls:
        is_safe, reason = validate_url_safety(url)
        assert is_safe is True, f"Expected {url} to be safe, got reason: {reason}"


def test_url_safety_validator_blocked_urls() -> None:
    """Verify SSRF targets, loopbacks, private IPs, and non-HTTP schemes are blocked."""
    blocked_urls = [
        ("http://127.0.0.1/admin", "SSRF_BLOCKED"),
        ("http://localhost:8000/api", "BLOCKED_HOST"),
        ("http://10.0.0.1/internal", "SSRF_BLOCKED"),
        ("http://172.16.0.1/secret", "SSRF_BLOCKED"),
        ("http://192.168.1.1/router", "SSRF_BLOCKED"),
        ("http://169.254.169.254/latest/meta-data/", "SSRF_BLOCKED"),
        ("file:///etc/passwd", "UNSUPPORTED_SCHEME"),
        ("ftp://ftp.example.com/file", "UNSUPPORTED_SCHEME"),
        ("gopher://gopher.example.com", "UNSUPPORTED_SCHEME"),
    ]
    for url, expected_code in blocked_urls:
        is_safe, reason = validate_url_safety(url)
        assert is_safe is False, f"Expected {url} to be blocked"
        assert expected_code in reason, f"Expected {expected_code} in {reason}"


@pytest.mark.asyncio
async def test_web_fetcher_blocks_ssrf_attempt(db_session: AsyncSession) -> None:
    """Verify WebFetcher rejects SSRF target URLs before attempting network request."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="SSRF WS", slug="ssrf-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="SSRF Corp",
            normalized_name="ssrf corp",
            status="published",
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalObjectStorage(temp_dir)
        fetcher = WebFetcher(db_session, storage=storage)

        res = await fetcher.fetch_and_store_source(
            workspace_id=ws.id,
            company_id=company.id,
            url="http://169.254.169.254/latest/meta-data/",
        )

        assert res.status_code == 400
        assert res.source.status == "rejected"
        assert res.snapshot is None
        assert "SSRF_PREVENTION" in (res.error_message or "")
