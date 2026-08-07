"""Deterministic Mock AiProvider implementation."""

from __future__ import annotations

from typing import Any


class MockAiProvider:
    """Mock AI adapter returning structured, evidence-grounded candidate responses."""

    async def extract_facts(
        self, document_blocks: list[dict[str, Any]], **_kwargs: Any
    ) -> dict[str, Any]:
        """Return deterministic extracted company facts."""
        block_id = document_blocks[0].get("block_id", "blk_001") if document_blocks else "blk_001"
        return {
            "facts": [
                {
                    "field_key": "company.legal_name",
                    "value": "Example Company LLC",
                    "evidence_block_id": block_id,
                    "confidence_score": 0.95,
                    "is_inferred": False,
                }
            ],
            "unknown_fields": [],
        }

    async def translate_text(self, text: str, target_language: str = "en", **_kwargs: Any) -> str:
        """Return deterministic translation."""
        return f"[Translated to {target_language}]: {text}"
