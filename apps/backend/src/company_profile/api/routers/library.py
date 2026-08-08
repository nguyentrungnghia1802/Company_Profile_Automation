"""FastAPI router for meeting brief, profile diffing, and file exports."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError
from company_profile.db.session import get_db_session
from company_profile.modules.export.service import ExportService
from company_profile.modules.profiles.brief import MeetingBriefGenerator
from company_profile.modules.profiles.diff import ProfileDiffService
from company_profile.modules.publication.service import PublicationService

router = APIRouter(tags=["library"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateExportRequest(BaseModel):
    export_format: str = Field("pdf", description="'pdf' | 'json'")
    locale: str = Field("vi", description="'vi' | 'en'")
    include_source_appendix: bool = Field(True, description="Include evidence excerpts and URLs")
    include_internal_notes: bool = Field(False, description="Include reviewer internal notes")


class ExportJobResponse(BaseModel):
    id: str
    workspace_id: str
    profile_version_id: str
    export_format: str
    locale: str
    status: str
    include_source_appendix: bool
    include_internal_notes: bool
    checksum_sha256: str | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/companies/{company_id}/meeting-brief",
    summary="Get 1-minute executive meeting brief for a company",
)
async def get_company_meeting_brief(
    company_id: uuid.UUID,
    locale: str = Query("vi", description="Language: 'vi' | 'en'"),
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Generate 1-minute grounded meeting brief."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    pub_svc = PublicationService(session)
    pv = await pub_svc.get_current_profile(actor.active_workspace.id, company_id)
    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active published profile version found for this company.",
        )

    brief_gen = MeetingBriefGenerator()
    return brief_gen.generate_brief(pv, locale=locale)


@router.get(
    "/profiles/{version_id}/diff/{other_version_id}",
    summary="Field-level diff between two profile versions",
)
async def diff_profile_versions(
    version_id: uuid.UUID,
    other_version_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Compare two profile versions."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    diff_svc = ProfileDiffService(session)
    try:
        return await diff_svc.compare_versions(
            workspace_id=actor.active_workspace.id,
            version_id_a=version_id,
            version_id_b=other_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/profiles/{version_id}/exports",
    response_model=ExportJobResponse,
    summary="Create profile export job (PDF/JSON)",
)
async def create_profile_export(
    version_id: uuid.UUID,
    body: CreateExportRequest,
    actor: RequestActor = Depends(require_capability("company:read")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Start profile export job."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    export_svc = ExportService(session)
    job = await export_svc.create_export_job(
        workspace_id=actor.active_workspace.id,
        profile_version_id=version_id,
        requested_by=actor.user_id,
        export_format=body.export_format,
        locale=body.locale,
        include_source_appendix=body.include_source_appendix,
        include_internal_notes=body.include_internal_notes,
    )

    return {
        "id": str(job.id),
        "workspace_id": str(job.workspace_id),
        "profile_version_id": str(job.profile_version_id),
        "export_format": job.export_format,
        "locale": job.locale,
        "status": job.status,
        "include_source_appendix": job.include_source_appendix,
        "include_internal_notes": job.include_internal_notes,
        "checksum_sha256": job.checksum_sha256,
        "file_size_bytes": job.file_size_bytes,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get(
    "/exports/{export_id}",
    response_model=ExportJobResponse,
    summary="Get export job status",
)
async def get_export_job_status(
    export_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get export job status."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    export_svc = ExportService(session)
    job = await export_svc.get_export_job(actor.active_workspace.id, export_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found.")

    return {
        "id": str(job.id),
        "workspace_id": str(job.workspace_id),
        "profile_version_id": str(job.profile_version_id),
        "export_format": job.export_format,
        "locale": job.locale,
        "status": job.status,
        "include_source_appendix": job.include_source_appendix,
        "include_internal_notes": job.include_internal_notes,
        "checksum_sha256": job.checksum_sha256,
        "file_size_bytes": job.file_size_bytes,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get(
    "/exports/{export_id}/download",
    summary="Download exported PDF or JSON file",
)
async def download_export_file(
    export_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Stream exported file."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    export_svc = ExportService(session)
    job = await export_svc.get_export_job(actor.active_workspace.id, export_id)
    if not job or job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed export file not found.",
        )

    file_path = export_svc.get_export_file_path(job)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file missing from storage.",
        )

    media_type = "application/pdf" if job.export_format == "pdf" else "application/json"
    filename = file_path.name

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
