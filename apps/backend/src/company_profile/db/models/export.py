"""SQLAlchemy ORM model for export jobs and private file downloads."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.publication import ProfileVersion


class ExportJob(Base):
    """Job tracking structured JSON or PDF generation of an immutable ProfileVersion."""

    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("profile_versions.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    export_format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="vi")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    include_source_appendix: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    include_internal_notes: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile_version: Mapped[ProfileVersion] = relationship("ProfileVersion")

    __table_args__ = (
        CheckConstraint(
            "export_format IN ('pdf', 'json')",
            name="ck_export_jobs_format",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'expired')",
            name="ck_export_jobs_status",
        ),
        Index(
            "ix_export_jobs_version",
            "workspace_id",
            "profile_version_id",
            "status",
        ),
    )

    def mark_completed(self, object_key: str, checksum: str, file_size: int) -> None:
        """Mark export job completed with storage key and checksum."""
        self.status = "completed"
        self.object_key = object_key
        self.checksum_sha256 = checksum
        self.file_size_bytes = file_size
        self.completed_at = datetime.now(UTC)

    def mark_failed(self, message: str) -> None:
        """Mark export job failed with error message."""
        self.status = "failed"
        self.error_message = message
        self.completed_at = datetime.now(UTC)
