"""FastAPI router for source URL management and domain policy administration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError, NotFoundError, ValidationError
from company_profile.db.models.source import (
    DocumentBlock,
    DomainPolicy,
    Source,
    SourceFetchAttempt,
    SourceSnapshot,
    normalize_url,
)
from company_profile.db.session import get_db_session
from company_profile.db.transaction import transactional
from company_profile.modules.sources.policy import classify_source_type

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("company_profile.api.routers.sources")

router = APIRouter()


class SourceResponseData(BaseModel):
    """Source response data model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: uuid.UUID
    canonical_url: str
    normalized_url: str
    domain: str
    source_type: str
    authority_tier: int
    status: str
    entity_match_score: float | None = None
    discovered_via: str = "manual_url"
    provider: str | None = None
    authority_by_field: dict[str, int] = Field(default_factory=dict)
    discovery_provenance: list[str] = Field(default_factory=list)
    selection_reason: str | None = None
    rejection_reason: str | None = None
    latest_fetch_status: str | None = None
    latest_fetch_outcome: str | None = None
    latest_fetch_policy_result: str | None = None
    latest_parser_status: str | None = None
    latest_parser_version: str | None = None
    latest_snapshot_id: uuid.UUID | None = None
    latest_fetched_at: datetime | None = None
    first_discovered_at: datetime
    last_checked_at: datetime | None = None


class SourceDetailResponse(BaseModel):
    """Source detail envelope."""

    success: bool = True
    data: SourceResponseData


class SourceListResponse(BaseModel):
    """Source list envelope."""

    success: bool = True
    data: list[SourceResponseData]


class AddSourceRequest(BaseModel):
    """Add manual source request payload."""

    company_id: uuid.UUID
    url: str
    source_type: str = "web_page"


class DomainPolicyResponseData(BaseModel):
    """Domain policy response model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    domain: str
    policy_type: str
    reason: str | None = None
    created_at: datetime


class DomainPolicyDetailResponse(BaseModel):
    """Domain policy envelope."""

    success: bool = True
    data: DomainPolicyResponseData


class DomainPolicyListResponse(BaseModel):
    """Domain policy list envelope."""

    success: bool = True
    data: list[DomainPolicyResponseData]


class AddDomainPolicyRequest(BaseModel):
    """Add domain policy request payload."""

    domain: str
    policy_type: str = "blocked"
    reason: str | None = None


def verify_active_workspace(actor: RequestActor) -> uuid.UUID:
    """Ensure current request actor has an active workspace selected."""
    if not actor.active_workspace:
        raise ForbiddenError(
            code="NO_ACTIVE_WORKSPACE",
            message="No active workspace selected for request.",
        )
    return actor.active_workspace.id


def _source_response_data(
    source: Source,
    *,
    latest_attempt: SourceFetchAttempt | None = None,
    latest_snapshot: SourceSnapshot | None = None,
) -> SourceResponseData:
    """Build source metadata required by the progress and evidence UI."""
    return SourceResponseData(
        id=source.id,
        workspace_id=source.workspace_id,
        company_id=source.company_id,
        canonical_url=source.canonical_url,
        normalized_url=source.normalized_url,
        domain=source.domain,
        source_type=source.source_type,
        authority_tier=source.authority_tier,
        status=source.status,
        entity_match_score=source.entity_match_score,
        discovered_via=source.discovered_via,
        provider=source.provider,
        authority_by_field=dict(source.authority_by_field or {}),
        discovery_provenance=list(source.discovery_provenance or []),
        selection_reason=source.selection_reason,
        rejection_reason=source.rejection_reason,
        latest_fetch_status=source.status,
        latest_fetch_outcome=latest_attempt.outcome_code if latest_attempt else None,
        latest_fetch_policy_result=latest_attempt.policy_result if latest_attempt else None,
        latest_parser_status=latest_snapshot.parser_status if latest_snapshot else None,
        latest_parser_version=latest_snapshot.parser_version if latest_snapshot else None,
        latest_snapshot_id=latest_snapshot.id if latest_snapshot else None,
        latest_fetched_at=(
            latest_snapshot.retrieved_at
            if latest_snapshot
            else (latest_attempt.completed_at if latest_attempt else None)
        ),
        first_discovered_at=source.first_discovered_at,
        last_checked_at=source.last_checked_at,
    )


async def _latest_source_artifacts(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    source_ids: list[uuid.UUID],
) -> tuple[dict[uuid.UUID, SourceFetchAttempt], dict[uuid.UUID, SourceSnapshot]]:
    """Load latest fetch and parser records without N+1 requests."""
    if not source_ids:
        return {}, {}

    attempts_result = await session.execute(
        select(SourceFetchAttempt)
        .where(
            SourceFetchAttempt.workspace_id == workspace_id,
            SourceFetchAttempt.source_id.in_(source_ids),
        )
        .order_by(SourceFetchAttempt.started_at.desc())
    )
    latest_attempts: dict[uuid.UUID, SourceFetchAttempt] = {}
    for attempt in attempts_result.scalars().all():
        latest_attempts.setdefault(attempt.source_id, attempt)

    snapshots_result = await session.execute(
        select(SourceSnapshot)
        .where(
            SourceSnapshot.workspace_id == workspace_id,
            SourceSnapshot.source_id.in_(source_ids),
        )
        .order_by(SourceSnapshot.retrieved_at.desc())
    )
    latest_snapshots: dict[uuid.UUID, SourceSnapshot] = {}
    for snapshot in snapshots_result.scalars().all():
        latest_snapshots.setdefault(snapshot.source_id, snapshot)

    return latest_attempts, latest_snapshots


@router.post("/sources", response_model=SourceDetailResponse)
async def add_source(
    payload: AddSourceRequest,
    actor: RequestActor = Depends(require_capability("company:update")),
    session: AsyncSession = Depends(get_db_session),
) -> SourceDetailResponse:
    """Manually add a public web URL source for a company profile."""
    workspace_id = verify_active_workspace(actor)
    norm_url = normalize_url(payload.url)
    domain = urlparse(norm_url).netloc.lower()

    async with transactional(session):
        # Check domain policies
        dp_stmt = select(DomainPolicy).where(
            DomainPolicy.workspace_id == workspace_id,
            DomainPolicy.domain == domain,
        )
        dp_res = await session.execute(dp_stmt)
        policy = dp_res.scalar_one_or_none()
        if policy and policy.policy_type == "blocked":
            raise ValidationError(
                code="DOMAIN_BLOCKED",
                message=f"Domain '{domain}' is explicitly blocked by workspace policy.",
            )

        stype, tier = classify_source_type(domain, norm_url)
        source = Source(
            workspace_id=workspace_id,
            company_id=payload.company_id,
            canonical_url=payload.url,
            normalized_url=norm_url,
            domain=domain,
            source_type=payload.source_type or stype,
            authority_tier=tier,
            status="discovered",
        )
        session.add(source)
        await session.flush()

        logger.info(
            "Added source URL for company",
            extra={
                "source_id": str(source.id),
                "company_id": str(payload.company_id),
                "domain": domain,
            },
        )
        return SourceDetailResponse(
            success=True,
            data=_source_response_data(source),
        )


@router.get("/sources", response_model=SourceListResponse)
async def list_company_sources(
    company_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> SourceListResponse:
    """List sources for a company profile."""
    workspace_id = verify_active_workspace(actor)
    stmt = (
        select(Source)
        .where(Source.workspace_id == workspace_id, Source.company_id == company_id)
        .order_by(Source.created_at.desc())
    )
    res = await session.execute(stmt)
    sources: Sequence[Source] = res.scalars().all()
    source_ids = [source.id for source in sources]
    latest_attempts, latest_snapshots = await _latest_source_artifacts(
        session, workspace_id, source_ids
    )

    return SourceListResponse(
        success=True,
        data=[
            _source_response_data(
                source,
                latest_attempt=latest_attempts.get(source.id),
                latest_snapshot=latest_snapshots.get(source.id),
            )
            for source in sources
        ],
    )


@router.get("/domain-policies", response_model=DomainPolicyListResponse)
async def list_domain_policies(
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> DomainPolicyListResponse:
    """List domain policy rules for active workspace."""
    workspace_id = verify_active_workspace(actor)
    stmt = (
        select(DomainPolicy)
        .where(DomainPolicy.workspace_id == workspace_id)
        .order_by(DomainPolicy.domain.asc())
    )
    res = await session.execute(stmt)
    policies: Sequence[DomainPolicy] = res.scalars().all()

    return DomainPolicyListResponse(
        success=True,
        data=[
            DomainPolicyResponseData(
                id=p.id,
                workspace_id=p.workspace_id,
                domain=p.domain,
                policy_type=p.policy_type,
                reason=p.reason,
                created_at=p.created_at,
            )
            for p in policies
        ],
    )


@router.post("/domain-policies", response_model=DomainPolicyDetailResponse)
async def add_domain_policy(
    payload: AddDomainPolicyRequest,
    actor: RequestActor = Depends(require_capability("workspace:admin")),
    session: AsyncSession = Depends(get_db_session),
) -> DomainPolicyDetailResponse:
    """Add domain rule (blocked/allowed) with audit event logging."""
    workspace_id = verify_active_workspace(actor)
    clean_domain = payload.domain.strip().lower()

    async with transactional(session):
        policy = DomainPolicy(
            workspace_id=workspace_id,
            domain=clean_domain,
            policy_type=payload.policy_type,
            reason=payload.reason,
            created_by=actor.user_id,
        )
        session.add(policy)
        await session.flush()

        logger.info(
            "Domain policy created",
            extra={
                "event_type": "source_domain.blocked"
                if payload.policy_type == "blocked"
                else "source_domain.policy_created",
                "domain": clean_domain,
                "policy_type": payload.policy_type,
                "workspace_id": str(workspace_id),
                "actor_id": str(actor.user_id),
            },
        )
        return DomainPolicyDetailResponse(
            success=True,
            data=DomainPolicyResponseData(
                id=policy.id,
                workspace_id=policy.workspace_id,
                domain=policy.domain,
                policy_type=policy.policy_type,
                reason=policy.reason,
                created_at=policy.created_at,
            ),
        )


@router.delete("/domain-policies/{policy_id}")
async def delete_domain_policy(
    policy_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("workspace:admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Delete domain policy rule."""
    workspace_id = verify_active_workspace(actor)

    async with transactional(session):
        stmt = select(DomainPolicy).where(
            DomainPolicy.id == policy_id,
            DomainPolicy.workspace_id == workspace_id,
        )
        res = await session.execute(stmt)
        policy = res.scalar_one_or_none()
        if not policy:
            raise NotFoundError(code="POLICY_NOT_FOUND", message="Domain policy rule not found.")

        await session.delete(policy)
        return {"success": True}


class FetchAttemptResponseData(BaseModel):
    """Fetch attempt model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    source_id: uuid.UUID
    research_job_id: uuid.UUID | None = None
    adapter: str
    started_at: datetime
    completed_at: datetime | None = None
    requested_url: str
    final_url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    byte_count: int
    outcome_code: str
    redirect_count: int = 0
    retry_count: int = 0
    policy_result: str = "not_evaluated"
    retryable: bool = False
    error_message: str | None = None


class FetchAttemptListResponse(BaseModel):
    """Fetch attempt list envelope."""

    success: bool = True
    data: list[FetchAttemptResponseData]


class SnapshotResponseData(BaseModel):
    """Source snapshot model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    source_id: uuid.UUID
    content_hash: str
    storage_provider: str
    object_key: str
    content_type: str
    byte_size: int
    malware_scan_status: str
    language: str
    parser_version: str
    parser_status: str
    parser_error: str | None = None
    retrieved_at: datetime


class SnapshotListResponse(BaseModel):
    """Source snapshot list envelope."""

    success: bool = True
    data: list[SnapshotResponseData]


class DocumentBlockResponseData(BaseModel):
    """Document block model."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    block_key: str
    block_type: str
    text_content: str
    block_hash: str
    language: str
    parser_version: str
    page_number: int | None = None
    section_path: list[str] = Field(default_factory=list)
    location: dict[str, object] = Field(default_factory=dict)
    block_metadata: dict[str, object] = Field(default_factory=dict)
    start_offset: int | None = None
    end_offset: int | None = None
    created_at: datetime


class DocumentBlockListResponse(BaseModel):
    """Document block list envelope."""

    success: bool = True
    data: list[DocumentBlockResponseData]


@router.get("/sources/{source_id}/attempts", response_model=FetchAttemptListResponse)
async def list_source_fetch_attempts(
    source_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> FetchAttemptListResponse:
    """List fetch attempts for a source URL."""
    workspace_id = verify_active_workspace(actor)
    stmt = (
        select(SourceFetchAttempt)
        .where(
            SourceFetchAttempt.workspace_id == workspace_id,
            SourceFetchAttempt.source_id == source_id,
        )
        .order_by(SourceFetchAttempt.started_at.desc())
    )
    res = await session.execute(stmt)
    attempts: Sequence[SourceFetchAttempt] = res.scalars().all()

    return FetchAttemptListResponse(
        success=True,
        data=[
            FetchAttemptResponseData(
                id=a.id,
                workspace_id=a.workspace_id,
                source_id=a.source_id,
                research_job_id=a.research_job_id,
                adapter=a.adapter,
                started_at=a.started_at,
                completed_at=a.completed_at,
                requested_url=a.requested_url,
                final_url=a.final_url,
                http_status=a.http_status,
                content_type=a.content_type,
                byte_count=a.byte_count,
                outcome_code=a.outcome_code,
                redirect_count=a.redirect_count,
                retry_count=a.retry_count,
                policy_result=a.policy_result,
                retryable=a.retryable,
                error_message=a.error_message,
            )
            for a in attempts
        ],
    )


@router.get("/sources/{source_id}/snapshots", response_model=SnapshotListResponse)
async def list_source_snapshots(
    source_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> SnapshotListResponse:
    """List snapshots for a source URL."""
    workspace_id = verify_active_workspace(actor)
    stmt = (
        select(SourceSnapshot)
        .where(
            SourceSnapshot.workspace_id == workspace_id,
            SourceSnapshot.source_id == source_id,
        )
        .order_by(SourceSnapshot.retrieved_at.desc())
    )
    res = await session.execute(stmt)
    snapshots: Sequence[SourceSnapshot] = res.scalars().all()

    return SnapshotListResponse(
        success=True,
        data=[
            SnapshotResponseData(
                id=s.id,
                workspace_id=s.workspace_id,
                source_id=s.source_id,
                content_hash=s.content_hash,
                storage_provider=s.storage_provider,
                object_key=s.object_key,
                content_type=s.content_type,
                byte_size=s.byte_size,
                malware_scan_status=s.malware_scan_status,
                language=s.language,
                parser_version=s.parser_version,
                parser_status=s.parser_status,
                parser_error=s.parser_error,
                retrieved_at=s.retrieved_at,
            )
            for s in snapshots
        ],
    )


@router.get("/snapshots/{snapshot_id}/blocks", response_model=DocumentBlockListResponse)
async def list_snapshot_document_blocks(
    snapshot_id: uuid.UUID,
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentBlockListResponse:
    """List extracted document blocks for a source snapshot."""
    workspace_id = verify_active_workspace(actor)
    stmt = (
        select(DocumentBlock)
        .where(
            DocumentBlock.workspace_id == workspace_id,
            DocumentBlock.source_snapshot_id == snapshot_id,
        )
        .order_by(DocumentBlock.created_at.asc())
    )
    res = await session.execute(stmt)
    blocks: Sequence[DocumentBlock] = res.scalars().all()

    return DocumentBlockListResponse(
        success=True,
        data=[
            DocumentBlockResponseData(
                id=b.id,
                workspace_id=b.workspace_id,
                source_snapshot_id=b.source_snapshot_id,
                block_key=b.block_key,
                block_type=b.block_type,
                text_content=b.text_content,
                block_hash=b.block_hash,
                language=b.language,
                parser_version=b.parser_version,
                page_number=b.page_number,
                section_path=list(b.section_path or []),
                location=dict(b.location or {}),
                block_metadata=dict(b.block_metadata or {}),
                start_offset=b.start_offset,
                end_offset=b.end_offset,
                created_at=b.created_at,
            )
            for b in blocks
        ],
    )
