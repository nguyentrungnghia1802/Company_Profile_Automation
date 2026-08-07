"""FastAPI router for source URL management and domain policy administration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError, NotFoundError, ValidationError
from company_profile.db.models.source import DomainPolicy, Source, normalize_url
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
            data=SourceResponseData(
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
                first_discovered_at=source.first_discovered_at,
                last_checked_at=source.last_checked_at,
            ),
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

    return SourceListResponse(
        success=True,
        data=[
            SourceResponseData(
                id=s.id,
                workspace_id=s.workspace_id,
                company_id=s.company_id,
                canonical_url=s.canonical_url,
                normalized_url=s.normalized_url,
                domain=s.domain,
                source_type=s.source_type,
                authority_tier=s.authority_tier,
                status=s.status,
                entity_match_score=s.entity_match_score,
                first_discovered_at=s.first_discovered_at,
                last_checked_at=s.last_checked_at,
            )
            for s in sources
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
