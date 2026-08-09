"""SQLAlchemy models for published versions, field values, and evidence snapshots."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
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


class ProfileVersion(Base):
    """Immutable published version of a company profile."""

    __tablename__ = "profile_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    profile_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("profile_drafts.id", ondelete="SET NULL"), nullable=True
    )

    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    policy_set_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    publication_note: Mapped[str | None] = mapped_column(Text(), nullable=True)

    published_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)

    source_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    overall_confidence: Mapped[float] = mapped_column(Float(), nullable=False, default=1.0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    field_values: Mapped[list[ProfileFieldValue]] = relationship(
        "ProfileFieldValue", back_populates="profile_version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('published', 'withdrawn', 'superseded')",
            name="ck_profile_versions_status",
        ),
        UniqueConstraint("company_id", "version_number", name="uq_profile_versions_company_ver"),
        Index(
            "ix_profile_versions_company",
            "workspace_id",
            "company_id",
            "status",
        ),
    )

    def withdraw(self, reason: str) -> None:
        """Mark published version as withdrawn with mandatory reason."""
        self.status = "withdrawn"
        self.withdrawn_at = datetime.now(UTC)
        self.withdrawal_reason = reason

    def mark_superseded(self) -> None:
        """Transition status from published to superseded when a newer version publishes."""
        if self.status == "published":
            self.status = "superseded"
            self.superseded_at = datetime.now(UTC)


class ProfileFieldValue(Base):
    """Field value snapshot belonging to an immutable ProfileVersion."""

    __tablename__ = "profile_field_values"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("profile_versions.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    context_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="string")
    value_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_status: Mapped[str] = mapped_column(String(32), nullable=False, default="verified")

    confidence_score: Mapped[float] = mapped_column(Float(), nullable=False, default=1.0)
    confidence_explanation: Mapped[str | None] = mapped_column(Text(), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ai")
    display_order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    profile_version: Mapped[ProfileVersion] = relationship(
        "ProfileVersion", back_populates="field_values"
    )
    evidences: Mapped[list[ProfileFieldEvidence]] = relationship(
        "ProfileFieldEvidence", back_populates="field_value", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "display_status IN ('verified', 'inferred', 'estimated', 'conflicting', 'unknown')",
            name="ck_profile_field_values_display_status",
        ),
        Index(
            "ix_profile_field_values_version",
            "workspace_id",
            "profile_version_id",
            "field_key",
        ),
    )

    def get_value(self) -> Any:
        """Parse value_json into Python object."""
        if self.value_json is None:
            return None
        return json.loads(self.value_json)


class ProfileFieldEvidence(Base):
    """Evidence excerpt snapshot linked to a published profile field value."""

    __tablename__ = "profile_field_evidences"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_field_value_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("profile_field_values.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True
    )
    original_excerpt: Mapped[str] = mapped_column(Text(), nullable=False)
    translated_excerpt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_authority_tier: Mapped[int] = mapped_column(Integer(), nullable=False, default=4)
    support_type: Mapped[str] = mapped_column(String(32), nullable=False, default="direct")
    evidence_quality_score: Mapped[float] = mapped_column(Float(), nullable=False, default=1.0)

    field_value: Mapped[ProfileFieldValue] = relationship(
        "ProfileFieldValue", back_populates="evidences"
    )

    __table_args__ = (
        Index(
            "ix_profile_field_evidences_field_val",
            "workspace_id",
            "profile_field_value_id",
        ),
    )
