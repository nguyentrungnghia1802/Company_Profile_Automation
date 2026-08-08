"""Tests for ExportService, JSON and PDF profile export generation, and file checksums."""

import json
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace
from company_profile.modules.drafts.service import ProfileDraftService
from company_profile.modules.export.service import ExportService
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.publication.service import PublicationService


@pytest.mark.asyncio
async def test_export_service_json_and_pdf(
    db_session: AsyncSession,
) -> None:
    """Test creating JSON and PDF exports from a published ProfileVersion."""
    ws = Workspace(id=uuid.uuid4(), name="Export WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"exp-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Exporter",
    )
    cp = CompanyProfile(id=uuid.uuid4(), workspace_id=ws.id, company_name="ExportCorp", normalized_name="exportcorp")
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    fact_repo = FactCandidateRepository(db_session)
    cand = await fact_repo.create_candidate(
        workspace_id=ws.id,
        company_id=cp.id,
        field_key="identity.legal_name",
        value={"name": "ExportCorp Ltd"},
    )
    cand.display_value = "ExportCorp Ltd"
    cand.fact_status = "accepted"
    await db_session.flush()

    draft_svc = ProfileDraftService(db_session)
    draft = await draft_svc.assemble_draft(ws.id, cp.id, title="Export Draft")
    pub_svc = PublicationService(db_session)
    ver = await pub_svc.publish_draft(ws.id, draft.id, usr.id)

    export_svc = ExportService(db_session)

    # 1. Test JSON Export
    job_json = await export_svc.create_export_job(
        workspace_id=ws.id,
        profile_version_id=ver.id,
        requested_by=usr.id,
        export_format="json",
    )
    assert job_json.status == "completed"
    assert job_json.checksum_sha256 is not None
    assert job_json.file_size_bytes is not None
    assert job_json.file_size_bytes > 0

    json_path = export_svc.get_export_file_path(job_json)
    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["version_number"] == 1
    assert payload["title"] == "Export Draft"

    # 2. Test PDF Export
    job_pdf = await export_svc.create_export_job(
        workspace_id=ws.id,
        profile_version_id=ver.id,
        requested_by=usr.id,
        export_format="pdf",
    )
    assert job_pdf.status == "completed"
    assert job_pdf.checksum_sha256 is not None

    pdf_path = export_svc.get_export_file_path(job_pdf)
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF-1.4")
