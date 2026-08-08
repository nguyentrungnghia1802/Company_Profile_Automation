"""Freshness evaluation engine for company profile facts.

Calculates freshness status ('fresh', 'warning', 'stale') based on field-specific
recency policies.
"""

from __future__ import annotations

from datetime import UTC, datetime

# Default freshness threshold policies in days
FIELD_FRESHNESS_THRESHOLDS: dict[str, dict[str, int]] = {
    # Identity & registration fields change rarely
    "identity": {"warning_days": 365, "stale_days": 730},
    # Overview & business model
    "overview": {"warning_days": 180, "stale_days": 365},
    # Product catalog & pricing
    "products": {"warning_days": 90, "stale_days": 180},
    # Employee count & revenue range
    "size": {"warning_days": 180, "stale_days": 365},
    # Target markets & partners
    "markets": {"warning_days": 180, "stale_days": 365},
    # Leadership & board
    "leadership": {"warning_days": 180, "stale_days": 365},
    # Innovation, awards, funding, recent activity
    "innovation": {"warning_days": 60, "stale_days": 120},
}

DEFAULT_THRESHOLDS: dict[str, int] = {"warning_days": 180, "stale_days": 365}


class FreshnessEvaluator:
    """Evaluates the freshness of a fact candidate based on observation time and field policy."""

    def evaluate(self, field_key: str, observed_at: datetime | None) -> str:
        """Evaluate freshness status for a given field_key and observation timestamp.

        Args:
            field_key: Target field identifier (e.g. 'identity.legal_name').
            observed_at: Timestamp when fact was last observed in source.

        Returns:
            One of 'fresh', 'warning', or 'stale'.
        """
        if observed_at is None:
            return "stale"

        section = field_key.split(".")[0] if "." in field_key else field_key
        thresholds = FIELD_FRESHNESS_THRESHOLDS.get(section, DEFAULT_THRESHOLDS)

        now = datetime.now(UTC)
        age_days = max(0, (now - observed_at).days)

        if age_days > thresholds["stale_days"]:
            return "stale"
        if age_days > thresholds["warning_days"]:
            return "warning"
        return "fresh"
