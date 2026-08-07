"""SQLAlchemy ORM models for research workflow jobs and tasks."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base


class ResearchJob(Base):
    """Research job tracking an automated company profile research execution."""

    __tablename__ = "research_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default="initial")
    scope: Mapped[str] = mapped_column(Text(), nullable=False, default="{}")
    requested_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="vi")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer(), nullable=False, default=10)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tasks: Mapped[list[ResearchTask]] = relationship(
        "ResearchTask", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('initial', 'refresh', 'targeted')",
            name="ck_research_jobs_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_jobs_status",
        ),
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_research_jobs_idempotency"),
        Index("ix_research_jobs_workspace_company", "workspace_id", "company_id"),
        Index("ix_research_jobs_status", "workspace_id", "status"),
    )

    def start(self) -> None:
        """Transition job from pending to running."""
        if self.status not in ("pending", "queued"):
            raise ValueError(f"Cannot start job in state '{self.status}'.")
        self.status = "running"
        self.started_at = datetime.now(UTC)
        self.version = (self.version or 1) + 1

    def complete(self) -> None:
        """Transition job to completed state."""
        if self.status != "running":
            raise ValueError(f"Cannot complete job in state '{self.status}'.")
        self.status = "completed"
        self.completed_at = datetime.now(UTC)
        self.version = (self.version or 1) + 1

    def fail(self, error_message: str) -> None:
        """Transition job to failed state with error message."""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.now(UTC)
        self.version = (self.version or 1) + 1

    def request_cancel(self) -> None:
        """Request cancellation of running job."""
        self.cancel_requested_at = datetime.now(UTC)
        self.status = "cancelled"
        self.completed_at = datetime.now(UTC)
        self.version = (self.version or 1) + 1


class ResearchTask(Base):
    """Granular task step within a research job (search, fetch, extract, synthesize)."""

    __tablename__ = "research_tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    research_job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False
    )
    step_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer(), nullable=False, default=3)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_payload: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_payload: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    job: Mapped[ResearchJob] = relationship("ResearchJob", back_populates="tasks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_tasks_status",
        ),
        Index("ix_research_tasks_job_id", "research_job_id"),
        Index("ix_research_tasks_claim", "status", "next_attempt_at"),
    )

    def claim(self, worker_id: str, lease_seconds: int = 300) -> None:
        """Claim task for worker execution with lease expiration."""
        now = datetime.now(UTC)
        self.status = "running"
        self.lease_owner = worker_id
        self.lease_expires_at = datetime.fromtimestamp(now.timestamp() + lease_seconds, tz=UTC)
        self.started_at = now
        self.attempt_count = (self.attempt_count or 0) + 1
        self.version = (self.version or 1) + 1

    def release(self) -> None:
        """Release claimed task back to queued/pending state."""
        self.status = "pending"
        self.lease_owner = None
        self.lease_expires_at = None
        self.version = (self.version or 1) + 1

    def complete(self, output_payload: str | None = None) -> None:
        """Mark task as successfully completed."""
        self.status = "completed"
        self.output_payload = output_payload
        self.completed_at = datetime.now(UTC)
        self.lease_owner = None
        self.lease_expires_at = None
        self.version = (self.version or 1) + 1

    def fail(self, error_message: str) -> None:
        """Mark task attempt as failed."""
        self.error_message = error_message
        self.lease_owner = None
        self.lease_expires_at = None
        if (self.attempt_count or 0) >= self.max_attempts:
            self.status = "failed"
            self.completed_at = datetime.now(UTC)
        else:
            self.status = "pending"
        self.version = (self.version or 1) + 1
