"""SQLAlchemy ORM model for Innovation Program Fit Assessment."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.company import CompanyProfile
    from company_profile.db.models.identity import User, Workspace


class ProgramFitAssessment(Base):
    """Program fit assessment entity with explainable criteria and evidence links."""

    __tablename__ = "program_fit_assessments"
    __table_args__ = (
        Index("ix_program_fit_assessments_ws_company", "workspace_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    program_name: Mapped[str] = mapped_column(String(100), nullable=False)
    overall_fit_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="review_recommended"
    )
    fit_score: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    assessment_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    reviewer_override_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
