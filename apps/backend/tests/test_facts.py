"""Tests for FactCandidate, Evidence, ConfidenceCalculator, FreshnessEvaluator,
and Facts API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.db.models.source import DocumentBlock, Source, SourceSnapshot
from company_profile.modules.facts.confidence import ConfidenceCalculator
from company_profile.modules.facts.freshness import FreshnessEvaluator
from company_profile.modules.facts.repository import FactCandidateRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def confidence_calc() -> ConfidenceCalculator:
    return ConfidenceCalculator()


@pytest.fixture
def freshness_eval() -> FreshnessEvaluator:
    return FreshnessEvaluator()


# ---------------------------------------------------------------------------
# ConfidenceCalculator Tests
# ---------------------------------------------------------------------------


def test_confidence_tier1_registry_high_score(confidence_calc: ConfidenceCalculator) -> None:
    """Tier 1 Registry direct evidence yields high confidence score (>0.85)."""
    res = confidence_calc.calculate(
        field_key="identity.legal_name",
        authority_tier=1,
        support_type="structured",
        observed_at=datetime.now(UTC),
        origin_type="reviewer",
    )
    assert res.total_score >= 0.85
    assert "High confidence" in res.explanation
    assert "Tier 1 Official Registry" in res.explanation


def test_confidence_decay_and_conflict_penalty(confidence_calc: ConfidenceCalculator) -> None:
    """Old observation date decays freshness, and conflicts reduce total score."""
    old_date = datetime.now(UTC) - timedelta(days=200)
    res = confidence_calc.calculate(
        field_key="overview.description",
        authority_tier=4,  # General Web
        support_type="contextual",
        observed_at=old_date,
        origin_type="ai",
        ai_confidence_hint=0.60,
        has_conflicts=True,
    )
    assert res.total_score < 0.60
    assert "WARNING: conflicting candidate detected" in res.explanation


def test_confidence_independent_domain_corroboration_boost(
    confidence_calc: ConfidenceCalculator,
) -> None:
    """Corroboration by 2+ independent domains boosts confidence score by +0.10."""
    base_res = confidence_calc.calculate(
        field_key="products.list",
        authority_tier=2,
        support_type="direct",
        independent_domain_count=1,
    )
    boosted_res = confidence_calc.calculate(
        field_key="products.list",
        authority_tier=2,
        support_type="direct",
        independent_domain_count=2,
    )
    assert boosted_res.total_score > base_res.total_score
    assert "corroborated by 2 independent domains" in boosted_res.explanation


# ---------------------------------------------------------------------------
# FreshnessEvaluator Tests
# ---------------------------------------------------------------------------


def test_freshness_identity_category(freshness_eval: FreshnessEvaluator) -> None:
    """Identity category remains fresh for 365 days."""
    now = datetime.now(UTC)
    assert freshness_eval.evaluate("identity.legal_name", now) == "fresh"
    assert freshness_eval.evaluate("identity.legal_name", now - timedelta(days=400)) == "warning"
    assert freshness_eval.evaluate("identity.legal_name", now - timedelta(days=800)) == "stale"


def test_freshness_innovation_category(freshness_eval: FreshnessEvaluator) -> None:
    """Innovation category becomes warning after 60 days and stale after 120 days."""
    now = datetime.now(UTC)
    assert (
        freshness_eval.evaluate("innovation.recent_activities", now - timedelta(days=10)) == "fresh"
    )
    assert (
        freshness_eval.evaluate("innovation.recent_activities", now - timedelta(days=70))
        == "warning"
    )
    assert (
        freshness_eval.evaluate("innovation.recent_activities", now - timedelta(days=150))
        == "stale"
    )


# ---------------------------------------------------------------------------
# Repository & API Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fact_candidate_repository_crud(db_session: AsyncSession) -> None:
    """FactCandidateRepository creates candidate, links evidence, and prevents duplicates."""
    ws = Workspace(id=uuid.uuid4(), name="Test WS", slug="test-ws-facts")
    cp = CompanyProfile(
        id=uuid.uuid4(), workspace_id=ws.id, company_name="Acme Ltd", normalized_name="acme ltd"
    )
    src = Source(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        canonical_url="https://acme.com",
        normalized_url="acme.com",
        domain="acme.com",
        source_type="official_site",
        authority_tier=2,
    )
    snap = SourceSnapshot(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        source_id=src.id,
        content_hash="hash123",
        storage_provider="local",
        object_key="key123",
        content_type="text/html",
        byte_size=100,
    )
    blk = DocumentBlock(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        source_snapshot_id=snap.id,
        block_key="blk_001",
        block_type="paragraph",
        text_content="Acme Ltd was founded in 2010.",
        block_hash="hash_blk_001",
    )

    db_session.add_all([ws, cp, src, snap, blk])
    await db_session.flush()

    repo = FactCandidateRepository(db_session)
    cand1 = await repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value="Acme Ltd",
        origin_type="ai",
        confidence_score=0.90,
    )
    assert cand1.id is not None
    assert cand1.fact_status == "candidate"

    # Duplicate check: exact same candidate value returns existing record
    cand2 = await repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value="Acme Ltd",
        origin_type="ai",
    )
    assert cand2.id == cand1.id

    # Add evidence
    ev = await repo.add_evidence(
        workspace_id=ws.id,
        fact_candidate_id=cand1.id,
        source_snapshot_id=snap.id,
        document_block_id=blk.id,
        original_excerpt="Acme Ltd was founded in 2010.",
        support_type="direct",
    )
    assert ev.id is not None

    # List candidates
    candidates = await repo.list_candidates(workspace_id=ws.id, company_id=cp.id)
    assert len(candidates) == 1
    assert candidates[0].field_key == "identity.legal_name"


@pytest.mark.asyncio
async def test_list_facts_api_endpoint(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """GET /api/v1/companies/{id}/facts returns extracted facts and evidence."""
    ws = Workspace(id=uuid.uuid4(), name="API WS", slug="api-ws-facts")
    user = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject="sub_user_facts",
        email="user@facts.com",
        display_name="User Facts",
    )
    member = WorkspaceMember(
        id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="workspace_admin", status="active"
    )
    cp = CompanyProfile(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_name="Facts API Co",
        normalized_name="facts api co",
    )

    cand = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.description",
        context_key="",
        value_type="string",
        value_json='"Leading tech provider."',
        display_value="Leading tech provider.",
        fact_status="validated",
        origin_type="ai",
        confidence_score=0.88,
        confidence_explanation="High confidence: Tier 2 Official Site direct evidence.",
        freshness_status="fresh",
    )

    db_session.add_all([ws, user, member, cp, cand])
    await db_session.flush()

    res = await async_client.get(
        f"/api/v1/companies/{cp.id}/facts",
        headers={
            "Authorization": f"Bearer {user.auth_subject}",
            "X-Workspace-ID": str(ws.id),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["field_key"] == "overview.description"
    assert data[0]["confidence_score"] == 0.88
