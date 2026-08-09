"""Regression tests for verified standard and compatibility TLS transport."""

from __future__ import annotations

import ssl
from typing import Any, ClassVar

import httpx
import pytest

from company_profile.integrations.fetch.http_transport import (
    SecureHttpTransport,
    TransportFailure,
    TransportFailureCode,
    TransportResponse,
    build_legacy_tls_context,
)


class _RecordingClient:
    """Small AsyncClient double that records verification contexts."""

    outcomes: ClassVar[list[object]] = []
    verifies: ClassVar[list[object]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.verifies.append(kwargs["verify"])

    async def __aenter__(self) -> _RecordingClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def get(self, _url: str, **_kwargs: Any) -> httpx.Response:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, httpx.Response)
        return outcome


@pytest.fixture(autouse=True)
def _safe_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "company_profile.integrations.fetch.http_transport.validate_url_safety",
        lambda _url: (True, "SAFE"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", _RecordingClient)
    _RecordingClient.outcomes = []
    _RecordingClient.verifies = []


def _response(url: str = "https://public.example/") -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("GET", url), content=b"ok")


@pytest.mark.anyio
async def test_standard_tls_is_always_attempted_first() -> None:
    _RecordingClient.outcomes = [_response()]

    result = await SecureHttpTransport(timeout=5).get("https://public.example/")

    assert isinstance(result, TransportResponse)
    assert result.tls_mode == "standard"
    assert _RecordingClient.verifies == [True]


@pytest.mark.anyio
async def test_compatible_legacy_context_is_used_only_after_dh_failure() -> None:
    request = httpx.Request("GET", "https://legacy.example/")
    _RecordingClient.outcomes = [
        httpx.ConnectError("[SSL: DH_KEY_TOO_SMALL] dh key too small", request=request),
        _response("https://legacy.example/"),
    ]

    result = await SecureHttpTransport(
        timeout=5,
        legacy_tls_fallback_enabled=True,
        legacy_tls_security_level=1,
    ).get("https://legacy.example/")

    assert isinstance(result, TransportResponse)
    assert result.tls_mode == "legacy"
    assert _RecordingClient.verifies[0] is True
    context = _RecordingClient.verifies[1]
    assert isinstance(context, ssl.SSLContext)
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.anyio
async def test_legacy_fallback_disabled_returns_typed_compatibility_failure() -> None:
    request = httpx.Request("GET", "https://legacy.example/")
    _RecordingClient.outcomes = [
        httpx.ConnectError("[SSL: DH_KEY_TOO_SMALL] dh key too small", request=request)
    ]

    result = await SecureHttpTransport(timeout=5).get("https://legacy.example/")

    assert isinstance(result, TransportFailure)
    assert result.code == TransportFailureCode.TLS_COMPATIBILITY
    assert result.message.endswith("LEGACY_FALLBACK_DISABLED")
    assert _RecordingClient.verifies == [True]


@pytest.mark.anyio
async def test_certificate_failure_never_triggers_legacy_fallback() -> None:
    request = httpx.Request("GET", "https://bad-cert.example/")
    _RecordingClient.outcomes = [
        httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] invalid certificate", request=request)
    ]

    result = await SecureHttpTransport(
        timeout=5,
        legacy_tls_fallback_enabled=True,
    ).get("https://bad-cert.example/")

    assert isinstance(result, TransportFailure)
    assert result.code == TransportFailureCode.TLS_CERTIFICATE
    assert _RecordingClient.verifies == [True]


@pytest.mark.anyio
async def test_generic_tls_failure_is_typed_without_downgrade() -> None:
    request = httpx.Request("GET", "https://broken-tls.example/")
    _RecordingClient.outcomes = [
        httpx.ConnectError("[SSL: WRONG_VERSION_NUMBER] wrong version", request=request)
    ]

    result = await SecureHttpTransport(
        timeout=5,
        legacy_tls_fallback_enabled=True,
    ).get("https://broken-tls.example/")

    assert isinstance(result, TransportFailure)
    assert result.code == TransportFailureCode.TLS_HANDSHAKE
    assert _RecordingClient.verifies == [True]


def test_legacy_context_rejects_unsafe_security_levels() -> None:
    with pytest.raises(ValueError, match="security level"):
        build_legacy_tls_context(0)


@pytest.mark.anyio
async def test_transport_enforces_response_size_in_both_tls_modes() -> None:
    _RecordingClient.outcomes = [
        httpx.Response(
            200,
            request=httpx.Request("GET", "https://large.example/"),
            content=b"too large",
        )
    ]

    result = await SecureHttpTransport(timeout=5, max_response_bytes=3).get(
        "https://large.example/"
    )

    assert isinstance(result, TransportFailure)
    assert result.code == TransportFailureCode.RESPONSE_TOO_LARGE
