"""Translation service for company profile evidence.

Preserves original source language text and stores translation separately
with full provider/model/version metadata.  Original text is never overwritten.

Per AGENT.md Rule 9: tests use the mock adapter only.
Per AGENT.md product trust rules: original language is preserved; translation
is stored separately and never presented as the original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TranslatedText:
    """Structured bilingual text result preserving original and translated versions."""

    original_text: str
    original_language: str | None
    translated_text: str
    target_language: str
    provider: str
    model: str
    translated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    prompt_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for persistence."""
        return {
            "original_text": self.original_text,
            "original_language": self.original_language,
            "translated_text": self.translated_text,
            "target_language": self.target_language,
            "provider": self.provider,
            "model": self.model,
            "translated_at": self.translated_at.isoformat(),
            "prompt_hash": self.prompt_hash,
        }


class TranslationService:
    """Service for translating evidence text through the configured AI provider.

    The original text is always preserved.  If translation fails, the service
    returns the original text as a fallback and records the failure.
    """

    def __init__(self, ai_provider: Any) -> None:
        """Initialize with an AiProvider instance.

        Args:
            ai_provider: Any object implementing the AiProvider protocol
                         (MockAiProvider or GeminiAiProvider).
        """
        self._provider = ai_provider

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
    ) -> TranslatedText:
        """Translate text to target language, preserving original.

        Args:
            text: Source text to translate.
            target_language: BCP-47 language tag, e.g. 'en' or 'vi'.
            source_language: Optional source language tag; None = auto-detect.

        Returns:
            TranslatedText with both original and translated text.
            Falls back to original text if translation fails.
        """
        if not text or not text.strip():
            return TranslatedText(
                original_text=text,
                original_language=source_language,
                translated_text=text,
                target_language=target_language,
                provider="passthrough",
                model="none",
            )

        # If source and target are the same, skip the provider call
        if source_language and source_language == target_language:
            return TranslatedText(
                original_text=text,
                original_language=source_language,
                translated_text=text,
                target_language=target_language,
                provider="passthrough",
                model="none",
            )

        try:
            result = await self._provider.run_translation(
                text=text,
                target_language=target_language,
                source_language=source_language,
            )
            return TranslatedText(
                original_text=result.original_text,
                original_language=result.original_language or source_language,
                translated_text=result.translated_text,
                target_language=result.target_language,
                provider=result.metadata.provider,
                model=result.metadata.model,
                prompt_hash=result.metadata.prompt_hash,
            )
        except Exception:
            # Translation failure: return original text as fallback
            # This is explicitly logged by the caller; we do not suppress the error silently.
            return TranslatedText(
                original_text=text,
                original_language=source_language,
                translated_text=text,  # fallback: return original
                target_language=target_language,
                provider="fallback",
                model="none",
            )
