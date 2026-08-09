"""FastAPI router for provider status, usage, and operational monitoring (no secrets)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError
from company_profile.config.settings import get_settings
from company_profile.db.models.ai import AiRun
from company_profile.db.models.research import ResearchJob
from company_profile.db.session import get_db_session

router = APIRouter(tags=["operations"])


class ProviderSettingsResponse(BaseModel):
    environment: str
    ai_provider: str
    gemini_model: str
    search_provider: str
    object_storage_provider: str
    ai_max_retries: int
    ai_timeout_seconds: int
    malware_scanner_mode: str
    # Strictly NO secrets exposed


class UpdateProviderSettingsRequest(BaseModel):
    ai_max_retries: int = Field(3, ge=1, le=10)
    ai_timeout_seconds: int = Field(60, ge=10, le=300)


@router.get(
    "/provider-settings",
    response_model=ProviderSettingsResponse,
    summary="Get safe provider status (strictly no secrets)",
)
async def get_provider_settings(
    _actor: RequestActor = Depends(require_capability("workspace:manage")),
) -> dict[str, Any]:
    """Get safe provider settings."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "ai_provider": settings.ai_provider,
        "gemini_model": settings.gemini_model,
        "search_provider": settings.search_provider,
        "object_storage_provider": settings.object_storage_provider,
        "ai_max_retries": settings.ai_max_retries,
        "ai_timeout_seconds": settings.ai_timeout,
        "malware_scanner_mode": settings.malware_scanner_mode,
    }


@router.patch(
    "/provider-settings",
    response_model=ProviderSettingsResponse,
    summary="Update non-secret provider behavior limits",
)
async def update_provider_settings(
    body: UpdateProviderSettingsRequest,
    _actor: RequestActor = Depends(require_capability("workspace:manage")),
) -> dict[str, Any]:
    """Update non-secret provider settings."""
    settings = get_settings()
    # Apply non-secret updates
    settings.ai_max_retries = body.ai_max_retries
    settings.ai_timeout = body.ai_timeout_seconds

    return {
        "environment": settings.environment,
        "ai_provider": settings.ai_provider,
        "gemini_model": settings.gemini_model,
        "search_provider": settings.search_provider,
        "object_storage_provider": settings.object_storage_provider,
        "ai_max_retries": settings.ai_max_retries,
        "ai_timeout_seconds": settings.ai_timeout,
        "malware_scanner_mode": settings.malware_scanner_mode,
    }


@router.get(
    "/operations/usage",
    summary="Get workspace provider usage and cost metrics",
)
async def get_operations_usage(
    actor: RequestActor = Depends(require_capability("workspace:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get workspace provider usage metrics."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    stmt_runs = select(func.count(AiRun.id), func.sum(AiRun.estimated_cost_usd)).where(
        AiRun.workspace_id == actor.active_workspace.id
    )
    res_runs = await session.execute(stmt_runs)
    total_runs, total_cost = res_runs.one()

    return {
        "workspace_id": str(actor.active_workspace.id),
        "total_ai_runs": total_runs or 0,
        "total_estimated_cost_usd": round(total_cost or 0.0, 4),
        "currency": "USD",
    }


@router.get(
    "/operations/jobs",
    summary="List workspace operational research jobs",
)
async def list_operations_jobs(
    actor: RequestActor = Depends(require_capability("workspace:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List operational research jobs."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    stmt = (
        select(ResearchJob)
        .where(ResearchJob.workspace_id == actor.active_workspace.id)
        .order_by(ResearchJob.created_at.desc())
        .limit(50)
    )
    res = await session.execute(stmt)
    jobs = res.scalars().all()

    return [
        {
            "id": str(job.id),
            "company_id": str(job.company_id),
            "job_type": job.job_type,
            "status": job.status,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        for job in jobs
    ]
