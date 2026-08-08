"""Deterministic Mock AiProvider implementation for testing and local development.

All outputs are schema-validated, evidence-grounded, and deterministic.
No live network calls are made.  Token counts and costs are simulated at zero.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from company_profile.integrations.ai.protocol import (
    AiInputBlock,
    AiRunMetadata,
    AiRunResult,
    AiTranslationResult,
)

_PROVIDER = "mock"
_MODEL = "mock-v1"


def _make_metadata(operation: str, prompt: str, latency_ms: int = 0) -> AiRunMetadata:
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    return AiRunMetadata(
        provider=_PROVIDER,
        model=_MODEL,
        operation=operation,
        prompt_hash=prompt_hash,
        input_token_count=0,
        output_token_count=0,
        estimated_cost_usd=0.0,
        latency_ms=latency_ms,
    )


def _first_block_id(blocks: list[AiInputBlock]) -> str:
    return blocks[0].block_id if blocks else "blk_001"


class MockAiProvider:
    """Deterministic mock AI adapter.

    Returns stable, evidence-grounded structured output for all extraction
    operations.  The block IDs from the first input block are included in
    every non-unknown fact to satisfy evidence validation.
    """

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    async def run_extraction(
        self,
        operation: str,
        blocks: list[AiInputBlock],
        company_name: str,
        **_kwargs: Any,
    ) -> AiRunResult:
        """Return deterministic structured extraction output for the given operation."""
        start = time.monotonic()
        block_id = _first_block_id(blocks)
        raw_output = self._build_raw_output(operation, block_id, company_name)
        latency_ms = int((time.monotonic() - start) * 1000)
        prompt = f"{operation}:{company_name}:{block_id}"
        meta = _make_metadata(operation, prompt, latency_ms)
        return AiRunResult(
            operation=operation,
            raw_output=raw_output,
            metadata=meta,
            validation_outcome="passed",
            validation_errors=[],
        )

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    async def run_translation(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
        **_kwargs: Any,
    ) -> AiTranslationResult:
        """Return deterministic mock translation."""
        operation = "translate"
        prompt = f"{operation}:{target_language}:{text[:40]}"
        meta = _make_metadata(operation, prompt, latency_ms=0)
        translated = f"[{target_language.upper()}] {text}"
        return AiTranslationResult(
            original_text=text,
            original_language=source_language or "vi",
            translated_text=translated,
            target_language=target_language,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_raw_output(self, operation: str, block_id: str, company_name: str) -> dict[str, Any]:
        """Build schema-compatible raw output for the given operation."""
        builders: dict[str, Callable[[str, str], dict[str, Any]]] = {
            "extract_identity": self._identity,
            "extract_overview": self._overview,
            "extract_products": self._products,
            "extract_size": self._size,
            "extract_markets": self._markets,
            "extract_leadership": self._leadership,
            "extract_innovation": self._innovation,
        }
        builder = builders.get(operation)
        if builder is None:
            return {"facts": [], "unknown_fields": [operation]}
        return builder(block_id, company_name)

    # ---- per-operation mock payloads ----

    def _identity(self, block_id: str, company_name: str) -> dict[str, Any]:
        return {
            "facts": [
                {
                    "field_key": "identity.legal_name",
                    "value": company_name,
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.95,
                    "is_inferred": False,
                    "is_unknown": False,
                },
                {
                    "field_key": "identity.country",
                    "value": "VN",
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.80,
                    "is_inferred": False,
                    "is_unknown": False,
                },
            ],
            "unknown_fields": ["identity.tax_id", "identity.founding_year"],
        }

    def _overview(self, block_id: str, company_name: str) -> dict[str, Any]:
        return {
            "facts": [
                {
                    "field_key": "overview.description",
                    "value": f"{company_name} is a Vietnamese technology company.",
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.70,
                    "is_inferred": True,
                    "is_unknown": False,
                },
            ],
            "unknown_fields": ["overview.industry"],
        }

    def _products(self, block_id: str, _company_name: str) -> dict[str, Any]:
        return {
            "facts": [
                {
                    "field_key": "products.list",
                    "value": [
                        {
                            "name": "Core Platform",
                            "category": "software",
                            "description": "Enterprise SaaS platform",
                        }
                    ],
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.75,
                    "is_inferred": False,
                    "is_unknown": False,
                },
            ],
            "unknown_fields": [],
        }

    def _size(self, block_id: str, _company_name: str) -> dict[str, Any]:
        return {
            "facts": [
                {
                    "field_key": "size.employee_count_range",
                    "value": "50-200",
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.60,
                    "is_inferred": True,
                    "is_unknown": False,
                },
            ],
            "unknown_fields": ["size.revenue_range"],
        }

    def _markets(self, block_id: str, _company_name: str) -> dict[str, Any]:
        return {
            "facts": [
                {
                    "field_key": "markets.target_markets",
                    "value": ["Vietnam", "Southeast Asia"],
                    "evidence_block_ids": [block_id],
                    "confidence_hint": 0.72,
                    "is_inferred": False,
                    "is_unknown": False,
                },
            ],
            "unknown_fields": ["markets.key_partners"],
        }

    def _leadership(self, _block_id: str, _company_name: str) -> dict[str, Any]:
        return {
            "facts": [],
            "unknown_fields": ["leadership.ceo", "leadership.founders"],
        }

    def _innovation(self, _block_id: str, _company_name: str) -> dict[str, Any]:
        return {
            "facts": [],
            "unknown_fields": [
                "innovation.awards",
                "innovation.certifications",
                "innovation.funding_rounds",
            ],
        }
