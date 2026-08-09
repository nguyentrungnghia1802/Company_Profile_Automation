"""Tests for AuditService, append-only logging, and secret redaction."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.identity import User, Workspace
from company_profile.modules.audit.service import AuditService, redact_sensitive_dict


@pytest.mark.asyncio
async def test_audit_logging_and_redaction(
    db_session: AsyncSession,
) -> None:
    """Test recording audit events and ensuring secrets are redacted."""
    ws = Workspace(id=uuid.uuid4(), name="Audit WS", slug=f"ws-{uuid.uuid4().hex[:6]}")
    usr = User(
        id=uuid.uuid4(),
        auth_provider="mock",
        auth_subject=f"sub-{uuid.uuid4().hex[:6]}",
        email=f"aud-{uuid.uuid4().hex[:6]}@example.com",
        display_name="Auditor",
    )
    db_session.add_all([ws, usr])
    await db_session.flush()

    svc = AuditService(db_session)

    # 1. Test secret redaction function
    untrusted_meta = {
        "user_email": "admin@example.com",
        "api_key": "secret-api-key-12345",
        "nested": {"token": "bearer-token-abc", "safe_field": "hello"},
    }
    safe_meta = redact_sensitive_dict(untrusted_meta)
    assert safe_meta["user_email"] == "admin@example.com"
    assert safe_meta["api_key"] == "[REDACTED]"
    assert safe_meta["nested"]["token"] == "[REDACTED]"
    assert safe_meta["nested"]["safe_field"] == "hello"

    # 2. Record audit event
    log = await svc.record_event(
        workspace_id=ws.id,
        action="policy:activate",
        resource_type="policy_set",
        resource_id="pol-123",
        actor_id=usr.id,
        metadata=untrusted_meta,
    )
    assert log.id is not None
    assert log.action == "policy:activate"
    meta_saved = log.get_metadata()
    assert meta_saved["api_key"] == "[REDACTED]"

    # 3. Query audit trail
    logs = await svc.list_audit_logs(ws.id, action="policy:activate")
    assert len(logs) == 1
    assert logs[0].id == log.id
