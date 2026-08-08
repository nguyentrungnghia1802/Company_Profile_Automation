"""AI extraction service orchestrating provider calls, validation, and audit recording.

Architecture boundaries:
- This service is the only place that calls AiProvider.run_extraction.
- It enforces per-job budget limits before every call.
- It enforces the kill switch (ai_kill_switch_enabled).
- It validates every extraction result before returning it.
- It persists an AiRun audit record for every call.
- It never exposes raw provider credentials or raw model payloads externally.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from company_profile.modules.ai.schemas import get_schema_for_operation
from company_profile.modules.ai.translation import TranslatedText, TranslationService
from company_profile.modules.ai.validation import ValidationOutcome, validate_extraction_result

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from company_profile.integrations.ai.protocol import AiInputBlock, AiProvider

log = structlog.get_logger(__name__)

MAX_SINGLE_CALL_ESTIMATE = 0.10


class AiBudgetExceededError(Exception):
    """Raised when the per-job AI cost budget would be exceeded."""


class AiKillSwitchError(Exception):
    """Raised when the AI kill switch is active and no calls are permitted."""


class AiExtractionService:
    """Orchestrates structured AI extraction with budget, kill-switch, validation, and audit.

    Usage:
        service = AiExtractionService(provider=mock_or_gemini, settings=settings)
        result = await service.extract(
            session=db_session,
            operation="extract_identity",
            blocks=[AiInputBlock(...)],
            company_name="Acme Ltd.",
            workspace_id=workspace_id,
            company_id=company_id,
            valid_block_ids={"blk_001", "blk_002"},
        )
    """

    def __init__(
        self,
        provider: AiProvider,
        ai_budget_usd_per_job: float = 1.0,
        ai_kill_switch_enabled: bool = False,
    ) -> None:
        self._provider = provider
        self._budget_usd_per_job = ai_budget_usd_per_job
        self._kill_switch = ai_kill_switch_enabled
        self._translation_service = TranslationService(provider)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    async def extract(
        self,
        session: AsyncSession,
        operation: str,
        blocks: list[AiInputBlock],
        company_name: str,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID | None,
        valid_block_ids: set[str],
        research_job_id: uuid.UUID | None = None,
        job_cost_so_far_usd: float = 0.0,
        **kwargs: Any,
    ) -> tuple[ValidationOutcome, float]:
        """Run an extraction operation and return the validated result + actual cost.

        Args:
            session: Database session for persisting AiRun audit records.
            operation: Extraction operation name (e.g. 'extract_identity').
            blocks: Document blocks to use as evidence.
            company_name: Target company name for entity match.
            workspace_id: Workspace scope for audit records.
            company_id: Company scope for audit records (nullable).
            valid_block_ids: Set of valid DocumentBlock.block_key values.
            research_job_id: Optional research job for budget tracking.
            job_cost_so_far_usd: Total AI spend in this job so far.
            **kwargs: Additional provider arguments.

        Returns:
            Tuple of (ValidationOutcome, actual_cost_usd_this_call).

        Raises:
            AiKillSwitchError: If kill switch is active.
            AiBudgetExceededError: If job budget would be exceeded.
            ValueError: If operation is not recognized.
        """
        # Guard: kill switch
        if self._kill_switch:
            raise AiKillSwitchError(
                "AI kill switch is enabled. All AI extraction calls are currently blocked."
            )

        # Guard: schema must exist before spending budget
        get_schema_for_operation(operation)  # raises ValueError if unknown

        # Guard: pre-check budget (conservative: assume max single-call cost = $0.10)
        if job_cost_so_far_usd + MAX_SINGLE_CALL_ESTIMATE > self._budget_usd_per_job:
            raise AiBudgetExceededError(
                f"AI budget exceeded: job has spent ${job_cost_so_far_usd:.4f}; "
                f"budget is ${self._budget_usd_per_job:.2f}."
            )

        # Execute provider call
        run_result = await self._provider.run_extraction(
            operation=operation,
            blocks=blocks,
            company_name=company_name,
            **kwargs,
        )

        actual_cost = run_result.metadata.estimated_cost_usd or 0.0

        # Validate
        outcome = validate_extraction_result(
            run_result=run_result,
            valid_block_ids=valid_block_ids,
            company_name=company_name,
        )

        # Determine final validation_outcome for audit
        audit_validation_outcome = "passed" if outcome.is_valid else "failed"

        # Persist AiRun audit record
        await self._persist_ai_run(
            session=session,
            workspace_id=workspace_id,
            company_id=company_id,
            research_job_id=research_job_id,
            run_result=run_result,
            validation_outcome=audit_validation_outcome,
        )

        log.info(
            "ai.extraction.complete",
            operation=operation,
            provider=run_result.metadata.provider,
            model=run_result.metadata.model,
            validation_outcome=audit_validation_outcome,
            cost_usd=actual_cost,
            errors=outcome.errors,
        )

        return outcome, actual_cost

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
    ) -> TranslatedText:
        """Translate evidence text preserving original.

        Args:
            text: Source text.
            target_language: BCP-47 tag (e.g. 'en', 'vi').
            source_language: Optional source language; None = auto-detect.

        Returns:
            TranslatedText with both original and translated text.
        """
        if self._kill_switch:
            raise AiKillSwitchError(
                "AI kill switch is enabled. All AI translation calls are currently blocked."
            )
        return await self._translation_service.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
        )

    # ------------------------------------------------------------------
    # Internal audit persistence
    # ------------------------------------------------------------------

    async def _persist_ai_run(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID | None,
        research_job_id: uuid.UUID | None,
        run_result: Any,
        validation_outcome: str,
    ) -> None:
        """Persist an AiRun audit record to the database."""
        from company_profile.db.models.ai import AiRun

        meta = run_result.metadata
        ai_run = AiRun(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            company_id=company_id,
            research_job_id=research_job_id,
            provider=meta.provider,
            model=meta.model,
            operation=meta.operation,
            prompt_hash=meta.prompt_hash,
            input_token_count=meta.input_token_count,
            output_token_count=meta.output_token_count,
            estimated_cost_usd=meta.estimated_cost_usd,
            latency_ms=meta.latency_ms,
            validation_outcome=validation_outcome,
            created_at=datetime.now(UTC),
        )
        session.add(ai_run)
        await session.flush()
