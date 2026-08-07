"""SQLAlchemy ORM models for Company Profiles, Aliases, and Relationships."""

from __future__ import annotations

import datetime
import re
import unicodedata
import uuid
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from company_profile.db.models.identity import Workspace


def normalize_company_name(name: str) -> str:
    """Normalize company name for exact and fuzzy alias matching.

    Strips accents, converts to lowercase, removes punctuation and common enterprise suffix noise.
    """
    if not name:
        return ""

    # Normalize unicode to NFD and strip combining accents
    nfkd_form = unicodedata.normalize("NFKD", name)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # Lowercase
    cleaned = only_ascii.lower()

    # Replace common legal suffixes/prefixes with space
    noise_patterns = [
        r"\bcong ty tnhh\b",
        r"\bcong ty co phan\b",
        r"\bco phan\b",
        r"\btnhh\b",
        r"\bcty\b",
        r"\binc\b",
        r"\bcorp\b",
        r"\bcorporation\b",
        r"\bltd\b",
        r"\bllc\b",
        r"\bplc\b",
        r"\bgmbh\b",
    ]
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, " ", cleaned)

    # Remove special characters
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)

    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned or name.lower().strip()


class CompanyProfile(Base):
    """Canonical company profile entity."""

    __tablename__ = "company_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'merged')",
            name="ck_company_profiles_status",
        ),
        Index("ix_company_profiles_workspace_normalized", "workspace_id", "normalized_name"),
        Index("ix_company_profiles_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    founding_date: Mapped[datetime.date | None] = mapped_column(nullable=True)
    headquarters_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", server_default="draft"
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("company_profiles.id", ondelete="SET NULL"), nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace", lazy="raise")
    aliases: Mapped[list[CompanyAlias]] = relationship(
        "CompanyAlias", back_populates="company", cascade="all, delete-orphan", lazy="selectin"
    )


class CompanyAlias(Base):
    """Company name alias or alternative trading name."""

    __tablename__ = "company_aliases"
    __table_args__ = (
        CheckConstraint(
            "alias_type IN ('trade_name', 'former_name', 'abbreviation', 'misspelling')",
            name="ck_company_aliases_type",
        ),
        UniqueConstraint(
            "workspace_id", "normalized_alias", name="uq_company_aliases_workspace_alias"
        ),
        Index("ix_company_aliases_workspace_normalized", "workspace_id", "normalized_alias"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="trade_name", server_default="trade_name"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company: Mapped[CompanyProfile] = relationship(
        "CompanyProfile", back_populates="aliases", lazy="raise"
    )


class CompanyRelationship(Base):
    """Relationship between two company profiles within a workspace."""

    __tablename__ = "company_relationships"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_company_id",
            "target_company_id",
            "relationship_type",
            name="uq_company_relationships",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    target_company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
