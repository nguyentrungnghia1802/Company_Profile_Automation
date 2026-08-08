"""SQLAlchemy ORM model for AI run audit and usage tracking."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from company_profile.db.base import GUID, Base


class AiRun(Base):
    """Immutable audit record for a single AI provider call (extraction or translation)."""

    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="SET NULL"), nullable=True
    )
    research_job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="mock")
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_token_count: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    output_token_count: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float(), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    validation_outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="passed")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "operation IN ('extract_identity', 'extract_overview', 'extract_products', "
            "'extract_size', 'extract_markets', 'extract_leadership', 'extract_innovation', "
            "'translate')",
            name="ck_ai_runs_operation",
        ),
        CheckConstraint(
            "validation_outcome IN ('passed', 'failed', 'skipped')",
            name="ck_ai_runs_validation_outcome",
        ),
        Index("ix_ai_runs_workspace_company", "workspace_id", "company_id"),
        Index("ix_ai_runs_workspace_operation", "workspace_id", "operation"),
    )
