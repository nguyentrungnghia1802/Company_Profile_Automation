"""Typed company lifecycle errors shared by application and transport layers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DuplicateCompanyMatch:
    """Safe details describing an existing workspace-scoped company match."""

    submitted_company_name: str
    normalized_name: str
    match_reason: str
    existing_company_id: uuid.UUID | None = None
    existing_company_name: str | None = None


class CompanyDuplicateError(Exception):
    """Raised when creation would violate company identity uniqueness."""

    def __init__(self, match: DuplicateCompanyMatch) -> None:
        super().__init__("COMPANY_DUPLICATE_REVIEW_REQUIRED")
        self.match = match
