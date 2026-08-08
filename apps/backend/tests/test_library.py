"""Tests for ProfileDiffService and MeetingBriefGenerator."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace
from company_profile.modules.drafts.service import ProfileDraftService
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.profiles.brief import MeetingBriefGenerator
from company_profile.modules.profiles.diff import ProfileDiffService
from company_profile.modules.publication.service import PublicationService


@pytest.mark.asyncio
async def test_profile_diff_and_meeting_brief(
    db_session: AsyncSession,
) -> None:
    """Test field-level diff between two versions and meeting brief generation."""
    ws = Workspace(id=uuid.uuid4(), name="Lib WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"lib-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Library User",
    )
    cp = CompanyProfile(id=uuid.uuid4(), workspace_id=ws.id, company_name="TechCorp JSC", normalized_name="techcorp jsc")
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    fact_repo = FactCandidateRepository(db_session)
    cand1 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value={"name": "TechCorp JSC"},
    )
    cand1.display_value = "TechCorp JSC"
    cand1.fact_status = "accepted"

    cand2 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.description",
        value="TechCorp develops enterprise AI tools.",
    )
    cand2.display_value = "TechCorp develops enterprise AI tools."
    cand2.fact_status = "accepted"
    await db_session.flush()

    # 1. Publish v1
    draft_svc = ProfileDraftService(db_session)
    draft1 = await draft_svc.assemble_draft(ws.id, cp.id, title="v1 Draft")
    pub_svc = PublicationService(db_session)
    ver1 = await pub_svc.publish_draft(ws.id, draft1.id, usr.id, "v1 release")

    # 2. Modify candidate and publish v2
    cand3 = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="overview.description",
        value="TechCorp develops advanced enterprise AI & cloud tools.",
        confidence_score=0.98,
    )
    cand3.display_value = "TechCorp develops advanced enterprise AI & cloud tools."
    cand3.fact_status = "accepted"
    await db_session.flush()

    draft2 = await draft_svc.assemble_draft(ws.id, cp.id, title="v2 Draft")
    ver2 = await pub_svc.publish_draft(ws.id, draft2.id, usr.id, "v2 release")

    # 3. Test ProfileDiffService
    diff_svc = ProfileDiffService(db_session)
    res = await diff_svc.compare_versions(ws.id, ver1.id, ver2.id)
    assert res["version_a"]["version_number"] == 1
    assert res["version_b"]["version_number"] == 2
    assert res["summary"]["modified_count"] == 1
    assert len(res["field_diffs"]) == 1
    assert res["field_diffs"][0]["field_key"] == "overview.description"
    assert res["field_diffs"][0]["change_type"] == "modified"

    # 4. Test MeetingBriefGenerator
    brief_gen = MeetingBriefGenerator()
    brief_vi = brief_gen.generate_brief(ver2, locale="vi")
    assert "TechCorp JSC" in brief_vi["title"]
    assert len(brief_vi["suggested_verification_questions"]) > 0
    assert "hướng dẫn" in brief_vi["disclaimer"]

    brief_en = brief_gen.generate_brief(ver2, locale="en")
    assert "Executive Meeting Brief" in brief_en["title"]
    assert "Notice:" in brief_en["disclaimer"]
