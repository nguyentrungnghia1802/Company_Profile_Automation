"""Unit tests for source classification, authority tier ranking, and entity match policy."""

from __future__ import annotations

from company_profile.modules.sources.policy import (
    calculate_entity_match_score,
    classify_source_type,
    evaluate_source_policy,
)


def test_classify_source_type_and_authority_tiers() -> None:
    """Verify source classification and authority tier assignments."""
    stype, tier = classify_source_type(
        "dangkykinhdoanh.gov.vn", "https://dangkykinhdoanh.gov.vn/company/123"
    )
    assert stype == "registry"
    assert tier == 1

    stype, tier = classify_source_type("masothue.com", "https://masothue.com/0312345678")
    assert stype == "registry"
    assert tier == 2

    stype, tier = classify_source_type(
        "trangvangvietnam.com", "https://trangvangvietnam.com/listing"
    )
    assert stype == "directory"
    assert tier == 3

    stype, tier = classify_source_type("vnexpress.net", "https://vnexpress.net/article/123")
    assert stype == "news"
    assert tier == 4


def test_entity_match_score_calculation() -> None:
    """Verify entity match scoring calculation with tax ID and name overlap."""
    text_content = "Công ty TNHH AI Riser Việt Nam có mã số thuế 0312345678 tại TP.HCM."

    # Tax ID match + name match -> 1.0
    score = calculate_entity_match_score(
        "Công ty TNHH AI Riser Việt Nam", "0312345678", text_content
    )
    assert score >= 0.8

    # Only partial name match, no tax ID -> < 0.5
    score_partial = calculate_entity_match_score(
        "Công ty TNHH AI Riser Việt Nam", "9999999999", "Thông tin về công ty AI Riser"
    )
    assert 0.0 < score_partial <= 0.5

    # Completely irrelevant text -> 0.0
    score_none = calculate_entity_match_score(
        "Công ty TNHH AI Riser Việt Nam", "0312345678", "Hôm nay thời tiết rất đẹp."
    )
    assert score_none == 0.0


def test_evaluate_source_policy_rules() -> None:
    """Verify source policy decision rules and reason descriptions."""
    # Blocked domain
    status, reason = evaluate_source_policy("web_page", 3, 0.9, domain_blocked=True)
    assert status == "rejected"
    assert "BLOCKED_DOMAIN" in reason

    # Low match score
    status, reason = evaluate_source_policy("web_page", 3, 0.1, domain_blocked=False)
    assert status == "rejected"
    assert "LOW_MATCH_SCORE" in reason

    # Accepted source
    status, reason = evaluate_source_policy("registry", 1, 0.95, domain_blocked=False)
    assert status == "fetched"
    assert "ACCEPTED" in reason
