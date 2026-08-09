"""Tests for ConflictEngine, comparators, conflict reopening, and Conflict API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.conflicts.engine import (
    ConflictEngine,
    evaluate_materiality,
    values_are_materially_different,
)

# ---------------------------------------------------------------------------
# Comparator Unit Tests
# ---------------------------------------------------------------------------


def test_values_are_materially_different_strings() -> None:
    """Exact/casing/whitespace matches are not materially different."""
    assert not values_are_materially_different("overview.description", "Acme Corp", "  acme corp ")
    assert values_are_materially_different("overview.description", "Acme Corp", "Beta Corp")


def test_values_are_materially_different_numbers() -> None:
    """Numeric values within 5% tolerance are not materially different."""
    assert not values_are_materially_different("size.office_count", 100, 102)
    assert values_are_materially_different("size.office_count", 100, 150)


def test_evaluate_materiality() -> None:
    """Identity legal fields yield critical materiality."""
    assert evaluate_materiality("identity.legal_name") == "critical"
    assert evaluate_materiality("overview.hq_address") == "high"
    assert evaluate_materiality("products.list") == "medium"


# ---------------------------------------------------------------------------
# ConflictEngine Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conflict_engine_detects_conflict(db_session: AsyncSession) -> None:
    """ConflictEngine detects material disagreement and creates a Conflict record."""
    ws = Workspace(id=uuid.uuid4(), name="Conflict WS", slug="conflict-ws")
    cp = CompanyProfile(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_name="Conflict Co",
        normalized_name="conflict co",
    )

    cand1 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        context_key="",
        value_type="string",
        value_json='"Acme Vietnam LLC"',
        display_value="Acme Vietnam LLC",
        fact_status="candidate",
        origin_type="ai",
    )
    cand2 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        context_key="",
        value_type="string",
        value_json='"Global Enterprise Corp"',
        display_value="Global Enterprise Corp",
        fact_status="candidate",
        origin_type="ai",
    )

    db_session.add_all([ws, cp, cand1, cand2])
    await db_session.flush()

    engine = ConflictEngine(db_session)
    conflict = await engine.detect_and_update_conflicts(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
    )

    assert conflict is not None
    assert conflict.status == "open"
    assert conflict.materiality == "critical"
    assert len(conflict.candidates) == 2


@pytest.mark.asyncio
async def test_conflict_engine_reopens_on_new_evidence(db_session: AsyncSession) -> None:
    """ConflictEngine reopens a resolved conflict when a new competing candidate arrives."""
    ws = Workspace(id=uuid.uuid4(), name="Reopen WS", slug="reopen-ws")
    cp = CompanyProfile(
        id=uuid.uuid4(), workspace_id=ws.id, company_name="Reopen Co", normalized_name="reopen co"
    )

    cand1 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="size.office_count",
        value_json="5",
        fact_status="candidate",
        origin_type="ai",
    )
    cand2 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="size.office_count",
        value_json="20",
        fact_status="candidate",
        origin_type="ai",
    )

    db_session.add_all([ws, cp, cand1, cand2])
    await db_session.flush()

    engine = ConflictEngine(db_session)
    conflict = await engine.detect_and_update_conflicts(
        workspace_id=ws.id, company_id=cp.id, field_key="size.office_count"
    )
    assert conflict is not None

    # Resolve conflict
    await engine.resolve_conflict(
        workspace_id=ws.id,
        company_id=cp.id,
        conflict_id=conflict.id,
        resolution_type="select_one",
        reason="Verified by official report",
        selected_candidate_ids=[cand1.id],
    )
    assert conflict.status == "resolved"

    # Add a third competing candidate
    cand3 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="size.office_count",
        value_json="50",
        fact_status="candidate",
        origin_type="ai",
    )
    db_session.add(cand3)
    await db_session.flush()

    # Re-evaluate
    reopened = await engine.detect_and_update_conflicts(
        workspace_id=ws.id, company_id=cp.id, field_key="size.office_count"
    )
    assert reopened is not None
    assert reopened.status == "reopened"
    assert len(reopened.candidates) == 3


@pytest.mark.asyncio
async def test_conflicts_api_endpoints(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """GET /api/v1/companies/{id}/conflicts and POST resolve conflict."""
    ws = Workspace(id=uuid.uuid4(), name="Conflict API WS", slug="conflict-api-ws")
    user = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject="sub_rev_conflicts",
        email="rev@conflicts.com",
        display_name="Reviewer Conflicts",
    )
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user.id,
        role="workspace_admin",
        status="active",
    )
    cp = CompanyProfile(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_name="API Conflict Co",
        normalized_name="api conflict co",
    )

    cand1 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.hq_address",
        value_json='"Hanoi, Vietnam"',
        display_value="Hanoi, Vietnam",
        fact_status="candidate",
        origin_type="ai",
    )
    cand2 = FactCandidate(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.hq_address",
        value_json='"Ho Chi Minh City, Vietnam"',
        display_value="Ho Chi Minh City, Vietnam",
        fact_status="candidate",
        origin_type="ai",
    )

    db_session.add_all([ws, user, member, cp, cand1, cand2])
    await db_session.flush()

    engine = ConflictEngine(db_session)
    conflict = await engine.detect_and_update_conflicts(
        workspace_id=ws.id, company_id=cp.id, field_key="overview.hq_address"
    )
    assert conflict is not None

    headers = {
        "Authorization": f"Bearer {user.auth_subject}",
        "X-Workspace-ID": str(ws.id),
    }

    # GET conflicts
    res = await async_client.get(
        f"/api/v1/companies/{cp.id}/conflicts",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["field_key"] == "overview.hq_address"
    assert data[0]["status"] == "open"

    # POST resolve conflict
    resolve_res = await async_client.post(
        f"/api/v1/companies/{cp.id}/conflicts/{conflict.id}/resolve",
        json={
            "resolution_type": "select_one",
            "reason": "Hanoi is the registered HQ address.",
            "selected_candidate_ids": [str(cand1.id)],
        },
        headers=headers,
    )
    assert resolve_res.status_code == 200
    res_data = resolve_res.json()
    assert res_data["status"] == "resolved"
    assert res_data["resolution_type"] == "select_one"
