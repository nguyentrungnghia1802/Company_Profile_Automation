"""SQLAlchemy ORM models for profile drafts and field selections."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.company import CompanyProfile
    from company_profile.db.models.fact import FactCandidate
    from company_profile.db.models.identity import User, Workspace


class ProfileDraft(Base):
    """Draft company profile under assembly before formal publication review."""

    __tablename__ = "profile_drafts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    research_job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="building")
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary_draft: Mapped[str | None] = mapped_column(Text(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    row_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    field_selections: Mapped[list[DraftFieldSelection]] = relationship(
        "DraftFieldSelection", back_populates="profile_draft", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('building', 'ready_for_review', 'changes_requested', "
            "'approved', 'superseded', 'discarded')",
            name="ck_profile_drafts_status",
        ),
        Index(
            "ix_profile_drafts_company",
            "workspace_id",
            "company_id",
            "status",
        ),
    )


class DraftFieldSelection(Base):
    """Mapping of a profile field key to a chosen FactCandidate in a draft."""

    __tablename__ = "draft_field_selections"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_draft_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("profile_drafts.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    context_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    selected_fact_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("fact_candidates.id", ondelete="SET NULL"), nullable=True
    )
    selection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    reviewer_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile_draft: Mapped[ProfileDraft] = relationship(
        "ProfileDraft", back_populates="field_selections"
    )
    selected_fact_candidate: Mapped[FactCandidate | None] = relationship(
        "FactCandidate"
    )

    __table_args__ = (
        CheckConstraint(
            "selection_state IN ('accepted', 'overridden', 'rejected', 'unknown')",
            name="ck_draft_field_selections_state",
        ),
        Index(
            "ix_draft_field_selections_draft",
            "workspace_id",
            "profile_draft_id",
            "field_key",
        ),
    )
