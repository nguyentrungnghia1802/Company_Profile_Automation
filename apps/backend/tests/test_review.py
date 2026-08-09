"""Tests for review lifecycle, optimistic locking, and decision audit logs."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace
from company_profile.modules.review.service import ReviewTaskService


@pytest.mark.asyncio
async def test_review_task_lifecycle(
    db_session: AsyncSession,
) -> None:
    """Test creating, claiming, completing, and reopening a review task."""
    ws = Workspace(id=uuid.uuid4(), name="Review WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Reviewer",
    )
    cp = CompanyProfile(
        id=uuid.uuid4(), workspace_id=ws.id, company_name="Acme Ltd", normalized_name="acme ltd"
    )
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    svc = ReviewTaskService(db_session)

    # 1. Create task
    task = await svc.create_task(
        workspace_id=ws.id,
        company_id=cp.id,
        task_type="identity_ambiguity",
        title="Resolve Ambiguous Entity Name",
        description="Verify legal incorporation country",
        priority="high",
    )
    assert task.id is not None
    assert task.status == "open"
    assert task.row_version == 1

    # 2. Claim task
    claimed = await svc.claim_task(ws.id, task.id, usr.id)
    assert claimed.status == "in_review"
    assert claimed.assigned_to == usr.id
    assert claimed.row_version == 2

    # 3. Complete task
    completed = await svc.complete_task(
        workspace_id=ws.id,
        task_id=task.id,
        actor_id=usr.id,
        decision_code="entity_confirmed",
        reason="Official business register matches company domain.",
        expected_row_version=2,
    )
    assert completed.status == "completed"
    assert completed.decision_code == "entity_confirmed"
    assert completed.row_version == 3

    # 4. Check decisions log
    task_with_decisions = await svc.get_task(ws.id, task.id)
    assert task_with_decisions is not None
    assert len(task_with_decisions.decisions) == 2  # claim + complete
    assert task_with_decisions.decisions[0].action == "claim"
    assert task_with_decisions.decisions[1].action == "complete"

    # 5. Reopen task
    reopened = await svc.reopen_task(
        workspace_id=ws.id,
        task_id=task.id,
        actor_id=usr.id,
        reason="New registration snapshot received.",
    )
    assert reopened.status == "reopened"
    assert reopened.row_version == 4


@pytest.mark.asyncio
async def test_review_task_version_conflict(
    db_session: AsyncSession,
) -> None:
    """Test optimistic row_version mismatch on completing review task."""
    ws = Workspace(id=uuid.uuid4(), name="Review WS 2", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Reviewer 2",
    )
    cp = CompanyProfile(
        id=uuid.uuid4(), workspace_id=ws.id, company_name="Acme Ltd", normalized_name="acme ltd"
    )
    db_session.add_all([ws, usr, cp])
    await db_session.flush()

    svc = ReviewTaskService(db_session)

    task = await svc.create_task(
        workspace_id=ws.id,
        company_id=cp.id,
        task_type="publication_approval",
        title="Approve Profile",
    )
    await svc.claim_task(ws.id, task.id, usr.id)

    with pytest.raises(ValueError, match="Row version conflict"):
        await svc.complete_task(
            workspace_id=ws.id,
            task_id=task.id,
            actor_id=usr.id,
            decision_code="approved",
            reason="Lgtm",
            expected_row_version=99,  # Mismatched expected version
        )
