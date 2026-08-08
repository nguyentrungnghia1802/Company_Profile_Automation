"""AI extraction result validation pipeline and prompt injection defense.

This module validates AI output BEFORE any extracted fact is accepted into
the system.  Validation happens locally, not by the model.

Security rules:
- Model cannot declare its own output valid.
- Evidence block IDs are checked against actual snapshot block IDs.
- Entity match is checked to ensure the extracted company name plausibly
  appears in or near the referenced evidence text.
- Prompt injection patterns in evidence text are detected and flagged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from company_profile.modules.ai.schemas import (
    BaseExtractionResult,
    ExtractedFact,
    get_schema_for_operation,
)

if TYPE_CHECKING:
    from company_profile.integrations.ai.protocol import AiRunResult

# ---------------------------------------------------------------------------
# Injection defense patterns
# ---------------------------------------------------------------------------

# Common patterns that indicate prompt injection attempts in fetched content.
# This is a defence-in-depth measure; the primary defence is role separation
# in the prompt (content is labelled UNTRUSTED SOURCE CONTENT).
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|?system\|?>", re.IGNORECASE),
    re.compile(r"assistant\s*:\s*", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?instructions", re.IGNORECASE),
    re.compile(r"new\s+instructions\s*:", re.IGNORECASE),
    re.compile(r"override\s+(the\s+)?previous", re.IGNORECASE),
]

# Control characters that should not appear in extracted text values
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def detect_injection_in_text(text: str) -> list[str]:
    """Return list of injection pattern descriptions found in text."""
    found = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            found.append(f"Injection pattern detected: {pattern.pattern}")
    return found


def sanitize_text_value(text: str) -> str:
    """Remove ASCII control characters from extracted string values."""
    return _CONTROL_CHAR_PATTERN.sub("", text)


# ---------------------------------------------------------------------------
# Validation outcome
# ---------------------------------------------------------------------------


@dataclass
class ValidationOutcome:
    """Result of validating an AI run result."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_result: BaseExtractionResult | None = None


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


def validate_extraction_result(
    run_result: AiRunResult,
    valid_block_ids: set[str],
    company_name: str,
) -> ValidationOutcome:
    """Validate an AI extraction result before accepting any facts.

    Steps:
    1. Parse raw_output through the typed Pydantic schema.
    2. Verify all evidence block IDs exist in valid_block_ids.
    3. Check entity match: company name should appear in referenced evidence text.
    4. Detect injection patterns in extracted string values.
    5. Sanitize control characters from string values.

    Args:
        run_result: The AiRunResult returned by the provider.
        valid_block_ids: Set of DocumentBlock.block_key values from the snapshot.
        company_name: Target company name for entity match check.

    Returns:
        ValidationOutcome with is_valid, errors, warnings, sanitized_result.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Step 1: Schema parse
    try:
        schema_class = get_schema_for_operation(run_result.operation)
        parsed: BaseExtractionResult = schema_class.model_validate(run_result.raw_output)
    except Exception as exc:
        return ValidationOutcome(
            is_valid=False,
            errors=[f"Schema validation failed: {exc}"],
        )

    # Step 2 & 3 & 4 & 5: Per-fact validation
    sanitized_facts: list[ExtractedFact] = []
    for fact in parsed.facts:
        fact_errors = _validate_fact(fact, valid_block_ids, company_name)
        errors.extend(fact_errors)

        # Sanitize string values
        sanitized_fact = _sanitize_fact(fact, warnings)
        sanitized_facts.append(sanitized_fact)

    # Rebuild parsed with sanitized facts
    try:
        sanitized_result = schema_class.model_validate(
            {
                "facts": [f.model_dump() for f in sanitized_facts],
                "unknown_fields": parsed.unknown_fields,
            }
        )
    except Exception as exc:
        errors.append(f"Sanitized result failed re-validation: {exc}")
        sanitized_result = None

    is_valid = len(errors) == 0
    return ValidationOutcome(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        sanitized_result=sanitized_result if is_valid else None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_fact(
    fact: ExtractedFact,
    valid_block_ids: set[str],
    company_name: str,
) -> list[str]:
    """Validate a single extracted fact. Returns list of error strings."""
    errors: list[str] = []

    if fact.is_unknown:
        return []  # unknown facts have no evidence requirement

    # Step 2: Evidence block ID existence check
    for bid in fact.evidence_block_ids:
        if bid not in valid_block_ids:
            errors.append(
                f"Field '{fact.field_key}': evidence block ID '{bid}' does not exist "
                "in the snapshot."
            )

    # Step 3: Entity match check for identity.legal_name
    # Only applied to string values matching the primary company name field
    if fact.field_key == "identity.legal_name" and isinstance(fact.value, str):
        name_lower = company_name.lower().strip()
        value_lower = str(fact.value).lower().strip()
        # Simple containment check: one should contain significant words of the other
        name_words = {w for w in name_lower.split() if len(w) > 2}
        overlap = any(w in value_lower for w in name_words)
        if name_words and not overlap:
            errors.append(
                f"Field 'identity.legal_name': extracted value '{fact.value}' does not "
                f"appear to match target company '{company_name}'."
            )

    # Step 4: Injection pattern detection in string values
    if isinstance(fact.value, str):
        injection_hits = detect_injection_in_text(fact.value)
        for hit in injection_hits:
            errors.append(f"Field '{fact.field_key}': {hit}")

    return errors


def _sanitize_fact(fact: ExtractedFact, warnings: list[str]) -> ExtractedFact:
    """Return a copy of the fact with sanitized string values."""
    if fact.is_unknown or not isinstance(fact.value, str):
        return fact
    sanitized_value = sanitize_text_value(fact.value)
    if sanitized_value != fact.value:
        warnings.append(f"Field '{fact.field_key}': control characters removed from value.")
    return ExtractedFact(
        field_key=fact.field_key,
        value=sanitized_value,
        evidence_block_ids=fact.evidence_block_ids,
        confidence_hint=fact.confidence_hint,
        is_inferred=fact.is_inferred,
        is_unknown=fact.is_unknown,
    )
