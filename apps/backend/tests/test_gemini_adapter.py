"""Deterministic tests for the async Google GenAI adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from company_profile.integrations.ai.gemini_adapter import (
    GeminiAiProvider,
    GeminiProviderError,
)
from company_profile.integrations.ai.protocol import AiInputBlock


class FakeModels:
    """Small async SDK surface used without network or credentials."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeProviderResponseError(Exception):
    """SDK-shaped error double exposing only the safe HTTP-like code."""

    def __init__(self, code: int) -> None:
        super().__init__("provider response omitted from application diagnostics")
        self.code = code


def fake_client(responses: list[Any]) -> tuple[Any, FakeModels]:
    models = FakeModels(responses)
    return SimpleNamespace(aio=SimpleNamespace(models=models)), models


@pytest.mark.asyncio
async def test_gemini_adapter_uses_async_json_request_and_records_usage() -> None:
    response = SimpleNamespace(
        text='{"facts": [], "unknown_fields": ["identity.tax_id"]}',
        usage_metadata=SimpleNamespace(prompt_token_count=20, candidates_token_count=5),
    )
    client, models = fake_client([response])
    provider = GeminiAiProvider("test-key", client=client)

    result = await provider.run_extraction(
        "extract_identity",
        [AiInputBlock(block_id="block-1", text_content="VNPT public evidence")],
        "VNPT",
    )

    assert result.raw_output["unknown_fields"] == ["identity.tax_id"]
    assert result.metadata.provider == "gemini"
    assert result.metadata.input_token_count == 20
    assert models.calls[0]["model"] == "gemini-2.0-flash"
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_gemini_adapter_retries_then_returns_typed_provider_failure() -> None:
    client, models = fake_client([OSError("first"), OSError("second")])
    provider = GeminiAiProvider("test-key", max_retries=2, client=client)

    with pytest.raises(GeminiProviderError, match="bounded retries") as error_info:
        await provider.run_extraction(
            "extract_identity",
            [AiInputBlock(block_id="block-1", text_content="Evidence")],
            "VNPT",
        )

    assert len(models.calls) == 2
    assert error_info.value.reason_code == "AI_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_gemini_adapter_reports_quota_and_does_not_retry_rejected_request() -> None:
    client, models = fake_client([FakeProviderResponseError(429)])
    provider = GeminiAiProvider("test-key", max_retries=3, client=client)

    with pytest.raises(GeminiProviderError) as error_info:
        await provider.run_extraction(
            "extract_identity",
            [AiInputBlock(block_id="block-1", text_content="Evidence")],
            "VNPT",
        )

    assert error_info.value.reason_code == "AI_QUOTA_EXCEEDED"
    assert len(models.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_reason"),
    [
        (401, "AI_AUTHENTICATION_FAILED"),
        (403, "AI_AUTHENTICATION_FAILED"),
        (404, "AI_MODEL_NOT_FOUND"),
        (400, "AI_REQUEST_REJECTED"),
    ],
)
async def test_gemini_adapter_classifies_non_retryable_provider_responses(
    status_code: int, expected_reason: str
) -> None:
    client, models = fake_client([FakeProviderResponseError(status_code)])
    provider = GeminiAiProvider("test-key", max_retries=3, client=client)

    with pytest.raises(GeminiProviderError) as error_info:
        await provider.run_extraction(
            "extract_identity",
            [AiInputBlock(block_id="block-1", text_content="Evidence")],
            "VNPT",
        )

    assert error_info.value.reason_code == expected_reason
    assert len(models.calls) == 1


@pytest.mark.asyncio
async def test_gemini_adapter_rejects_invalid_json_without_fabricating_output() -> None:
    client, _models = fake_client([SimpleNamespace(text="not-json", usage_metadata=None)])
    provider = GeminiAiProvider("test-key", client=client)

    with pytest.raises(GeminiProviderError, match="invalid JSON") as error_info:
        await provider.run_extraction(
            "extract_identity",
            [AiInputBlock(block_id="block-1", text_content="Evidence")],
            "VNPT",
        )

    assert error_info.value.reason_code == "AI_OUTPUT_INVALID"
