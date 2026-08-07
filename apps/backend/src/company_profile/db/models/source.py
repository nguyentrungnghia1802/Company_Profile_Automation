"""SQLAlchemy ORM models for source discovery and content snapshot acquisition."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from urllib.parse import urlparse, urlunparse

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
