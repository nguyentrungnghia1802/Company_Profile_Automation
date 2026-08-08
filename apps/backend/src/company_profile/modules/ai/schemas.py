"""Pydantic extraction schemas for AI-extracted company profile fields.

Each schema:
- Has typed field_key, value, evidence_block_ids, confidence_hint, is_inferred, is_unknown.
- Requires at least one evidence_block_id for every non-unknown fact.
- Uses is_unknown=True as a valid signal; value must be None when unknown.
- Prevents AI from silently inventing values for missing fields.

All schemas are validated before storing extracted candidates.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Base fact and result types
# ---------------------------------------------------------------------------


class ExtractedFact(BaseModel):
    """A single extracted field candidate referencing evidence blocks."""

    field_key: str = Field(..., description="Dotted field identifier, e.g. 'identity.legal_name'")
    value: Any = Field(None, description="Typed field value; None when is_unknown=True")
    evidence_block_ids: list[str] = Field(
        default_factory=list,
        description="Block IDs from DocumentBlock.block_key that support this fact",
    )
    confidence_hint: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Raw model confidence hint (0.0-1.0); not the final confidence score",
    )
    is_inferred: bool = Field(
        default=False,
        description="True when value is derived by reasoning rather than direct extraction",
    )
    is_unknown: bool = Field(
        default=False,
        description="True when field is not found in evidence; value must be None",
    )

    @model_validator(mode="after")
    def validate_evidence_and_unknown(self) -> ExtractedFact:
        """Enforce evidence requirement and unknown/value consistency."""
        if self.is_unknown:
            if self.value is not None:
                raise ValueError(
                    f"Field '{self.field_key}': is_unknown=True but value is not None."
                )
        else:
            if not self.evidence_block_ids:
                raise ValueError(
                    f"Field '{self.field_key}': non-unknown fact must have at least one "
                    "evidence_block_id."
                )
            if self.value is None:
                raise ValueError(
                    f"Field '{self.field_key}': value cannot be None when is_unknown=False."
                )
        return self


class BaseExtractionResult(BaseModel):
    """Common structure for all extraction schema outputs."""

    facts: list[ExtractedFact] = Field(default_factory=list)
    unknown_fields: list[str] = Field(
        default_factory=list,
        description="Field keys that were not found in the evidence",
    )


# ---------------------------------------------------------------------------
# 1. Identity and legal information
# ---------------------------------------------------------------------------


class IdentityExtractionResult(BaseExtractionResult):
    """Extracted company identity and legal registration fields.

    Supported field_keys:
    - identity.legal_name: Full registered legal name.
    - identity.brand_name: Common trading or brand name.
    - identity.tax_id: Tax identification number (string to preserve leading zeros).
    - identity.registration_number: Company registration / business number.
    - identity.country: ISO 3166-1 alpha-2 country code.
    - identity.legal_form: Legal entity form (e.g. 'LLC', 'JSC', 'Cty TNHH').
    - identity.founding_year: 4-digit founding year integer.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_identity_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "identity.legal_name",
            "identity.brand_name",
            "identity.tax_id",
            "identity.registration_number",
            "identity.country",
            "identity.legal_form",
            "identity.founding_year",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in IdentityExtractionResult. "
                    f"Valid keys: {sorted(valid_keys)}"
                )
            if fact.field_key == "identity.founding_year" and not fact.is_unknown:
                year = fact.value
                if not isinstance(year, int) or not (1800 <= year <= 2100):
                    raise ValueError(
                        f"identity.founding_year must be an integer between 1800 and 2100, "
                        f"got: {year!r}"
                    )
            if fact.field_key == "identity.country" and not fact.is_unknown:
                country = str(fact.value)
                if len(country) != 2 or not country.isalpha():
                    raise ValueError(
                        f"identity.country must be an ISO 3166-1 alpha-2 code "
                        f"(2 uppercase letters), got: {country!r}"
                    )
        return facts


# ---------------------------------------------------------------------------
# 2. Overview, industry, and business model
# ---------------------------------------------------------------------------


class OverviewExtractionResult(BaseExtractionResult):
    """Extracted overview, description, industry, and HQ fields.

    Supported field_keys:
    - overview.description: Short company description (max 2000 chars).
    - overview.industry: Primary industry classification string.
    - overview.business_model: B2B, B2C, B2G, marketplace, etc.
    - overview.hq_address: Headquarters address string.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_overview_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "overview.description",
            "overview.industry",
            "overview.business_model",
            "overview.hq_address",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in OverviewExtractionResult."
                )
            if (
                fact.field_key == "overview.description"
                and not fact.is_unknown
                and (not isinstance(fact.value, str) or len(fact.value) > 2000)
            ):
                raise ValueError("overview.description must be a string of max 2000 characters.")
        return facts


# ---------------------------------------------------------------------------
# 3. Products and services
# ---------------------------------------------------------------------------


class ProductEntry(BaseModel):
    """A single product or service item."""

    name: str
    category: str | None = None
    description: str | None = None


class ProductsExtractionResult(BaseExtractionResult):
    """Extracted products and services catalog.

    Supported field_keys:
    - products.list: List of ProductEntry objects.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_products_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {"products.list"}
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in ProductsExtractionResult."
                )
            if fact.field_key == "products.list" and not fact.is_unknown:
                if not isinstance(fact.value, list):
                    raise ValueError("products.list value must be a list.")
                for item in fact.value:
                    if not isinstance(item, dict) or "name" not in item:
                        raise ValueError(
                            "Each products.list item must be a dict with at least 'name'."
                        )
        return facts


# ---------------------------------------------------------------------------
# 4. Size and footprint
# ---------------------------------------------------------------------------


class SizeExtractionResult(BaseExtractionResult):
    """Extracted employee count, revenue range, and office count.

    Supported field_keys:
    - size.employee_count_range: String range e.g. '50-200' or '<50'.
    - size.revenue_range: String range e.g. '$1M-$10M'.
    - size.office_count: Integer number of office locations.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_size_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "size.employee_count_range",
            "size.revenue_range",
            "size.office_count",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(f"Unknown field_key '{fact.field_key}' in SizeExtractionResult.")
            if (
                fact.field_key == "size.office_count"
                and not fact.is_unknown
                and (not isinstance(fact.value, int) or fact.value < 0)
            ):
                raise ValueError("size.office_count must be a non-negative integer.")
        return facts


# ---------------------------------------------------------------------------
# 5. Markets, customers, and partners
# ---------------------------------------------------------------------------


class MarketsExtractionResult(BaseExtractionResult):
    """Extracted target markets, customer segments, and key partners.

    Supported field_keys:
    - markets.target_markets: List of country names or region strings.
    - markets.customer_segments: List of customer segment descriptions.
    - markets.key_partners: List of known partner/customer organization names.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_markets_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "markets.target_markets",
            "markets.customer_segments",
            "markets.key_partners",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in MarketsExtractionResult."
                )
            if not fact.is_unknown and not isinstance(fact.value, list):
                raise ValueError(f"Field '{fact.field_key}' must have a list value.")
        return facts


# ---------------------------------------------------------------------------
# 6. Leadership and ownership
# ---------------------------------------------------------------------------


class PersonEntry(BaseModel):
    """A named individual in a leadership or ownership role."""

    name: str
    role: str | None = None
    title: str | None = None


class LeadershipExtractionResult(BaseExtractionResult):
    """Extracted leadership and ownership information.

    Supported field_keys:
    - leadership.ceo: PersonEntry dict for CEO.
    - leadership.founders: List of PersonEntry dicts.
    - leadership.board_members: List of PersonEntry dicts.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_leadership_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "leadership.ceo",
            "leadership.founders",
            "leadership.board_members",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in LeadershipExtractionResult."
                )
            if fact.is_unknown:
                continue
            if fact.field_key == "leadership.ceo":
                if not isinstance(fact.value, dict) or "name" not in fact.value:
                    raise ValueError("leadership.ceo must be a dict with at least 'name'.")
            elif fact.field_key in ("leadership.founders", "leadership.board_members"):
                if not isinstance(fact.value, list):
                    raise ValueError(f"'{fact.field_key}' must be a list of person dicts.")
                for item in fact.value:
                    if not isinstance(item, dict) or "name" not in item:
                        raise ValueError(
                            f"Each item in '{fact.field_key}' must have at least 'name'."
                        )
        return facts


# ---------------------------------------------------------------------------
# 7. Innovation, awards, certifications, funding, and recent activity
# ---------------------------------------------------------------------------


class FundingRound(BaseModel):
    """A single funding round event."""

    round_type: str | None = None  # e.g. 'Series A', 'Seed'
    amount_usd: float | None = None
    year: int | None = None
    investors: list[str] = Field(default_factory=list)


class InnovationExtractionResult(BaseExtractionResult):
    """Extracted innovation, awards, certifications, funding, and recent activities.

    Supported field_keys:
    - innovation.awards: List of award name strings.
    - innovation.certifications: List of certification name strings.
    - innovation.funding_rounds: List of FundingRound dicts.
    - innovation.recent_activities: List of recent activity description strings.
    """

    @field_validator("facts", mode="after")
    @classmethod
    def validate_innovation_fields(cls, facts: list[ExtractedFact]) -> list[ExtractedFact]:
        valid_keys = {
            "innovation.awards",
            "innovation.certifications",
            "innovation.funding_rounds",
            "innovation.recent_activities",
        }
        for fact in facts:
            if fact.field_key not in valid_keys:
                raise ValueError(
                    f"Unknown field_key '{fact.field_key}' in InnovationExtractionResult."
                )
            if not fact.is_unknown and not isinstance(fact.value, list):
                raise ValueError(f"Field '{fact.field_key}' must have a list value.")
        return facts


# ---------------------------------------------------------------------------
# Schema registry
# ---------------------------------------------------------------------------

OPERATION_SCHEMA_MAP: dict[str, type[BaseExtractionResult]] = {
    "extract_identity": IdentityExtractionResult,
    "extract_overview": OverviewExtractionResult,
    "extract_products": ProductsExtractionResult,
    "extract_size": SizeExtractionResult,
    "extract_markets": MarketsExtractionResult,
    "extract_leadership": LeadershipExtractionResult,
    "extract_innovation": InnovationExtractionResult,
}


def get_schema_for_operation(operation: str) -> type[BaseExtractionResult]:
    """Return the Pydantic schema class for a given extraction operation name."""
    schema = OPERATION_SCHEMA_MAP.get(operation)
    if schema is None:
        raise ValueError(
            f"Unknown extraction operation '{operation}'. "
            f"Valid operations: {sorted(OPERATION_SCHEMA_MAP)}"
        )
    return schema
