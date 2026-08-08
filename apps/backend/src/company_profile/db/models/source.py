"""SQLAlchemy ORM models for source discovery and content snapshot acquisition."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from urllib.parse import urlparse, urlunparse

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from company_profile.db.base import GUID, Base


def normalize_url(url: str) -> str:
    """Normalize URL by lowercasing scheme/host and stripping trailing slash."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    path = parsed.path.rstrip("/")
    if not path:
        path = ""
    normalized_tuple = (scheme, netloc, path, parsed.params, parsed.query, "")
    return urlunparse(normalized_tuple)


def calculate_content_hash(content: bytes) -> str:
    """Calculate SHA-256 hex digest of raw document bytes."""
    return hashlib.sha256(content).hexdigest()


class Source(Base):
    """Discovered web page or registry source for company profile research."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    canonical_url: Mapped[str] = mapped_column(Text(), nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text(), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="web_page")
    authority_tier: Mapped[int] = mapped_column(Integer(), nullable=False, default=3)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="discovered")
    entity_match_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    discovered_via: Mapped[str] = mapped_column(
        String(64), nullable=False, default="manual_url", server_default="manual_url"
    )
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    authority_by_field: Mapped[dict[str, int]] = mapped_column(
        JSON(), nullable=False, default=dict, server_default="{}"
    )
    discovery_provenance: Mapped[list[str]] = mapped_column(
        JSON(), nullable=False, default=list, server_default="[]"
    )
    selection_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    snapshots: Mapped[list[SourceSnapshot]] = relationship(
        "SourceSnapshot", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('registry', 'official_site', 'news', 'directory', 'web_page')",
            name="ck_sources_type",
        ),
        CheckConstraint(
            "status IN ('discovered', 'fetched', 'failed', 'rejected')",
            name="ck_sources_status",
        ),
        UniqueConstraint(
            "workspace_id", "company_id", "normalized_url", name="uq_sources_normalized_url"
        ),
        Index("ix_sources_workspace_company", "workspace_id", "company_id"),
        Index("ix_sources_domain", "workspace_id", "domain"),
    )

    def authority_for_field(self, field_key: str) -> int:
        """Return the source authority tier applicable to one fact field."""
        field_authority = self.authority_by_field or {}
        value = field_authority.get(field_key, field_authority.get("*"))
        if isinstance(value, int) and 1 <= value <= 4:
            return value
        return self.authority_tier


class SourceSnapshot(Base):
    """Immutable content snapshot retrieved from a source URL."""

    __tablename__ = "source_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/html")
    byte_size: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    malware_scan_status: Mapped[str] = mapped_column(String(32), nullable=False, default="clean")
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source: Mapped[Source] = relationship("Source", back_populates="snapshots")

    __table_args__ = (
        CheckConstraint(
            "malware_scan_status IN ('clean', 'infected', 'pending')",
            name="ck_source_snapshots_malware_status",
        ),
        UniqueConstraint("source_id", "content_hash", name="uq_source_snapshots_hash"),
        Index("ix_source_snapshots_source_id", "source_id"),
    )


class DomainPolicy(Base):
    """Allowed or blocked domain rule within a workspace."""

    __tablename__ = "domain_policies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(32), nullable=False, default="blocked")
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "policy_type IN ('blocked', 'allowed', 'trusted')",
            name="ck_domain_policies_type",
        ),
        UniqueConstraint("workspace_id", "domain", name="uq_domain_policies_domain"),
        Index("ix_domain_policies_workspace", "workspace_id", "domain"),
    )


class SourceFetchAttempt(Base):
    """Audit log entry for an HTTP fetch attempt against a source URL."""

    __tablename__ = "source_fetch_attempts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    research_job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True
    )
    adapter: Mapped[str] = mapped_column(String(64), nullable=False, default="httpx")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_url: Mapped[str] = mapped_column(Text(), nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    outcome_code: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "outcome_code IN ('success', 'http_error', 'timeout', "
            "'malware_detected', 'size_exceeded')",
            name="ck_fetch_attempts_outcome",
        ),
        Index("ix_source_fetch_attempts_source", "workspace_id", "source_id"),
    )


class DocumentBlock(Base):
    """Extracted text paragraph, heading, or table block from a source document snapshot."""

    __tablename__ = "document_blocks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    block_key: Mapped[str] = mapped_column(String(128), nullable=False)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False, default="paragraph")
    text_content: Mapped[str] = mapped_column(Text(), nullable=False)
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    snapshot: Mapped[SourceSnapshot] = relationship("SourceSnapshot", backref="blocks")

    __table_args__ = (
        CheckConstraint(
            "block_type IN ('heading', 'paragraph', 'table', 'list')",
            name="ck_document_blocks_type",
        ),
        UniqueConstraint("source_snapshot_id", "block_key", name="uq_document_blocks_key"),
        Index("ix_document_blocks_snapshot", "workspace_id", "source_snapshot_id"),
    )
