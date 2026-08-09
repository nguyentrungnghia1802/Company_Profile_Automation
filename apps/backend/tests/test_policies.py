"""Tests for PolicyService and PolicySet ORM models."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.identity import User, Workspace
from company_profile.modules.policies.service import (
    DEFAULT_POLICY_CONFIG,
    PolicyService,
)


@pytest.mark.asyncio
async def test_policy_set_lifecycle(
    db_session: AsyncSession,
) -> None:
    """Test creating, versioning, and activating policy sets."""
    ws = Workspace(id=uuid.uuid4(), name="Policy WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"pol-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Policy Admin",
    )
    db_session.add_all([ws, usr])
    await db_session.flush()

    svc = PolicyService(db_session)

    # 1. Create v1
    p1 = await svc.create_policy_set(
        workspace_id=ws.id,
        name="Strict Financial Policy v1",
        policy_config=DEFAULT_POLICY_CONFIG,
        description="First policy draft",
        created_by=usr.id,
    )
    assert p1.version_number == 1
    assert p1.is_active is False

    # 2. Activate v1
    active_p1 = await svc.activate_policy_set(ws.id, p1.id)
    assert active_p1.is_active is True

    # 3. Create v2
    custom_cfg = dict(DEFAULT_POLICY_CONFIG)
    custom_cfg["ai_budget_per_job_usd"] = 10.0
    p2 = await svc.create_policy_set(
        workspace_id=ws.id,
        name="Higher Budget Policy v2",
        policy_config=custom_cfg,
        created_by=usr.id,
    )
    assert p2.version_number == 2
    assert p2.is_active is False

    # 4. Activate v2 (v1 should become inactive)
    active_p2 = await svc.activate_policy_set(ws.id, p2.id)
    assert active_p2.is_active is True

    # Verify v1 is inactive now
    reloaded_p1 = await svc.get_policy_set(ws.id, p1.id)
    assert reloaded_p1 is not None
    assert reloaded_p1.is_active is False

    current_active = await svc.get_active_policy_set(ws.id)
    assert current_active is not None
    assert current_active.id == p2.id
    assert current_active.get_policy_config()["ai_budget_per_job_usd"] == 10.0
