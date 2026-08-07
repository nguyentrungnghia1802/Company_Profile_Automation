"""Deterministic development fixtures for company profiles, aliases, and relationships."""

from __future__ import annotations

import uuid

from db.fixtures.identity_fixtures import DEV_WORKSPACE_ID

from company_profile.db.models.company import CompanyProfile, normalize_company_name

DEV_COMPANY_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
DEV_COMPANY_TAX_ID = "0101234567"
DEV_COMPANY_NAME = "Công ty TNHH AI Riser Việt Nam"


def get_dev_company(workspace_id: uuid.UUID = DEV_WORKSPACE_ID) -> CompanyProfile:
    """Return a deterministic dev company profile instance."""
    return CompanyProfile(
        id=DEV_COMPANY_ID,
        workspace_id=workspace_id,
        company_name=DEV_COMPANY_NAME,
        normalized_name=normalize_company_name(DEV_COMPANY_NAME),
        legal_name=DEV_COMPANY_NAME,
        tax_id=DEV_COMPANY_TAX_ID,
        registration_number="0101234567",
        industry="Software & AI",
        website_url="https://airiser.vn",
        status="published",
        confidence_score=0.95,
        version=1,
    )
