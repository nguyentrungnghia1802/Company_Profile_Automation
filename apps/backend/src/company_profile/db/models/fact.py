"""SQLAlchemy ORM models for fact candidates and source evidence links."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class FactCandidate(Base):
    """Extracted or proposed company profile fact candidate."""

    __tablename__ = "fact_candidates"

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
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    context_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="string")
    value_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    normalized_value_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_value: Mapped[str | None] = mapped_column(Text(), nullable=True)

    fact_status: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate")
    origin_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ai")
    is_inferred: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_unknown: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    confidence_score: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    confidence_components: Mapped[str | None] = mapped_column(Text(), nullable=True)
    confidence_explanation: Mapped[str | None] = mapped_column(Text(), nullable=True)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(32), nullable=False, default="fresh")

    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    row_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    evidences: Mapped[list[Evidence]] = relationship(
        "Evidence", back_populates="fact_candidate", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "fact_status IN ('candidate', 'validated', 'recommended', "
            "'accepted', 'rejected', 'superseded', 'stale')",
            name="ck_fact_candidates_status",
        ),
        CheckConstraint(
            "origin_type IN ('ai', 'deterministic', 'user', 'reviewer', 'import')",
            name="ck_fact_candidates_origin",
        ),
        CheckConstraint(
            "freshness_status IN ('fresh', 'warning', 'stale')",
            name="ck_fact_candidates_freshness",
        ),
        Index(
            "ix_fact_candidates_company_field",
            "workspace_id",
            "company_id",
            "field_key",
            "fact_status",
        ),
    )

    def get_value(self) -> Any:
        """Parse value_json into Python object."""
        if self.value_json is None:
            return None
        return json.loads(self.value_json)

    def set_value(self, val: Any) -> None:
        """Serialize value to value_json and set display_value."""
        if val is None:
            self.value_json = None
            self.display_value = None
        else:
            self.value_json = json.dumps(val, ensure_ascii=False)
            self.display_value = (
                str(val)
                if not isinstance(val, (dict, list))
                else json.dumps(val, ensure_ascii=False)
            )

    def validate(self) -> None:
        """Transition status from candidate to validated."""
        if self.fact_status == "candidate":
            self.fact_status = "validated"
            self.row_version = (self.row_version or 1) + 1

    def recommend(self) -> None:
        """Transition status to recommended."""
        if self.fact_status in ("candidate", "validated"):
            self.fact_status = "recommended"
            self.row_version = (self.row_version or 1) + 1

    def accept(self) -> None:
        """Transition status to accepted."""
        self.fact_status = "accepted"
        self.row_version = (self.row_version or 1) + 1

    def reject(self) -> None:
        """Transition status to rejected."""
        self.fact_status = "rejected"
        self.row_version = (self.row_version or 1) + 1

    def supersede(self) -> None:
        """Transition status to superseded."""
        self.fact_status = "superseded"
        self.row_version = (self.row_version or 1) + 1

    def mark_stale(self) -> None:
        """Mark freshness status as stale."""
        self.freshness_status = "stale"
        self.row_version = (self.row_version or 1) + 1


class Evidence(Base):
    """Source document excerpt supporting a fact candidate."""

    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    fact_candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("fact_candidates.id", ondelete="CASCADE"), nullable=False
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    document_block_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("document_blocks.id", ondelete="CASCADE"), nullable=False
    )
    original_excerpt: Mapped[str] = mapped_column(Text(), nullable=False)
    translated_excerpt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    start_offset: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    support_type: Mapped[str] = mapped_column(String(32), nullable=False, default="direct")
    evidence_quality_score: Mapped[float] = mapped_column(Float(), nullable=False, default=1.0)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False, default="ai")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    fact_candidate: Mapped[FactCandidate] = relationship(
        "FactCandidate", back_populates="evidences"
    )

    __table_args__ = (
        CheckConstraint(
            "support_type IN ('direct', 'structured', 'corroborating', "
            "'contextual', 'contradicting', 'human_note')",
            name="ck_evidences_support_type",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'accepted', 'rejected')",
            name="ck_evidences_review_status",
        ),
        UniqueConstraint(
            "fact_candidate_id",
            "source_snapshot_id",
            "document_block_id",
            name="uq_evidences_candidate_block",
        ),
        Index("ix_evidences_fact_candidate", "workspace_id", "fact_candidate_id"),
    )
