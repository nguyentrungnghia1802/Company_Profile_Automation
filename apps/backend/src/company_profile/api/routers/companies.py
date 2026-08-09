"""FastAPI router for company profile management, candidate resolution, and entity merging."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from company_profile.db.session import get_db_session
from company_profile.modules.companies.errors import CompanyDuplicateError
from company_profile.modules.companies.repository import CompanyRepository
from company_profile.modules.companies.resolution import (
    CompanyResolutionService,
    ResolutionCandidate,
)
from company_profile.modules.companies.service import CompanyService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from company_profile.db.models.company import CompanyProfile

router = APIRouter()


class CompanyResponseData(BaseModel):
    """Company profile item."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    company_name: str
    normalized_name: str
    tax_id: str | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    industry: str | None = None
    website_url: str | None = None
    status: str
    confidence_score: float
    version: int


class CompanyListResponse(BaseModel):
    """Company profile list envelope."""

    success: bool = True
    data: list[CompanyResponseData]


class CompanyDetailResponse(BaseModel):
    """Company profile detail envelope."""

    success: bool = True
    data: CompanyResponseData


class CreateCompanyRequest(BaseModel):
    """Create company profile request body."""

    company_name: str
    tax_id: str | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    industry: str | None = None
    website_url: str | None = None
    headquarters_address: str | None = None
    primary_phone: str | None = None
    primary_email: str | None = None


class UpdateCompanyRequest(BaseModel):
    """Update company profile request body."""

    company_name: str | None = None
    tax_id: str | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    industry: str | None = None
    website_url: str | None = None
    status: str | None = None


class ResolvePreviewRequest(BaseModel):
    """Company resolution preview request body."""

    company_name: str
    tax_id: str | None = None
    registration_number: str | None = None


class ResolvePreviewResponse(BaseModel):
    """Company resolution preview envelope."""

    success: bool = True
    data: list[ResolutionCandidate]


class MergeCompanyRequest(BaseModel):
    """Merge company request body."""

    source_company_id: uuid.UUID


def verify_active_workspace(actor: RequestActor) -> uuid.UUID:
    """Ensure current request actor has an active workspace selected."""
    if not actor.active_workspace:
        raise ForbiddenError(
            code="NO_ACTIVE_WORKSPACE",
            message="No active workspace selected for request.",
        )
    return actor.active_workspace.id


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    status: str | None = None,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyListResponse:
    """List company profiles for active workspace."""
    workspace_id = verify_active_workspace(actor)
    repo = CompanyRepository(session)

    items: Sequence[CompanyProfile] = await repo.list_by_workspace(workspace_id, status=status)
    return CompanyListResponse(
        success=True,
        data=[
            CompanyResponseData(
                id=c.id,
                workspace_id=c.workspace_id,
                company_name=c.company_name,
                normalized_name=c.normalized_name,
                tax_id=c.tax_id,
                legal_name=c.legal_name,
                registration_number=c.registration_number,
                industry=c.industry,
                website_url=c.website_url,
                status=c.status,
                confidence_score=c.confidence_score,
                version=c.version,
            )
            for c in items
        ],
    )


@router.post("/companies", response_model=CompanyDetailResponse)
async def create_company(
    payload: CreateCompanyRequest,
    actor: RequestActor = Depends(require_capability("company:create")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Create a new company profile."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyService(session)

    try:
        c = await service.create_company(
            workspace_id=workspace_id,
            company_name=payload.company_name,
            tax_id=payload.tax_id,
            legal_name=payload.legal_name,
            registration_number=payload.registration_number,
            industry=payload.industry,
            website_url=payload.website_url,
            headquarters_address=payload.headquarters_address,
            primary_phone=payload.primary_phone,
            primary_email=payload.primary_email,
            actor_id=str(actor.user_id),
        )
    except CompanyDuplicateError as exc:
        match = exc.match
        details = {
            "submitted_company_name": match.submitted_company_name,
            "normalized_name": match.normalized_name,
            "match_reason": match.match_reason,
            "next_step": (
                "Use the existing company profile or review duplicate candidates before "
                "creating another record."
            ),
        }
        if match.existing_company_id is not None:
            details["existing_company_id"] = str(match.existing_company_id)
        if match.existing_company_name is not None:
            details["existing_company_name"] = match.existing_company_name
        raise ConflictError(
            code="COMPANY_DUPLICATE_REVIEW_REQUIRED",
            message=(
                "A company with the same normalized identity already exists in this workspace."
            ),
            details=details,
        ) from exc
    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=c.id,
            workspace_id=c.workspace_id,
            company_name=c.company_name,
            normalized_name=c.normalized_name,
            tax_id=c.tax_id,
            legal_name=c.legal_name,
            registration_number=c.registration_number,
            industry=c.industry,
            website_url=c.website_url,
            status=c.status,
            confidence_score=c.confidence_score,
            version=c.version,
        ),
    )


@router.post("/companies/resolve", response_model=ResolvePreviewResponse)
async def resolve_company_candidates(
    payload: ResolvePreviewRequest,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> ResolvePreviewResponse:
    """Search workspace for potential duplicate company profile candidates."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyResolutionService(session)

    candidates = await service.find_candidates(
        workspace_id=workspace_id,
        company_name=payload.company_name,
        tax_id=payload.tax_id,
        registration_number=payload.registration_number,
    )
    return ResolvePreviewResponse(success=True, data=candidates)


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Get company profile details."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyService(session)

    c = await service.get_company(workspace_id, company_id)
    if not c:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Company profile not found.")

    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=c.id,
            workspace_id=c.workspace_id,
            company_name=c.company_name,
            normalized_name=c.normalized_name,
            tax_id=c.tax_id,
            legal_name=c.legal_name,
            registration_number=c.registration_number,
            industry=c.industry,
            website_url=c.website_url,
            status=c.status,
            confidence_score=c.confidence_score,
            version=c.version,
        ),
    )


@router.patch("/companies/{company_id}", response_model=CompanyDetailResponse)
async def update_company(
    company_id: uuid.UUID,
    payload: UpdateCompanyRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Update fields of an existing company profile."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyService(session)

    updates = payload.model_dump(exclude_unset=True)
    c = await service.update_company(workspace_id, company_id, updates, actor_id=str(actor.user_id))
    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=c.id,
            workspace_id=c.workspace_id,
            company_name=c.company_name,
            normalized_name=c.normalized_name,
            tax_id=c.tax_id,
            legal_name=c.legal_name,
            registration_number=c.registration_number,
            industry=c.industry,
            website_url=c.website_url,
            status=c.status,
            confidence_score=c.confidence_score,
            version=c.version,
        ),
    )


@router.post("/companies/{company_id}/merge", response_model=CompanyDetailResponse)
async def merge_company(
    company_id: uuid.UUID,
    payload: MergeCompanyRequest,
    actor: RequestActor = Depends(require_capability("company:merge")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Merge a source company profile into the target company profile."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyResolutionService(session)

    try:
        merged = await service.merge_companies(
            workspace_id=workspace_id,
            source_id=payload.source_company_id,
            target_id=company_id,
            actor_id=str(actor.user_id),
        )
    except ValueError as err:
        raise ValidationError(code="MERGE_FAILED", message=str(err)) from err

    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=merged.id,
            workspace_id=merged.workspace_id,
            company_name=merged.company_name,
            normalized_name=merged.normalized_name,
            tax_id=merged.tax_id,
            legal_name=merged.legal_name,
            registration_number=merged.registration_number,
            industry=merged.industry,
            website_url=merged.website_url,
            status=merged.status,
            confidence_score=merged.confidence_score,
            version=merged.version,
        ),
    )


@router.post("/companies/{company_id}/archive", response_model=CompanyDetailResponse)
async def archive_company(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("company:archive")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Archive a company profile."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyService(session)

    try:
        archived = await service.archive_company(
            workspace_id, company_id, actor_id=str(actor.user_id)
        )
    except ValueError as err:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message=str(err)) from err

    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=archived.id,
            workspace_id=archived.workspace_id,
            company_name=archived.company_name,
            normalized_name=archived.normalized_name,
            tax_id=archived.tax_id,
            legal_name=archived.legal_name,
            registration_number=archived.registration_number,
            industry=archived.industry,
            website_url=archived.website_url,
            status=archived.status,
            confidence_score=archived.confidence_score,
            version=archived.version,
        ),
    )


@router.post("/companies/{company_id}/restore", response_model=CompanyDetailResponse)
async def restore_company(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("company:restore")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    """Restore an archived company profile."""
    workspace_id = verify_active_workspace(actor)
    service = CompanyService(session)

    try:
        restored = await service.restore_company(
            workspace_id, company_id, actor_id=str(actor.user_id)
        )
    except ValueError as err:
        raise ValidationError(code="RESTORE_FAILED", message=str(err)) from err

    return CompanyDetailResponse(
        success=True,
        data=CompanyResponseData(
            id=restored.id,
            workspace_id=restored.workspace_id,
            company_name=restored.company_name,
            normalized_name=restored.normalized_name,
            tax_id=restored.tax_id,
            legal_name=restored.legal_name,
            registration_number=restored.registration_number,
            industry=restored.industry,
            website_url=restored.website_url,
            status=restored.status,
            confidence_score=restored.confidence_score,
            version=restored.version,
        ),
    )
