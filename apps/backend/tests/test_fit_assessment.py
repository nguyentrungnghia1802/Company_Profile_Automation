"""Unit & integration tests for Program Fit Assessment service and API router."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.fit_assessment.service import ProgramFitAssessmentService


@pytest.mark.asyncio
async def test_program_fit_assessment_rules(db_session: AsyncSession) -> None:
    """Test rules-based fit assessment calculation and evidence generation."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()

    ws = Workspace(id=ws_id, name="Accelerator Workspace", slug="accel-ws")
    usr = User(
        id=user_id,
        auth_provider="mock",
        auth_subject="sub-accel",
        email="accel@example.com",
        display_name="Accel Admin",
    )
    member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="workspace_admin")
    cp = CompanyProfile(
        id=company_id,
        workspace_id=ws_id,
        company_name="Fit Company JSC",
        normalized_name="fit company jsc",
        tax_id="0109998877",
        legal_name="Công ty Cổ phần Fit Company",
        website_url="https://fitcompany.vn",
    )

    db_session.add_all([ws, usr, member, cp])
    await db_session.commit()

    svc = ProgramFitAssessmentService(db_session)
    assessment = await svc.evaluate_program_fit(ws_id, company_id, "AI Riser Accelerator 2026")

    assert assessment.company_id == company_id
    assert assessment.overall_fit_status in {"eligible", "review_recommended", "needs_more_data"}
    assert assessment.fit_score >= 0.5
    assert len(assessment.assessment_json["reasons"]) == 4

    # Test reviewer override
    updated = await svc.apply_reviewer_override(
        workspace_id=ws_id,
        assessment_id=assessment.id,
        user_id=user_id,
        override_status="eligible",
        notes="Chấp nhận doanh nghiệp sau buổi phỏng vấn trực tiếp",
    )

    assert updated.reviewer_override_status == "eligible"
    assert updated.reviewed_by == user_id


@pytest.mark.asyncio
async def test_fit_assessment_api_endpoints(
    async_client: AsyncClient,
) -> None:
    """Test HTTP API router for program fit assessment."""
    ws_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())

    # Listing should be empty initially
    res = await async_client.get(
        f"/api/v1/companies/{company_id}/fit-assessments",
        headers={"X-Workspace-ID": ws_id},
    )
    assert res.status_code == 200
    assert res.json() == []
