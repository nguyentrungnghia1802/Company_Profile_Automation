"""SQLAlchemy ORM model for versioned policy sets."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from company_profile.db.base import GUID, Base

if TYPE_CHECKING:
    from company_profile.db.models.identity import User, Workspace


class PolicySet(Base):
    """Immutable versioned policy configuration for workspace rules."""

    __tablename__ = "policy_sets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="Default Workspace Policy"
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_policy_sets_version",
            "workspace_id",
            "version_number",
            unique=True,
        ),
    )

    def get_policy_config(self) -> dict[str, Any]:
        """Deserialize policy configuration JSON."""
        if isinstance(self.policy_json, str):
            return json.loads(self.policy_json)
        return self.policy_json or {}
