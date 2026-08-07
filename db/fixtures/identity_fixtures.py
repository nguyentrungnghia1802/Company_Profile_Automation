"""Deterministic development users and workspace fixtures."""

from __future__ import annotations

import uuid

from company_profile.db.models.identity import User, Workspace, WorkspaceMember

# Fixed UUIDs for deterministic development and E2E testing
DEV_USER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
DEV_ADMIN_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
DEV_REVIEWER_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
DEV_WORKSPACE_ID = uuid.UUID("a1111111-1111-4111-8111-111111111111")


def get_dev_user() -> User:
    """Return deterministic researcher development user."""
    return User(
        id=DEV_USER_ID,
        auth_provider="mock",
        auth_subject="sub_dev_researcher_001",
        email="researcher@example.com",
        display_name="Dev Researcher",
        preferred_locale="vi",
        status="active",
    )


def get_dev_admin() -> User:
    """Return deterministic workspace admin development user."""
    return User(
        id=DEV_ADMIN_ID,
        auth_provider="mock",
        auth_subject="sub_dev_admin_001",
        email="admin@example.com",
        display_name="Dev Admin",
        preferred_locale="vi",
        status="active",
    )


def get_dev_reviewer() -> User:
    """Return deterministic reviewer development user."""
    return User(
        id=DEV_REVIEWER_ID,
        auth_provider="mock",
        auth_subject="sub_dev_reviewer_001",
        email="reviewer@example.com",
        display_name="Dev Reviewer",
        preferred_locale="vi",
        status="active",
    )


def get_dev_workspace() -> Workspace:
    """Return deterministic development workspace."""
    return Workspace(
        id=DEV_WORKSPACE_ID,
        name="AI Riser Vietnam",
        slug="ai-riser-vn",
        default_locale="vi",
        timezone="UTC",
        status="active",
    )


def get_dev_memberships() -> list[WorkspaceMember]:
    """Return initial memberships for development users in the development workspace."""
    return [
        WorkspaceMember(
            workspace_id=DEV_WORKSPACE_ID,
            user_id=DEV_USER_ID,
            role="researcher",
            status="active",
        ),
        WorkspaceMember(
            workspace_id=DEV_WORKSPACE_ID,
            user_id=DEV_ADMIN_ID,
            role="workspace_admin",
            status="active",
        ),
        WorkspaceMember(
            workspace_id=DEV_WORKSPACE_ID,
            user_id=DEV_REVIEWER_ID,
            role="reviewer",
            status="active",
        ),
    ]
