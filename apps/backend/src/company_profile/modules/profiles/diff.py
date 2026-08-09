"""Profile version diffing service for field-level comparison and audit visualization."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from company_profile.db.models.publication import ProfileVersion


class ProfileDiffService:
    """Service for computing structured field-level diffs between two ProfileVersion snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compare_versions(
        self, workspace_id: uuid.UUID, version_id_a: uuid.UUID, version_id_b: uuid.UUID
    ) -> dict[str, Any]:
        """Compute detailed field diff between version A (base) and version B (target)."""
        ver_a = await self._get_version(workspace_id, version_id_a)
        ver_b = await self._get_version(workspace_id, version_id_b)

        if not ver_a or not ver_b:
            raise ValueError("One or both profile versions were not found.")

        map_a = {f"{fv.field_key}:{fv.context_key}": fv for fv in ver_a.field_values}
        map_b = {f"{fv.field_key}:{fv.context_key}": fv for fv in ver_b.field_values}

        all_keys = set(map_a.keys()).union(map_b.keys())
        field_diffs = []

        added_count = 0
        modified_count = 0
        removed_count = 0
        unchanged_count = 0

        for key in sorted(all_keys):
            fv_a = map_a.get(key)
            fv_b = map_b.get(key)

            if fv_a is None and fv_b is not None:
                added_count += 1
                field_diffs.append(
                    {
                        "field_key": fv_b.field_key,
                        "context_key": fv_b.context_key,
                        "change_type": "added",
                        "old_value": None,
                        "new_value": fv_b.get_value(),
                        "old_display_value": None,
                        "new_display_value": fv_b.display_value,
                        "old_confidence": None,
                        "new_confidence": fv_b.confidence_score,
                        "old_evidence_count": 0,
                        "new_evidence_count": len(fv_b.evidences),
                    }
                )
            elif fv_a is not None and fv_b is None:
                removed_count += 1
                field_diffs.append(
                    {
                        "field_key": fv_a.field_key,
                        "context_key": fv_a.context_key,
                        "change_type": "removed",
                        "old_value": fv_a.get_value(),
                        "new_value": None,
                        "old_display_value": fv_a.display_value,
                        "new_display_value": None,
                        "old_confidence": fv_a.confidence_score,
                        "new_confidence": None,
                        "old_evidence_count": len(fv_a.evidences),
                        "new_evidence_count": 0,
                    }
                )
            elif fv_a is not None and fv_b is not None:
                is_changed = (
                    fv_a.display_value != fv_b.display_value
                    or fv_a.value_json != fv_b.value_json
                    or fv_a.display_status != fv_b.display_status
                )
                if is_changed:
                    modified_count += 1
                    field_diffs.append(
                        {
                            "field_key": fv_b.field_key,
                            "context_key": fv_b.context_key,
                            "change_type": "modified",
                            "old_value": fv_a.get_value(),
                            "new_value": fv_b.get_value(),
                            "old_display_value": fv_a.display_value,
                            "new_display_value": fv_b.display_value,
                            "old_confidence": fv_a.confidence_score,
                            "new_confidence": fv_b.confidence_score,
                            "old_evidence_count": len(fv_a.evidences),
                            "new_evidence_count": len(fv_b.evidences),
                        }
                    )
                else:
                    unchanged_count += 1

        return {
            "version_a": {
                "id": str(ver_a.id),
                "version_number": ver_a.version_number,
                "status": ver_a.status,
                "published_at": ver_a.published_at.isoformat(),
            },
            "version_b": {
                "id": str(ver_b.id),
                "version_number": ver_b.version_number,
                "status": ver_b.status,
                "published_at": ver_b.published_at.isoformat(),
            },
            "summary": {
                "added_count": added_count,
                "modified_count": modified_count,
                "removed_count": removed_count,
                "unchanged_count": unchanged_count,
                "confidence_delta": round(ver_b.overall_confidence - ver_a.overall_confidence, 2),
            },
            "field_diffs": field_diffs,
        }

    async def _get_version(
        self, workspace_id: uuid.UUID, version_id: uuid.UUID
    ) -> ProfileVersion | None:
        stmt = (
            select(ProfileVersion)
            .options(
                selectinload(ProfileVersion.field_values).selectinload(
                    ProfileVersion.field_values.property.mapper.class_.evidences
                )
            )
            .where(
                ProfileVersion.workspace_id == workspace_id,
                ProfileVersion.id == version_id,
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()
