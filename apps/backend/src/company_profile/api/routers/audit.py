"""FastAPI router for querying append-only security audit trail."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError
from company_profile.db.session import get_db_session
from company_profile.modules.audit.service import AuditService

router = APIRouter(tags=["audit"])


class AuditLogResponse(BaseModel):
    id: str
    workspace_id: str
    actor_id: str | None = None
    actor_type: str
    action: str
    resource_type: str
    resource_id: str | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str

    model_config = {"from_attributes": True}


@router.get(
    "/audit",
    response_model=list[AuditLogResponse],
    summary="Query paginated workspace audit trail",
)
async def list_audit_trail(
    action: str | None = Query(None, description="Filter by action name"),
    actor_id: uuid.UUID | None = Query(None, description="Filter by actor ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: RequestActor = Depends(require_capability("workspace:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get security audit log trail."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = AuditService(session)
    logs = await svc.list_audit_logs(
        workspace_id=actor.active_workspace.id,
        action=action,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "id": str(log.id),
            "workspace_id": str(log.workspace_id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "actor_type": log.actor_type,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "correlation_id": log.correlation_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.get_metadata(),
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
