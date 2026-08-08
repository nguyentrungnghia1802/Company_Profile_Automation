"""Confidence calculation engine and explainable scoring policy.

Computes a deterministic, explainable confidence score for fact candidates
based on field-specific source authority, support type, recency/freshness decay,
extraction reliability, and multi-source agreement.

Confidence is advisory and explainable; it is never presented as absolute certainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Default Authority Tiers & Field Overrides
# ---------------------------------------------------------------------------

DEFAULT_TIER_SCORES: dict[int, float] = {
    1: 1.00,  # Official Legal Registry / Government
    2: 0.85,  # Official Company Site / Verified Filings
    3: 0.70,  # Reputable Business News / Directory
    4: 0.50,  # General Web Page
}

SUPPORT_TYPE_SCORES: dict[str, float] = {
    "structured": 1.00,
    "direct": 0.95,
    "corroborating": 0.85,
    "contextual": 0.60,
    "human_note": 1.00,
    "contradicting": 0.20,
}

# Field keys where Tier 1 (Registry) is mandatory for top confidence
REGISTRY_PRIMARY_FIELDS: set[str] = {
    "identity.legal_name",
    "identity.tax_id",
    "identity.registration_number",
    "identity.country",
}

# Field keys where Tier 2 (Official Site) has primary authority
OFFICIAL_SITE_PRIMARY_FIELDS: set[str] = {
    "overview.description",
    "products.list",
    "markets.target_markets",
}


@dataclass
class ConfidenceComponents:
    """Breakdown of confidence score components."""

    source_authority_score: float
    support_type_score: float
    freshness_score: float
    extraction_reliability_score: float
    agreement_adjustment: float


@dataclass
class ConfidenceResult:
    """Result of confidence calculation containing total score and explanation."""

    total_score: float
    components: ConfidenceComponents
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "source_authority_score": self.components.source_authority_score,
            "support_type_score": self.components.support_type_score,
            "freshness_score": self.components.freshness_score,
            "extraction_reliability_score": self.components.extraction_reliability_score,
            "agreement_adjustment": self.components.agreement_adjustment,
            "explanation": self.explanation,
        }


class ConfidenceCalculator:
    """Policy engine for calculating explainable confidence scores."""

    def __init__(self, policy_version: int = 1) -> None:
        self.policy_version = policy_version

    def calculate(
        self,
        field_key: str,
        authority_tier: int,
        support_type: str = "direct",
        observed_at: datetime | None = None,
        origin_type: str = "ai",
        ai_confidence_hint: float | None = None,
        independent_domain_count: int = 1,
        has_conflicts: bool = False,
    ) -> ConfidenceResult:
        """Calculate confidence score and explanation for a fact candidate.

        Args:
            field_key: Target field identifier (e.g. 'identity.legal_name').
            authority_tier: Authority tier of the supporting source (1-4).
            support_type: Evidence support type ('direct', 'structured', etc.).
            observed_at: Observation timestamp for freshness decay.
            origin_type: Candidate origin ('ai', 'deterministic', 'user', 'reviewer').
            ai_confidence_hint: Raw confidence hint from AI model (0.0-1.0).
            independent_domain_count: Number of independent domains corroborating value.
            has_conflicts: True if competing material candidate exists.

        Returns:
            ConfidenceResult with total_score bounded to 0.0-1.0 and human-readable explanation.
        """
        # 1. Base Source Authority
        base_authority = DEFAULT_TIER_SCORES.get(authority_tier, 0.50)
        # Apply field-specific authority adjustment
        if field_key in REGISTRY_PRIMARY_FIELDS and authority_tier == 1:
            authority_score = 1.00
        elif field_key in OFFICIAL_SITE_PRIMARY_FIELDS and authority_tier in (1, 2):
            authority_score = 0.95
        else:
            authority_score = base_authority

        # 2. Support Type Score
        supp_score = SUPPORT_TYPE_SCORES.get(support_type, 0.80)

        # 3. Freshness Score
        now = datetime.now(UTC)
        obs_time = observed_at or now
        age_days = max(0, (now - obs_time).days)
        if age_days <= 30:
            freshness_score = 1.00
        elif age_days <= 180:
            freshness_score = 0.90
        elif age_days <= 365:
            freshness_score = 0.80
        else:
            freshness_score = 0.65

        # 4. Extraction Reliability Score
        if origin_type in ("reviewer", "user", "deterministic"):
            reliability_score = 1.00
        elif origin_type == "ai":
            hint = ai_confidence_hint if ai_confidence_hint is not None else 0.80
            reliability_score = max(0.50, min(1.00, hint * 0.95))
        else:
            reliability_score = 0.80

        # 5. Agreement Adjustment
        agreement_adj = 0.0
        if independent_domain_count >= 2:
            agreement_adj += 0.10
        if has_conflicts:
            agreement_adj -= 0.25

        # Weighted combination: Authority (40%), Support (30%), Reliability (15%),
        # Freshness (15%) + Agreement adjustment
        weighted_base = (
            (authority_score * 0.40)
            + (supp_score * 0.30)
            + (reliability_score * 0.15)
            + (freshness_score * 0.15)
        )
        total_score = round(max(0.0, min(1.0, weighted_base + agreement_adj)), 2)

        components = ConfidenceComponents(
            source_authority_score=round(authority_score, 2),
            support_type_score=round(supp_score, 2),
            freshness_score=round(freshness_score, 2),
            extraction_reliability_score=round(reliability_score, 2),
            agreement_adjustment=round(agreement_adj, 2),
        )

        explanation = self._build_explanation(
            total_score=total_score,
            authority_tier=authority_tier,
            support_type=support_type,
            independent_domains=independent_domain_count,
            has_conflicts=has_conflicts,
            origin_type=origin_type,
        )

        return ConfidenceResult(
            total_score=total_score,
            components=components,
            explanation=explanation,
        )

    def _build_explanation(
        self,
        total_score: float,
        authority_tier: int,
        support_type: str,
        independent_domains: int,
        has_conflicts: bool,
        origin_type: str,
    ) -> str:
        tier_names = {
            1: "Tier 1 Official Registry",
            2: "Tier 2 Official Site",
            3: "Tier 3 News/Directory",
            4: "Tier 4 General Web",
        }
        tier_str = tier_names.get(authority_tier, f"Tier {authority_tier}")

        rating = "High" if total_score >= 0.80 else ("Medium" if total_score >= 0.60 else "Low")
        parts = [
            (
                f"{rating} confidence ({total_score:.2f}): supported by "
                f"{tier_str} ({support_type} evidence)"
            )
        ]

        if origin_type in ("reviewer", "user"):
            parts.append("manually verified by human reviewer")
        if independent_domains >= 2:
            parts.append(f"corroborated by {independent_domains} independent domains")
        if has_conflicts:
            parts.append("WARNING: conflicting candidate detected")

        return "; ".join(parts) + "."
