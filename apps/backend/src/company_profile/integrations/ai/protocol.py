"""Provider-neutral AI operation protocol and typed input/output schemas.

All AI operations must go through this interface.  Credentials are never
exposed outside the backend; no external caller can select provider, model,
or invoke tools directly.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared input schema
# ---------------------------------------------------------------------------


class AiInputBlock(BaseModel):
    """A document block passed as evidence context to an AI operation."""

    block_id: str = Field(..., description="Stable block key from DocumentBlock.block_key")
    block_type: str = Field(default="paragraph")
    text_content: str = Field(..., description="Plain text content of the block")
    source_url: str | None = Field(default=None)
    language: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# Run result schemas
# ---------------------------------------------------------------------------


class AiRunMetadata(BaseModel):
    """Provider telemetry recorded after every AI call."""

    provider: str
    model: str
    operation: str
    prompt_hash: str | None = None
    input_token_count: int | None = None
    output_token_count: int | None = None
    estimated_cost_usd: float | None = None
    latency_ms: int | None = None


class AiRunResult(BaseModel):
    """Raw structured output from an extraction AI call."""

    operation: str
    raw_output: dict[str, Any]
    metadata: AiRunMetadata
    validation_outcome: str = "passed"  # passed | failed | skipped
    validation_errors: list[str] = Field(default_factory=list)


class AiTranslationResult(BaseModel):
    """Structured result from a translation AI call."""

    original_text: str
    original_language: str | None = None
    translated_text: str
    target_language: str
    metadata: AiRunMetadata


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AiProvider(Protocol):
    """Protocol for AI provider adapters used in extraction and translation.

    All implementations must:
    - Accept only AiInputBlock lists as document context.
    - Return fully typed AiRunResult / AiTranslationResult.
    - Never read provider credentials from caller arguments.
    - Record provider, model, operation, token, cost, and latency.
    - Provide deterministic mock behavior for tests.
    """

    async def run_extraction(
        self,
        operation: str,
        blocks: list[AiInputBlock],
        company_name: str,
        **kwargs: Any,
    ) -> AiRunResult:
        """Run a structured extraction operation against document blocks.

        Args:
            operation: One of extract_identity, extract_overview, extract_products,
                       extract_size, extract_markets, extract_leadership, extract_innovation.
            blocks: Document blocks to use as evidence context.
            company_name: Target company name for entity match validation.
            **kwargs: Provider-specific parameters (e.g. locale, temperature).

        Returns:
            AiRunResult with raw_output, metadata, and validation_outcome.
        """
        ...

    async def run_translation(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
        **kwargs: Any,
    ) -> AiTranslationResult:
        """Translate text preserving original language.

        Args:
            text: Source text to translate.
            target_language: BCP-47 language tag (e.g. 'en', 'vi').
            source_language: Optional source language tag; None means auto-detect.
            **kwargs: Provider-specific parameters.

        Returns:
            AiTranslationResult with both original and translated text.
        """
        ...
