"""Policy service for managing versioned immutable policy sets."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.policy import PolicySet

if TYPE_CHECKING:
    from collections.abc import Sequence


DEFAULT_POLICY_CONFIG: dict[str, Any] = {
    "source_authority_tiers": {
        "government_registry": 1.0,
        "official_website": 0.85,
        "trusted_news": 0.70,
        "social_media": 0.40,
    },
    "freshness_thresholds_days": {
        "identity": 365,
        "financials": 180,
        "leadership": 90,
    },
    "mandatory_review_fields": [
        "identity.legal_name",
        "identity.tax_id",
        "financials.revenue",
    ],
    "ai_budget_per_job_usd": 5.0,
}


class PolicyService:
    """Service for managing versioned workspace policy sets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_policy_set(
        self,
        workspace_id: uuid.UUID,
        name: str,
        policy_config: dict[str, Any],
        description: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> PolicySet:
        """Create a new versioned PolicySet."""
        stmt = (
            select(PolicySet.version_number)
            .where(PolicySet.workspace_id == workspace_id)
            .order_by(PolicySet.version_number.desc())
        )
        res = await self._session.execute(stmt)
        latest_v = res.scalar_one_or_none() or 0
        next_v = latest_v + 1

        policy = PolicySet(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            version_number=next_v,
            name=name,
            description=description,
            is_active=False,
            policy_json=policy_config,
            created_by=created_by,
        )
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def activate_policy_set(self, workspace_id: uuid.UUID, policy_id: uuid.UUID) -> PolicySet:
        """Activate a policy set, deactivating all other versions for the workspace."""
        policy = await self.get_policy_set(workspace_id, policy_id)
        if not policy:
            raise ValueError(f"PolicySet '{policy_id}' not found.")

        # Deactivate all
        await self._session.execute(
            update(PolicySet).where(PolicySet.workspace_id == workspace_id).values(is_active=False)
        )

        policy.is_active = True
        await self._session.flush()
        return policy

    async def get_active_policy_set(self, workspace_id: uuid.UUID) -> PolicySet | None:
        """Get currently active PolicySet for workspace."""
        stmt = select(PolicySet).where(
            PolicySet.workspace_id == workspace_id,
            PolicySet.is_active.is_(True),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_policy_set(
        self, workspace_id: uuid.UUID, policy_id: uuid.UUID
    ) -> PolicySet | None:
        """Get PolicySet by ID."""
        stmt = select(PolicySet).where(
            PolicySet.workspace_id == workspace_id,
            PolicySet.id == policy_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_policy_sets(self, workspace_id: uuid.UUID) -> Sequence[PolicySet]:
        """List all policy versions for workspace."""
        stmt = (
            select(PolicySet)
            .where(PolicySet.workspace_id == workspace_id)
            .order_by(PolicySet.version_number.desc())
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()
