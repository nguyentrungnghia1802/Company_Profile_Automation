"""ORM models for provider-neutral research queries and search metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.research import ResearchJob


class ResearchQuery(Base):
    """Generated or user-supplied query used only to discover public sources."""

    __tablename__ = "research_queries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    research_job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False
    )
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, default="source_discovery")
    requested_section: Mapped[str] = mapped_column(String(64), nullable=False, default="official")
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_by: Mapped[str] = mapped_column(
        String(64), nullable=False, default="deterministic_template"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[ResearchJob] = relationship("ResearchJob", back_populates="queries")
    results: Mapped[list[SearchResult]] = relationship(
        "SearchResult", back_populates="query", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_research_queries_workspace_job", "workspace_id", "research_job_id"),
    )


class SearchResult(Base):
    """Search-provider metadata retained for ranking and audit, never evidence."""

    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    research_query_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("research_queries.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text(), nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    title: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    rank: Mapped[int] = mapped_column(Integer(), nullable=False)
    provider_metadata: Mapped[dict[str, object]] = mapped_column(
        JSON(), nullable=False, default=dict, server_default="{}"
    )
    selection_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="candidate", server_default="candidate"
    )
    selection_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    entity_match_score: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="web_page")
    result_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    query: Mapped[ResearchQuery] = relationship("ResearchQuery", back_populates="results")

    __table_args__ = (
        CheckConstraint(
            "selection_status IN ('candidate', 'review', 'selected', 'rejected')",
            name="ck_search_results_selection_status",
        ),
        Index("ix_search_results_workspace_query", "workspace_id", "research_query_id"),
        Index("ix_search_results_normalized_url", "workspace_id", "normalized_url"),
    )
