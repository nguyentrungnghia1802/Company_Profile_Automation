"""Regression tests for the local Compose authentication bootstrap."""

from __future__ import annotations

from sqlalchemy import select

from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.operations.local_bootstrap import (
    LOCAL_WORKSPACE_ID,
    ensure_local_development_identity,
)


async def test_local_bootstrap_creates_research_capable_membership(db_session) -> None:  # noqa: ANN001
    """The local researcher token receives research:start without company fixtures."""
    await ensure_local_development_identity(db_session)
    await ensure_local_development_identity(db_session)

    workspace = await db_session.get(Workspace, LOCAL_WORKSPACE_ID)
    assert workspace is not None

    user = await db_session.scalar(
        select(User).where(User.auth_subject == "sub_dev_researcher_001")
    )
    assert user is not None
    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == LOCAL_WORKSPACE_ID,
            WorkspaceMember.user_id == user.id,
        )
    )
    assert membership is not None
    assert membership.role == "researcher"
    assert membership.status == "active"

    membership_count = await db_session.scalars(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == LOCAL_WORKSPACE_ID)
    )
    assert len(list(membership_count)) == 3
