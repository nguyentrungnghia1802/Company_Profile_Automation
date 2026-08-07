"""Phase 5 E2E & security integration test suite."""

from __future__ import annotations

import uuid

import pytest
from db.fixtures.identity_fixtures import get_dev_admin, get_dev_workspace
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import WorkspaceMember
from company_profile.db.models.source import (
    DocumentBlock,
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
)
from company_profile.modules.sources.parser import DocumentParser, PDFDocumentParser
from company_profile.modules.sources.policy import evaluate_robots_policy
from company_profile.modules.sources.validator import validate_url_safety


@pytest.mark.anyio
async def test_p5_025_security_and_robots_policy() -> None:
    """P5-025: Verify SSRF validation, host restrictions, and robots policy decision recording."""
    # Loopback IP SSRF
    safe, reason = validate_url_safety("http://127.0.0.1:8000/admin")
    assert not safe
    assert "restricted range" in reason or "127.0.0.0/8" in reason

    # Cloud metadata IP SSRF
    safe_meta, reason_meta = validate_url_safety("http://169.254.169.254/latest/meta-data")
    assert not safe_meta
    assert "restricted range" in reason_meta or "169.254.0.0/16" in reason_meta

    # Robots policy decision
    decision = evaluate_robots_policy("https://example.com/private/page", user_agent="VCPS-Bot")
    assert decision in ("allowed", "disallowed", "unknown")


@pytest.mark.anyio
async def test_p5_026_parser_multilingual_and_pdf_fixtures() -> None:
    """P5-026: Verify HTML and PDF parsers with Vietnamese multilingual content."""
    html_parser = DocumentParser()
    ws_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    vn_html = """
    <html>
    <body>
        <h1>Công Ty TNHH Giải Pháp Công Nghệ Việt</h1>
        <p>Địa chỉ: 123 Đường Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh.</p>
        <p>Mã số thuế: 0312345678. Điện thoại: 02838221100.</p>
    </body>
    </html>
    """
    blocks = html_parser.parse_html_to_blocks(ws_id, snap_id, vn_html)
    assert len(blocks) >= 2
    heading = next(b for b in blocks if b.block_type == "heading")
    assert "Giải Pháp Công Nghệ" in heading.text_content

    pdf_parser = PDFDocumentParser()
    pdf_text = b"Trang 1: Cong ty TNHH Viet Nam.\n\nTrang 2: Ma so thue 0312345678."
    pdf_blocks = pdf_parser.parse_pdf_to_blocks(ws_id, snap_id, pdf_text)
    assert len(pdf_blocks) >= 1
    assert "Cong ty TNHH" in pdf_blocks[0].text_content


@pytest.mark.anyio
async def test_p5_027_source_integrity_and_reconciliation_api(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """P5-027: Verify source attempts, snapshots, and document block API endpoints."""
    user = get_dev_admin()
    ws = get_dev_workspace()
    db_session.add_all([user, ws])
    await db_session.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="workspace_admin")
    company = CompanyProfile(
        workspace_id=ws.id,
        tax_id="0312345678",
        company_name="Reconciliation Test Corp",
        normalized_name="reconciliation test corp",
    )
    db_session.add_all([member, company])
    await db_session.flush()

    source = Source(
        workspace_id=ws.id,
        company_id=company.id,
        canonical_url="https://example.com/recon",
        normalized_url="https://example.com/recon",
        domain="example.com",
        source_type="web_page",
        status="fetched",
    )
    db_session.add(source)
    await db_session.flush()

    attempt = SourceFetchAttempt(
        workspace_id=ws.id,
        source_id=source.id,
        adapter="httpx",
        requested_url="https://example.com/recon",
        http_status=200,
        byte_count=500,
        outcome_code="success",
    )
    snapshot = SourceSnapshot(
        workspace_id=ws.id,
        source_id=source.id,
        content_hash="abc123hash",
        storage_provider="local",
        object_key=f"{ws.id}/{company.id}/abc123hash.html",
        content_type="text/html",
        byte_size=500,
    )
    db_session.add_all([attempt, snapshot])
    await db_session.flush()

    block = DocumentBlock(
        workspace_id=ws.id,
        source_snapshot_id=snapshot.id,
        block_key="block_0",
        block_type="paragraph",
        text_content="Extracted reconciliation paragraph text.",
        block_hash="hashblock0",
    )
    db_session.add(block)
    await db_session.flush()

    headers = {"Authorization": "Bearer mock-token-admin", "X-Workspace-ID": str(ws.id)}

    # Test GET /api/v1/sources/{source_id}/attempts
    res_atts = await async_client.get(f"/api/v1/sources/{source.id}/attempts", headers=headers)
    assert res_atts.status_code == 200
    atts_data = res_atts.json()["data"]
    assert len(atts_data) == 1
    assert atts_data[0]["adapter"] == "httpx"

    # Test GET /api/v1/sources/{source_id}/snapshots
    res_snaps = await async_client.get(f"/api/v1/sources/{source.id}/snapshots", headers=headers)
    assert res_snaps.status_code == 200
    snaps_data = res_snaps.json()["data"]
    assert len(snaps_data) == 1
    assert snaps_data[0]["content_hash"] == "abc123hash"

    # Test GET /api/v1/snapshots/{snapshot_id}/blocks
    res_blks = await async_client.get(f"/api/v1/snapshots/{snapshot.id}/blocks", headers=headers)
    assert res_blks.status_code == 200
    blks_data = res_blks.json()["data"]
    assert len(blks_data) == 1
    assert blks_data[0]["block_key"] == "block_0"
