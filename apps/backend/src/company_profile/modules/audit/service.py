"""Audit service for recording append-only security logs with automatic secret redaction."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.audit import AuditLog

if TYPE_CHECKING:
    from collections.abc import Sequence


SENSITIVE_KEYS = {"api_key", "secret", "password", "token", "auth_token", "access_token", "private_key"}


def redact_sensitive_dict(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively redact sensitive keys in metadata dictionary."""
    if not data:
        return data

    redacted = {}
    for k, v in data.items():
        if any(sk in k.lower() for sk in SENSITIVE_KEYS):
            redacted[k] = "[REDACTED]"
        elif isinstance(v, dict):
            redacted[k] = redact_sensitive_dict(v)
        else:
            redacted[k] = v
    return redacted


class AuditService:
    """Service for appending and querying security audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_event(
        self,
        workspace_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "user",
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Record an append-only audit event with redacted metadata."""
        safe_meta = redact_sensitive_dict(metadata)
        entry = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=safe_meta,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_audit_logs(
        self,
        workspace_id: uuid.UUID,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """Query paginated audit logs for workspace."""
        stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        res = await self._session.execute(stmt)
        return res.scalars().all()
