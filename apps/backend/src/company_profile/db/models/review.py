"""SQLAlchemy ORM models for human review tasks and append-only decision audit log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

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


class ReviewTask(Base):
    """Human review task requiring reviewer evaluation, claim, and completion."""

    __tablename__ = "review_tasks"

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
    conflict_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("conflicts.id", ondelete="SET NULL"), nullable=True
    )
    fact_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("fact_candidates.id", ondelete="SET NULL"), nullable=True
    )

    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decision_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)

    row_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decisions: Mapped[list[ReviewDecision]] = relationship(
        "ReviewDecision", back_populates="review_task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "task_type IN ('identity_ambiguity', 'high_impact_fact', "
            "'field_conflict', 'publication_approval', 'source_verification')",
            name="ck_review_tasks_type",
        ),
        CheckConstraint(
            "status IN ('open', 'claimed', 'in_review', "
            "'changes_requested', 'completed', 'cancelled', 'reopened')",
            name="ck_review_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('urgent', 'high', 'medium', 'low')",
            name="ck_review_tasks_priority",
        ),
        Index(
            "ix_review_tasks_ws_status",
            "workspace_id",
            "status",
            "priority",
            "created_at",
        ),
        Index(
            "ix_review_tasks_company",
            "workspace_id",
            "company_id",
            "status",
        ),
    )

    def claim(self, user_id: uuid.UUID) -> None:
        """Claim open review task."""
        if self.status not in ("open", "reopened", "changes_requested"):
            raise ValueError(f"Cannot claim task in status '{self.status}'")
        self.assigned_to = user_id
        self.claimed_at = datetime.now(UTC)
        self.status = "in_review"
        self.row_version = (self.row_version or 1) + 1

    def release(self) -> None:
        """Release claimed task back to open pool."""
        self.assigned_to = None
        self.claimed_at = None
        self.status = "open"
        self.row_version = (self.row_version or 1) + 1

    def complete(self, decision_code: str, reason: str) -> None:
        """Complete review task with decision code and rationale."""
        self.status = "completed"
        self.decision_code = decision_code
        self.decision_reason = reason
        self.completed_at = datetime.now(UTC)
        self.row_version = (self.row_version or 1) + 1

    def reopen(self, reason: str) -> None:
        """Reopen completed task when new context is introduced."""
        self.status = "reopened"
        self.decision_reason = reason
        self.completed_at = None
        self.row_version = (self.row_version or 1) + 1


class ReviewDecision(Base):
    """Append-only audit record of reviewer decisions and actions."""

    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    review_task_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)

    previous_state_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    new_state_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review_task: Mapped[ReviewTask] = relationship("ReviewTask", back_populates="decisions")

    __table_args__ = (
        Index(
            "ix_review_decisions_task",
            "workspace_id",
            "review_task_id",
            "created_at",
        ),
    )
