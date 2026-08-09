"""Explicit local Compose bootstrap for schema and mock-auth memberships.

This module is intentionally limited to local development. It creates the current
SQLAlchemy schema and deterministic mock identities/workspace membership so the
local UI can authenticate without inventing company data. Production deployment
must continue to use the explicit Alembic migration workflow.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import company_profile.db.models  # noqa: F401  # Register all model metadata.
from company_profile.config.settings import get_settings
from company_profile.db.base import Base
from company_profile.db.models.identity import User, Workspace, WorkspaceMember

LOCAL_WORKSPACE_ID: Final = uuid.UUID("11111111-1111-1111-1111-111111111111")

_LOCAL_IDENTITIES: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "sub_dev_researcher_001",
        "researcher@example.com",
        "Dev Researcher",
        "researcher",
    ),
    ("sub_dev_reviewer_001", "reviewer@example.com", "Dev Reviewer", "reviewer"),
    ("sub_dev_admin_001", "admin@example.com", "Dev Admin", "workspace_admin"),
)


async def ensure_local_development_identity(session: AsyncSession) -> None:
    """Create or repair the local workspace and mock-auth memberships idempotently."""
    workspace = await session.get(Workspace, LOCAL_WORKSPACE_ID)
    if workspace is None:
        workspace = Workspace(
            id=LOCAL_WORKSPACE_ID,
            name="Local Development Workspace",
            slug="local-development",
            default_locale="vi",
            timezone="UTC",
            status="active",
        )
        session.add(workspace)
        await session.flush()
    elif workspace.status != "active":
        workspace.status = "active"

    for auth_subject, email, display_name, role in _LOCAL_IDENTITIES:
        user = await session.scalar(
            select(User).where(
                User.auth_provider == "mock",
                User.auth_subject == auth_subject,
            )
        )
        if user is None:
            user = User(
                auth_provider="mock",
                auth_subject=auth_subject,
                email=email,
                display_name=display_name,
                preferred_locale="vi",
                status="active",
            )
            session.add(user)
            await session.flush()
        else:
            user.email = email
            user.display_name = display_name
            user.status = "active"

        membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )
        if membership is None:
            session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=role,
                    status="active",
                )
            )
        else:
            membership.role = role
            membership.status = "active"

    await session.commit()


async def bootstrap_local_database(database_url: str | None = None) -> None:
    """Create local tables and mock identities without seeding company data."""
    settings = get_settings()
    engine = create_async_engine(database_url or settings.database_url, echo=settings.db_echo)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await ensure_local_development_identity(session)
    finally:
        await engine.dispose()


def main() -> None:
    """Run the local bootstrap command."""
    asyncio.run(bootstrap_local_database())


if __name__ == "__main__":
    main()
