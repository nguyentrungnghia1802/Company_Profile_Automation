"""Tests for ProfileDraftService, PublicationService, publication blockers, and immutable version management."""

import json
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace
from company_profile.modules.conflicts.engine import ConflictEngine
from company_profile.modules.drafts.service import ProfileDraftService
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.publication.service import PublicationService


@pytest.mark.asyncio
async def test_draft_assembly_and_publication(
    db_session: AsyncSession,
) -> None:
    """Test assembling draft profile, checking blockers, and publishing immutable version."""
    ws = Workspace(id=uuid.uuid4(), name="Pub WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"pub-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Publisher",
    )
    cp = CompanyProfile(id=uuid.uuid4(), workspace_id=ws.id, company_name="Acme Tech JSC", normalized_name="acme tech jsc")
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    fact_repo = FactCandidateRepository(db_session)

    # 1. Insert accepted candidates
    cand1 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value_type="string",
        value={"name": "Acme Tech JSC"},
        confidence_score=0.95,
        confidence_explanation="Confirmed via official registry",
    )
    cand1.display_value = "Acme Tech JSC"
    cand1.fact_status = "accepted"

    cand2 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.description",
        value_type="string",
        value="Acme Tech provides cloud automation software.",
        confidence_score=0.90,
    )
    cand2.display_value = "Acme Tech provides cloud automation software."
    cand2.fact_status = "accepted"
    await db_session.flush()

    # 2. Assemble draft
    draft_svc = ProfileDraftService(db_session)
    draft = await draft_svc.assemble_draft(
        workspace_id=ws.id,
        company_id=cp.id,
        title="Acme Profile Draft",
        created_by=usr.id,
    )
    assert draft.id is not None
    assert draft.status == "building"
    assert len(draft.field_selections) == 2

    # 3. Check publication blockers (should be 0)
    blockers = await draft_svc.check_publication_blockers(ws.id, cp.id)
    assert len(blockers) == 0

    # 4. Request review
    draft = await draft_svc.request_review(
        workspace_id=ws.id,
        draft_id=draft.id,
        actor_id=usr.id,
    )
    assert draft.status == "ready_for_review"

    # 5. Publish draft
    pub_svc = PublicationService(db_session)
    ver1 = await pub_svc.publish_draft(
        workspace_id=ws.id,
        draft_id=draft.id,
        published_by=usr.id,
        publication_note="Initial publication v1.0",
    )
    assert ver1.id is not None
    assert ver1.version_number == 1
    assert ver1.status == "published"
    assert "Acme Tech JSC" in ver1.executive_summary
    assert len(ver1.field_values) == 2
    assert ver1.content_hash is not None

    # 6. Verify current profile query
    curr = await pub_svc.get_current_profile(ws.id, cp.id)
    assert curr is not None
    assert curr.id == ver1.id

    # 7. Publish v2 -> v1 should become superseded
    draft2 = await draft_svc.assemble_draft(
        workspace_id=ws.id,
        company_id=cp.id,
        title="Acme Profile Draft v2",
        created_by=usr.id,
    )
    ver2 = await pub_svc.publish_draft(
        workspace_id=ws.id,
        draft_id=draft2.id,
        published_by=usr.id,
        publication_note="Updated v2",
    )
    assert ver2.version_number == 2
    assert ver2.status == "published"

    v1_reloaded = await pub_svc.get_profile_version(ws.id, ver1.id)
    assert v1_reloaded is not None
    assert v1_reloaded.status == "superseded"


@pytest.mark.asyncio
async def test_publication_blockers_on_unresolved_conflict(
    db_session: AsyncSession,
) -> None:
    """Test publication fails when material unresolved conflict exists."""
    ws = Workspace(id=uuid.uuid4(), name="Pub Block WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"pubblock-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Publisher Block",
    )
    cp = CompanyProfile(id=uuid.uuid4(), workspace_id=ws.id, company_name="Acme Inc", normalized_name="acme inc")
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    fact_repo = FactCandidateRepository(db_session)
    cand1 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value_type="string",
        value={"name": "Acme Inc"},
    )
    cand1.fact_status = "accepted"

    cand2 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value_type="string",
        value={"name": "Acme Ltd"},
    )
    cand2.fact_status = "candidate"
    await db_session.flush()

    # Create material conflict
    conflict_engine = ConflictEngine(db_session)
    conf = await conflict_engine.detect_and_update_conflicts(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
    )
    assert conf is not None

    draft_svc = ProfileDraftService(db_session)
    draft = await draft_svc.assemble_draft(
        workspace_id=ws.id,
        company_id=cp.id,
        title="Blocked Draft",
    )

    # Publish draft should raise ValueError due to unresolved conflict
    pub_svc = PublicationService(db_session)
    with pytest.raises(ValueError, match="Cannot publish draft"):
        await pub_svc.publish_draft(
            workspace_id=ws.id,
            draft_id=draft.id,
            published_by=usr.id,
        )
