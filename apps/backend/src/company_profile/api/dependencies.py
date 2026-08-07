"""FastAPI dependency injection utilities for authentication and workspace authorization."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from company_profile.api.errors import ForbiddenError
from company_profile.config.settings import get_settings
from company_profile.db.models.identity import User, WorkspaceMember
from company_profile.db.session import get_db_session
from company_profile.db.transaction import transactional
from company_profile.integrations.auth.mock_auth import MockAuthProvider
from company_profile.modules.workspaces.repository import (
    UserRepository,
    WorkspaceRepository,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.integrations.auth.protocol import AuthProvider, AuthSubjectContext

# Role capability mapping table
ROLE_CAPABILITIES: dict[str, list[str]] = {
    "researcher": [
        "company:read",
        "company:create",
        "research:start",
        "source:fetch",
        "fact:candidate_create",
    ],
    "reviewer": [
        "company:read",
        "company:create",
        "company:update",
        "research:start",
        "source:fetch",
        "fact:candidate_create",
        "fact:review",
        "conflict:resolve",
        "profile:publish",
        "company:archive",
        "company:merge",
    ],
    "officer": [
        "company:read",
        "export:generate",
        "audit:view",
    ],
    "workspace_admin": [
        "company:read",
        "company:create",
        "company:update",
        "research:start",
        "workspace:admin",
        "member:manage",
        "policy:manage",
    ],
}


class ActiveWorkspaceContext(BaseModel):
    """Context model for currently active workspace."""

    id: uuid.UUID
    name: str
    slug: str
    role: str
    capabilities: list[str]


class WorkspaceSummaryContext(BaseModel):
    """Summary model for available user workspace membership."""

    id: uuid.UUID
    name: str
    slug: str
    role: str


class RequestActor(BaseModel):
    """Authenticated request actor context."""

    user_id: uuid.UUID
    email: str | None
    display_name: str
    preferred_locale: str
    status: str
    active_workspace: ActiveWorkspaceContext | None
    workspaces: list[WorkspaceSummaryContext]
    capabilities: list[str]


def get_auth_provider() -> AuthProvider:
    """Return configured AuthProvider implementation singleton."""
    settings = get_settings()
    if settings.auth_mode == "mock":
        return MockAuthProvider()
    return MockAuthProvider()


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db_session),
    auth_provider: AuthProvider = Depends(get_auth_provider),
) -> User:
    """Verify authorization token and synchronize current User entity."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = authorization[7:].strip()
    try:
        subject_ctx: AuthSubjectContext = await auth_provider.verify_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user_repo = UserRepository(session)
    async with transactional(session):
        user = await user_repo.get_by_auth(
            provider=subject_ctx.auth_provider, subject=subject_ctx.auth_subject
        )
        if not user:
            user = User(
                auth_provider=subject_ctx.auth_provider,
                auth_subject=subject_ctx.auth_subject,
                email=subject_ctx.email,
                display_name=subject_ctx.display_name,
                preferred_locale=subject_ctx.preferred_locale,
                status="active",
            )
            await user_repo.create(user)

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled or inactive",
        )

    return user


async def get_current_actor(
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> RequestActor:
    """Build full RequestActor context with workspace memberships and capabilities."""
    ws_repo = WorkspaceRepository(session)

    stmt = select(WorkspaceMember).where(
        WorkspaceMember.user_id == current_user.id, WorkspaceMember.status == "active"
    )
    result = await session.execute(stmt)
    active_memberships = result.scalars().all()

    workspaces_list: list[WorkspaceSummaryContext] = []
    active_ws_ctx: ActiveWorkspaceContext | None = None

    selected_ws_id: uuid.UUID | None = None
    if x_workspace_id:
        try:
            selected_ws_id = uuid.UUID(x_workspace_id)
        except ValueError:
            selected_ws_id = None

    for m in active_memberships:
        ws = await ws_repo.get_by_id(m.workspace_id)
        if not ws or ws.status != "active":
            continue

        role_caps = ROLE_CAPABILITIES.get(m.role, [])
        ws_summary = WorkspaceSummaryContext(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            role=m.role,
        )
        workspaces_list.append(ws_summary)

        if (selected_ws_id and ws.id == selected_ws_id) or not active_ws_ctx:
            active_ws_ctx = ActiveWorkspaceContext(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                role=m.role,
                capabilities=role_caps,
            )

    capabilities = active_ws_ctx.capabilities if active_ws_ctx else []

    return RequestActor(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        preferred_locale=current_user.preferred_locale,
        status=current_user.status,
        active_workspace=active_ws_ctx,
        workspaces=workspaces_list,
        capabilities=capabilities,
    )


def require_capability(
    required_capability: str,
) -> Callable[[RequestActor], RequestActor]:
    """FastAPI dependency factory enforcing a specific capability on current actor."""

    def _dependency(actor: RequestActor = Depends(get_current_actor)) -> RequestActor:
        if required_capability not in actor.capabilities:
            raise ForbiddenError(
                code="INSUFFICIENT_CAPABILITY",
                message=f"Required capability '{required_capability}' is missing.",
            )
        return actor

    return _dependency
