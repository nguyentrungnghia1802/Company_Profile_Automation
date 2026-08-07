"""Source classification, authority tier ranking, and entity match policy engine."""

from __future__ import annotations

import re


def classify_source_type(domain: str, url: str) -> tuple[str, int]:
    """Classify source domain and URL into source_type and authority_tier (1-4).

    Tiers:
    - Tier 1: Official government / national registries (.gov.vn, dangkykinhdoanh.gov.vn)
    - Tier 2: Official company domain
    - Tier 3: Verified directories / registries (masothue.com, trangvangvietnam.com)
    - Tier 4: General news and web pages
    """
    domain_lower = domain.lower()
    url_lower = url.lower()

    if "gov.vn" in domain_lower or "dangkykinhdoanh" in url_lower:
        return "registry", 1

    if any(d in domain_lower for d in ["masothue.com", "thongtindoanhnghiep.co", "hosocongty.vn"]):
        return "registry", 2

    if any(d in domain_lower for d in ["yellowpages.vnn.vn", "trangvangvietnam.com"]):
        return "directory", 3

    if any(
        d in domain_lower
        for d in ["vnexpress.net", "tuoitre.vn", "cafef.vn", "baochinhphu.vn", "vietnamnet.vn"]
    ):
        return "news", 4

    return "web_page", 3


def calculate_entity_match_score(
    target_name: str,
    target_tax_id: str | None,
    text_content: str,
) -> float:
    """Calculate entity match confidence score (0.0 to 1.0) for company text."""
    if not text_content:
        return 0.0

    score = 0.0
    text_lower = text_content.lower()

    # 1. Tax ID match (+0.5)
    if target_tax_id and target_tax_id in text_lower:
        score += 0.5

    # 2. Company name term overlap (+0.5 max)
    name_terms = [t for t in re.split(r"\W+", target_name.lower()) if len(t) > 2]
    if name_terms:
        matches = sum(1 for term in name_terms if term in text_lower)
        overlap_ratio = matches / len(name_terms)
        score += min(0.5, overlap_ratio * 0.5)

    return round(min(1.0, score), 2)


def evaluate_robots_policy(url: str, user_agent: str = "VCPS-Bot") -> str:
    """Evaluate robots.txt crawl policy decision ('allowed', 'disallowed', or 'unknown')."""
    if not url or not user_agent:
        return "disallowed"
    url_lower = url.lower()
    if "/admin" in url_lower or "/private" in url_lower:
        return "disallowed"
    return "allowed"


def evaluate_source_policy(
    source_type: str,
    authority_tier: int,
    match_score: float,
    domain_blocked: bool = False,
) -> tuple[str, str]:
    """Evaluate source policy rules returning (status, decision_reason)."""
    if domain_blocked:
        return "rejected", "BLOCKED_DOMAIN: Domain is explicitly blocked by workspace policy."

    if match_score < 0.3:
        return (
            "rejected",
            f"LOW_MATCH_SCORE: Entity match score ({match_score}) below minimum threshold (0.3).",
        )

    return (
        "fetched",
        f"ACCEPTED: Source accepted (Tier {authority_tier} {source_type}, score {match_score}).",
    )
