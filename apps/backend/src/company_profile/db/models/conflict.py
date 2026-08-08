"""SQLAlchemy ORM models for material conflicts between competing fact candidates."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.fact import FactCandidate


class Conflict(Base):
    """Group of competing fact candidates for the same company field key."""

    __tablename__ = "conflicts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    context_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    materiality: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    detected_policy_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)

    resolution_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    row_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    candidates: Mapped[list[ConflictCandidate]] = relationship(
        "ConflictCandidate", back_populates="conflict", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'needs_research', 'resolved', "
            "'accepted_multiple', 'dismissed', 'reopened')",
            name="ck_conflicts_status",
        ),
        CheckConstraint(
            "materiality IN ('critical', 'high', 'medium', 'low')",
            name="ck_conflicts_materiality",
        ),
        Index("ix_conflicts_company_field", "workspace_id", "company_id", "field_key", "status"),
    )

    def resolve(
        self,
        resolution_type: str,
        reason: str,
        resolved_by: uuid.UUID | None = None,
    ) -> None:
        """Resolve conflict with explicit resolution type and reason."""
        self.status = "resolved" if resolution_type != "accepted_multiple" else "accepted_multiple"
        self.resolution_type = resolution_type
        self.resolution_reason = reason
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now(UTC)
        self.row_version = (self.row_version or 1) + 1

    def reopen(self, reason: str | None = None) -> None:
        """Reopen a previously resolved conflict when new material evidence arrives."""
        self.status = "reopened"
        if reason:
            self.resolution_reason = (
                f"Reopened: {reason} (Previous resolution: {self.resolution_reason})"
            )
        self.row_version = (self.row_version or 1) + 1


class ConflictCandidate(Base):
    """Join table linking a FactCandidate to a Conflict."""

    __tablename__ = "conflict_candidates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    conflict_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("conflicts.id", ondelete="CASCADE"), nullable=False
    )
    fact_candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("fact_candidates.id", ondelete="CASCADE"), nullable=False
    )
    candidate_role: Mapped[str] = mapped_column(String(32), nullable=False, default="competing")
    is_selected: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conflict: Mapped[Conflict] = relationship("Conflict", back_populates="candidates")
    fact_candidate: Mapped[FactCandidate] = relationship("FactCandidate")

    __table_args__ = (
        CheckConstraint(
            "candidate_role IN ('primary', 'competing')",
            name="ck_conflict_candidates_role",
        ),
        UniqueConstraint("conflict_id", "fact_candidate_id", name="uq_conflict_candidates_pair"),
        Index("ix_conflict_candidates_conflict", "workspace_id", "conflict_id"),
    )
