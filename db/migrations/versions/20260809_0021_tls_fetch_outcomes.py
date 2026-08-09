"""Add typed TLS and browser-unavailable fetch outcomes.

Revision ID: 20260809_0021
Revises: 20260809_0020
Create Date: 2026-08-09
"""

from __future__ import annotations

from alembic import op

revision: str = "20260809_0021"
down_revision: str = "20260809_0020"
branch_labels = None
depends_on = None

_PREVIOUS_OUTCOMES = (
    "'success', 'http_error', 'timeout', 'malware_detected', 'size_exceeded', "
    "'decompression_exceeded', 'mime_rejected', 'redirect_blocked', 'max_redirects', "
    "'policy_blocked', 'retry_exhausted', 'parse_error'"
)
_TLS_OUTCOMES = (
    f"{_PREVIOUS_OUTCOMES}, 'connect_error', 'tls_compatibility_failed', "
    "'tls_certificate_failed', 'tls_handshake_failed', 'browser_unavailable'"
)


def upgrade() -> None:
    """Allow sanitized transport-specific failure categories."""
    with op.batch_alter_table("source_fetch_attempts") as batch_op:
        batch_op.drop_constraint("ck_fetch_attempts_outcome", type_="check")
        batch_op.create_check_constraint(
            "ck_fetch_attempts_outcome",
            f"outcome_code IN ({_TLS_OUTCOMES})",
        )


def downgrade() -> None:
    """Restore the previous bounded fetch outcome set."""
    with op.batch_alter_table("source_fetch_attempts") as batch_op:
        batch_op.drop_constraint("ck_fetch_attempts_outcome", type_="check")
        batch_op.create_check_constraint(
            "ck_fetch_attempts_outcome",
            f"outcome_code IN ({_PREVIOUS_OUTCOMES})",
        )
