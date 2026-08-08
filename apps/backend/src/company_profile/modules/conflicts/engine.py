"""Conflict Engine for detecting material disagreements between fact candidates.

Preserves full candidate history and creates or reopens Conflict records without
overwriting prior candidates. Supports field-specific equivalence comparators,
time-scoped multi-value acceptance, and targeted re-research requests.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.conflict import Conflict, ConflictCandidate
from company_profile.db.models.fact import FactCandidate

# ---------------------------------------------------------------------------
# Comparators
# ---------------------------------------------------------------------------


def values_are_materially_different(field_key: str, val1: Any, val2: Any) -> bool:
    """Compare two field values using field-specific equivalence rules.

    Returns True if val1 and val2 represent a material disagreement.
    Returns False if they are equivalent (ignoring minor formatting/casing/whitespace).
    """
    if val1 is None or val2 is None:
        return False

    # String values: normalize whitespace, casing, accents/legal suffixes if identity name
    if isinstance(val1, str) and isinstance(val2, str):
        v1_clean = val1.strip().lower()
        v2_clean = val2.strip().lower()
        if v1_clean == v2_clean:
            return False
        # If identity.legal_name, check if one contains the other
        if field_key == "identity.legal_name":
            words1 = set(v1_clean.split())
            words2 = set(v2_clean.split())
            if words1 and words2 and (words1.issubset(words2) or words2.issubset(words1)):
                return False
        return True

    # Numeric values: allow 5% tolerance for estimates
    if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
        diff = abs(val1 - val2)
        max_val = max(abs(val1), abs(val2))
        return not (max_val > 0 and (diff / max_val) <= 0.05)

    # List values (e.g. products, markets, partners): check set equality
    if isinstance(val1, list) and isinstance(val2, list):
        if len(val1) == len(val2):
            s1 = json.dumps(val1, sort_keys=True)
            s2 = json.dumps(val2, sort_keys=True)
            if s1 == s2:
                return False
        return True

    # Dictionary / complex JSON: compare serialized JSON
    j1 = json.dumps(val1, sort_keys=True) if not isinstance(val1, str) else val1
    j2 = json.dumps(val2, sort_keys=True) if not isinstance(val2, str) else val2
    return j1 != j2


def evaluate_materiality(field_key: str) -> str:
    """Determine conflict materiality level based on field category."""
    critical_fields = {"identity.legal_name", "identity.tax_id", "identity.registration_number"}
    high_fields = {"overview.hq_address", "size.employee_count_range", "size.revenue_range"}
    if field_key in critical_fields:
        return "critical"
    if field_key in high_fields:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Conflict Engine Class
# ---------------------------------------------------------------------------


class ConflictEngine:
    """Engine for evaluating candidates, detecting conflicts, and resolving/reopening conflicts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def detect_and_update_conflicts(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        field_key: str,
        context_key: str = "",
    ) -> Conflict | None:
        """Scan active candidates for a field and create or reopen a Conflict.

        Preserves candidate history (non-destructive).
        """
        # Fetch non-rejected candidates for this field
        stmt = (
            select(FactCandidate)
            .where(
                FactCandidate.workspace_id == workspace_id,
                FactCandidate.company_id == company_id,
                FactCandidate.field_key == field_key,
                FactCandidate.context_key == context_key,
                FactCandidate.fact_status.in_(
                    ["candidate", "validated", "recommended", "accepted", "superseded"]
                ),
                FactCandidate.is_unknown.is_(False),
            )
            .order_by(FactCandidate.created_at.asc())
        )
        result = await self._session.execute(stmt)
        candidates = result.scalars().all()

        if len(candidates) < 2:
            return None

        # Check pairwise for material disagreement
        competing: list[FactCandidate] = [candidates[0]]
        primary_val = candidates[0].get_value()

        for cand in candidates[1:]:
            val = cand.get_value()
            if values_are_materially_different(field_key, primary_val, val):
                competing.append(cand)

        if len(competing) < 2:
            return None  # All candidates are equivalent

        materiality = evaluate_materiality(field_key)

        # Check if an existing Conflict record exists for this field
        stmt_conf = (
            select(Conflict)
            .options(selectinload(Conflict.candidates))
            .where(
                Conflict.workspace_id == workspace_id,
                Conflict.company_id == company_id,
                Conflict.field_key == field_key,
                Conflict.context_key == context_key,
            )
        )
        res_conf = await self._session.execute(stmt_conf)
        conflict = res_conf.scalar_one_or_none()

        if conflict is None:
            # Create new Conflict
            conflict = Conflict(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                company_id=company_id,
                field_key=field_key,
                context_key=context_key,
                status="open",
                materiality=materiality,
                detected_policy_version=1,
            )
            self._session.add(conflict)
            await self._session.flush()

            # Attach candidates
            for idx, c in enumerate(competing):
                role = "primary" if idx == 0 else "competing"
                cc = ConflictCandidate(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    conflict_id=conflict.id,
                    fact_candidate_id=c.id,
                    candidate_role=role,
                    is_selected=False,
                )
                self._session.add(cc)
            await self._session.flush()

        elif conflict.status in ("resolved", "accepted_multiple", "dismissed"):
            # Check if any new candidate was added that is not in conflict.candidates
            existing_cand_ids = {cc.fact_candidate_id for cc in conflict.candidates}
            new_cands = [c for c in competing if c.id not in existing_cand_ids]
            if new_cands:
                # Reopen conflict when new material evidence arrives (P7-017)
                conflict.reopen(
                    reason=f"New candidate {new_cands[0].id} introduced material disagreement"
                )
                for c in new_cands:
                    cc = ConflictCandidate(
                        id=uuid.uuid4(),
                        workspace_id=workspace_id,
                        conflict_id=conflict.id,
                        fact_candidate_id=c.id,
                        candidate_role="competing",
                        is_selected=False,
                    )
                    self._session.add(cc)
                await self._session.flush()

        self._session.expire(conflict, ["candidates"])
        stmt_reload = (
            select(Conflict)
            .options(selectinload(Conflict.candidates))
            .where(Conflict.id == conflict.id)
        )
        res_reload = await self._session.execute(stmt_reload)
        return res_reload.scalar_one()

    async def resolve_conflict(
        self,
        workspace_id: uuid.UUID,
        conflict_id: uuid.UUID,
        resolution_type: str,
        reason: str,
        selected_candidate_ids: list[uuid.UUID],
        resolved_by: uuid.UUID | None = None,
    ) -> Conflict:
        """Resolve a conflict with explicit resolution type and reason.

        Resolution types:
        - 'select_one': Mark selected candidate as accepted, others as rejected/superseded.
        - 'accepted_multiple': Multi-value time-scoped acceptance (P7-016).
        - 'dismissed': Difference was non-material formatting difference.
        """
        stmt = (
            select(Conflict)
            .options(selectinload(Conflict.candidates))
            .where(
                Conflict.workspace_id == workspace_id,
                Conflict.id == conflict_id,
            )
        )
        res = await self._session.execute(stmt)
        conflict = res.scalar_one_or_none()
        if conflict is None:
            raise ValueError(f"Conflict '{conflict_id}' not found in workspace.")

        conflict.resolve(resolution_type=resolution_type, reason=reason, resolved_by=resolved_by)

        for cc in conflict.candidates:
            if cc.fact_candidate_id in selected_candidate_ids:
                cc.is_selected = True
                # Update FactCandidate status
                cand = await self._session.get(FactCandidate, cc.fact_candidate_id)
                if cand:
                    cand.accept()
            else:
                cc.is_selected = False
                if resolution_type == "select_one":
                    cand = await self._session.get(FactCandidate, cc.fact_candidate_id)
                    if cand:
                        cand.supersede()

        await self._session.flush()
        return conflict

    async def list_conflicts(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        status: str | None = None,
    ) -> Sequence[Conflict]:
        """List Conflicts for a company with optional status filter."""
        stmt = (
            select(Conflict)
            .options(
                selectinload(Conflict.candidates).selectinload(ConflictCandidate.fact_candidate)
            )
            .where(
                Conflict.workspace_id == workspace_id,
                Conflict.company_id == company_id,
            )
        )
        if status is not None:
            stmt = stmt.where(Conflict.status == status)
        stmt = stmt.order_by(Conflict.created_at.desc())
        res = await self._session.execute(stmt)
        return res.scalars().all()
