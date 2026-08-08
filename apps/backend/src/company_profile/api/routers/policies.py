"""FastAPI router for versioned policy set management and domain policies."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.api.dependencies import (
    RequestActor,
    get_current_actor,
    require_capability,
)
from company_profile.api.errors import ForbiddenError
from company_profile.db.session import get_db_session
from company_profile.modules.policies.service import (
    DEFAULT_POLICY_CONFIG,
    PolicyService,
)

router = APIRouter(tags=["policies"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreatePolicyRequest(BaseModel):
    name: str = Field(..., max_length=128)
    description: str | None = None
    policy_config: dict[str, Any] = Field(default_factory=lambda: DEFAULT_POLICY_CONFIG)


class PolicySetResponse(BaseModel):
    id: str
    workspace_id: str
    version_number: int
    name: str
    description: str | None = None
    is_active: bool
    policy_config: dict[str, Any]
    created_by: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/policies",
    response_model=list[PolicySetResponse],
    summary="List workspace policy versions",
)
async def list_policy_versions(
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List policy versions."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = PolicyService(session)
    policies = await svc.list_policy_sets(actor.active_workspace.id)

    # Seed default policy if none exists
    if not policies:
        default_p = await svc.create_policy_set(
            workspace_id=actor.active_workspace.id,
            name="Default Workspace Policy v1",
            policy_config=DEFAULT_POLICY_CONFIG,
            description="Initial default system policy.",
            created_by=actor.user_id,
        )
        await svc.activate_policy_set(actor.active_workspace.id, default_p.id)
        policies = await svc.list_policy_sets(actor.active_workspace.id)

    return [
        {
            "id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "version_number": p.version_number,
            "name": p.name,
            "description": p.description,
            "is_active": p.is_active,
            "policy_config": p.get_policy_config(),
            "created_by": str(p.created_by) if p.created_by else None,
            "created_at": p.created_at.isoformat(),
        }
        for p in policies
    ]


@router.post(
    "/policies",
    response_model=PolicySetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create immutable policy version",
)
async def create_policy_version(
    body: CreatePolicyRequest,
    actor: RequestActor = Depends(require_capability("workspace:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create new policy version."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = PolicyService(session)
    policy = await svc.create_policy_set(
        workspace_id=actor.active_workspace.id,
        name=body.name,
        policy_config=body.policy_config,
        description=body.description,
        created_by=actor.user_id,
    )

    return {
        "id": str(policy.id),
        "workspace_id": str(policy.workspace_id),
        "version_number": policy.version_number,
        "name": policy.name,
        "description": policy.description,
        "is_active": policy.is_active,
        "policy_config": policy.get_policy_config(),
        "created_by": str(policy.created_by) if policy.created_by else None,
        "created_at": policy.created_at.isoformat(),
    }


@router.post(
    "/policies/{policy_id}/activate",
    response_model=PolicySetResponse,
    summary="Activate policy version",
)
async def activate_policy_version(
    policy_id: uuid.UUID,
    actor: RequestActor = Depends(require_capability("workspace:manage")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Activate policy set."""
    if not actor.active_workspace:
        raise ForbiddenError("No active workspace selected.")

    svc = PolicyService(session)
    try:
        policy = await svc.activate_policy_set(actor.active_workspace.id, policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "id": str(policy.id),
        "workspace_id": str(policy.workspace_id),
        "version_number": policy.version_number,
        "name": policy.name,
        "description": policy.description,
        "is_active": policy.is_active,
        "policy_config": policy.get_policy_config(),
        "created_by": str(policy.created_by) if policy.created_by else None,
        "created_at": policy.created_at.isoformat(),
    }
