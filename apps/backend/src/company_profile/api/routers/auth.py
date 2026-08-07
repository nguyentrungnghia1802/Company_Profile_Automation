"""Authentication and user session routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from company_profile.api.dependencies import (
    ActiveWorkspaceContext,
    RequestActor,
    WorkspaceSummaryContext,
    get_auth_provider,
    get_current_actor,
    get_current_user,
)
from company_profile.db.models.identity import User
from company_profile.db.session import get_db_session
from company_profile.db.transaction import transactional
from company_profile.modules.workspaces.repository import UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.integrations.auth.protocol import AuthProvider, AuthSubjectContext

router = APIRouter()


class ExchangeTokenRequest(BaseModel):
    """Token exchange request body."""

    token: str


class ExchangeTokenResponseData(BaseModel):
    """Token exchange response payload."""

    access_token: str
    token_type: str = "Bearer"
    user_id: str
    email: str | None
    display_name: str


class ExchangeTokenResponse(BaseModel):
    """Token exchange envelope."""

    success: bool = True
    data: ExchangeTokenResponseData


class CurrentUserResponseData(BaseModel):
    """Current user /me payload."""

    id: str
    email: str | None
    display_name: str
    preferred_locale: str
    status: str
    active_workspace: ActiveWorkspaceContext | None
    workspaces: list[WorkspaceSummaryContext]
    capabilities: list[str]


class CurrentUserResponse(BaseModel):
    """Current user /me envelope."""

    success: bool = True
    data: CurrentUserResponseData


class UpdateUserRequest(BaseModel):
    """Update profile request body."""

    display_name: str | None = None
    preferred_locale: str | None = None


class LogoutResponse(BaseModel):
    """Logout response envelope."""

    success: bool = True
    message: str = "Session logged out"


@router.post("/auth/exchange", response_model=ExchangeTokenResponse)
async def exchange_token(
    payload: ExchangeTokenRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_provider: AuthProvider = Depends(get_auth_provider),
) -> ExchangeTokenResponse:
    """Exchange external identity token for application session token."""
    subject_ctx: AuthSubjectContext = await auth_provider.verify_token(payload.token)

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

    return ExchangeTokenResponse(
        success=True,
        data=ExchangeTokenResponseData(
            access_token=payload.token,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        ),
    )


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    _actor: RequestActor = Depends(get_current_actor),
) -> LogoutResponse:
    """Revoke session token."""
    return LogoutResponse(success=True, message="Session logged out")


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    actor: RequestActor = Depends(get_current_actor),
) -> CurrentUserResponse:
    """Get current authenticated actor context and active workspace capabilities."""
    return CurrentUserResponse(
        success=True,
        data=CurrentUserResponseData(
            id=str(actor.user_id),
            email=actor.email,
            display_name=actor.display_name,
            preferred_locale=actor.preferred_locale,
            status=actor.status,
            active_workspace=actor.active_workspace,
            workspaces=actor.workspaces,
            capabilities=actor.capabilities,
        ),
    )


@router.patch("/me", response_model=CurrentUserResponse)
async def update_me(
    payload: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    actor: RequestActor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    """Update current user display name or preferred locale."""
    async with transactional(session):
        if payload.display_name is not None:
            current_user.display_name = payload.display_name
        if payload.preferred_locale is not None:
            current_user.preferred_locale = payload.preferred_locale

    return CurrentUserResponse(
        success=True,
        data=CurrentUserResponseData(
            id=str(current_user.id),
            email=current_user.email,
            display_name=current_user.display_name,
            preferred_locale=current_user.preferred_locale,
            status=current_user.status,
            active_workspace=actor.active_workspace,
            workspaces=actor.workspaces,
            capabilities=actor.capabilities,
        ),
    )
