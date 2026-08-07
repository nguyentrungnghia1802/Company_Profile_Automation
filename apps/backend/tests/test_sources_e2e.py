"""End-to-end integration tests for source acquisition, policy rules, and duplicate handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID
from sqlalchemy.exc import IntegrityError

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import Workspace
from company_profile.db.models.source import DomainPolicy, Source, normalize_url
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.sources.policy import (
    calculate_entity_match_score,
    evaluate_source_policy,
)
from company_profile.modules.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_duplicate_url_unique_constraint(db_session: AsyncSession) -> None:
    """Verify unique constraint on (workspace_id, company_id, normalized_url)."""
    ws_repo = WorkspaceRepository(db_session)
    comp_repo = CompanyRepository(db_session)

    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Dup WS", slug="dup-ws"))
    company = await comp_repo.create(
        CompanyProfile(
            workspace_id=ws.id,
            company_name="Dup Corp",
            normalized_name="dup corp",
            status="published",
        )
    )

    norm_url = normalize_url("https://dup.example.com/info/")

    s1 = Source(
        workspace_id=ws.id,
        company_id=company.id,
        canonical_url="https://dup.example.com/info/",
        normalized_url=norm_url,
        domain="dup.example.com",
    )
    db_session.add(s1)
    await db_session.flush()

    s2 = Source(
        workspace_id=ws.id,
        company_id=company.id,
        canonical_url="https://dup.example.com/info",
        normalized_url=norm_url,
        domain="dup.example.com",
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_wrong_entity_match_score_rejection() -> None:
    """Verify source with low entity match score is rejected with LOW_MATCH_SCORE reason."""
    match_score = calculate_entity_match_score(
        target_name="Công ty TNHH AI Riser Việt Nam",
        target_tax_id="0312345678",
        text_content="Thông tin về công ty Xổ Số Kiến Thiết Bình Thuận.",
    )
    assert match_score < 0.3

    status, reason = evaluate_source_policy("web_page", 3, match_score, domain_blocked=False)
    assert status == "rejected"
    assert "LOW_MATCH_SCORE" in reason


@pytest.mark.asyncio
async def test_blocked_domain_rejection_policy(db_session: AsyncSession) -> None:
    """Verify workspace domain block policy prevents source acceptance."""
    ws_repo = WorkspaceRepository(db_session)
    ws = await ws_repo.create(Workspace(id=DEV_WORKSPACE_ID, name="Block WS", slug="block-ws"))

    policy = DomainPolicy(
        workspace_id=ws.id,
        domain="badsite.com",
        policy_type="blocked",
        reason="Malicious directory site",
    )
    db_session.add(policy)
    await db_session.flush()

    status, reason = evaluate_source_policy("web_page", 3, 0.9, domain_blocked=True)
    assert status == "rejected"
    assert "BLOCKED_DOMAIN" in reason
