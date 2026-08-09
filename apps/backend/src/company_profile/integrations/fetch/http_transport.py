"""Verified HTTP transport with a narrowly scoped legacy TLS fallback."""

from __future__ import annotations

import asyncio
import ssl
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from company_profile.modules.sources.validator import validate_url_safety

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class TransportFailureCode(StrEnum):
    """Stable categories for failures before an HTTP response is available."""

    SSRF_BLOCKED = "ssrf_blocked"
    TIMEOUT = "timeout"
    CONNECT_ERROR = "connect_error"
    TLS_COMPATIBILITY = "tls_compatibility_failed"
    TLS_CERTIFICATE = "tls_certificate_failed"
    TLS_HANDSHAKE = "tls_handshake_failed"
    RESPONSE_TOO_LARGE = "size_exceeded"
    HTTP_CLIENT = "http_client_error"


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """One response returned without automatically following redirects."""

    status_code: int
    url: str
    headers: httpx.Headers
    content: bytes
    tls_mode: str = "standard"


@dataclass(frozen=True, slots=True)
class TransportFailure:
    """Sanitized transport failure safe for durable fetch metadata."""

    code: TransportFailureCode
    message: str
    retryable: bool = False
    tls_mode: str = "standard"


_TLS_COMPATIBILITY_MARKERS = (
    "DH_KEY_TOO_SMALL",
    "UNSAFE_LEGACY_RENEGOTIATION_DISABLED",
    "LEGACY_SIGALG_DISALLOWED_OR_UNSUPPORTED",
)
_TLS_CERTIFICATE_MARKERS = (
    "CERTIFICATE_VERIFY_FAILED",
    "CERTIFICATE_VERIFY",
    "HOSTNAME_MISMATCH",
    "IP_ADDRESS_MISMATCH",
    "UNKNOWN_CA",
)
_TLS_MARKERS = (
    "[SSL:",
    "SSLV3_ALERT",
    "TLSV1_ALERT",
    "WRONG_VERSION_NUMBER",
    "UNEXPECTED_EOF_WHILE_READING",
)


def build_legacy_tls_context(security_level: int) -> ssl.SSLContext:
    """Build an isolated verified context with a controlled OpenSSL security level."""
    if security_level not in {1, 2}:
        raise ValueError("Legacy TLS security level must be 1 or 2.")
    context = httpx.create_ssl_context(verify=True, trust_env=True)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.set_ciphers(f"DEFAULT:@SECLEVEL={security_level}")
    return context


def classify_transport_error(exc: httpx.HTTPError) -> TransportFailureCode:
    """Classify TLS compatibility separately from certificate and network failures."""
    if isinstance(exc, httpx.TimeoutException):
        return TransportFailureCode.TIMEOUT

    chain = _exception_chain(exc)
    message = " ".join(str(item).upper() for item in chain)
    if any(isinstance(item, ssl.SSLCertVerificationError) for item in chain) or any(
        marker in message for marker in _TLS_CERTIFICATE_MARKERS
    ):
        return TransportFailureCode.TLS_CERTIFICATE
    if any(marker in message for marker in _TLS_COMPATIBILITY_MARKERS):
        return TransportFailureCode.TLS_COMPATIBILITY
    if any(isinstance(item, ssl.SSLError) for item in chain) or any(
        marker in message for marker in _TLS_MARKERS
    ):
        return TransportFailureCode.TLS_HANDSHAKE
    if isinstance(exc, httpx.ConnectError):
        return TransportFailureCode.CONNECT_ERROR
    return TransportFailureCode.HTTP_CLIENT


class SecureHttpTransport:
    """Attempt standard TLS first, then an opt-in per-request compatibility context."""

    def __init__(
        self,
        *,
        timeout: float,
        legacy_tls_fallback_enabled: bool = False,
        legacy_tls_security_level: int = 1,
        max_response_bytes: int = 10_000_000,
        rate_limit_seconds: float = 0.0,
        max_concurrency_per_domain: int = 2,
    ) -> None:
        self.timeout = timeout
        self.legacy_tls_fallback_enabled = legacy_tls_fallback_enabled
        self.legacy_tls_security_level = legacy_tls_security_level
        self.max_response_bytes = max(1, max_response_bytes)
        self.rate_limit_seconds = max(0.0, rate_limit_seconds)
        self.max_concurrency_per_domain = max(1, max_concurrency_per_domain)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._last_request: dict[str, float] = {}
        self._rate_lock = asyncio.Lock()

    async def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> TransportResponse | TransportFailure:
        """GET one validated URL without following redirects."""
        safe, reason = validate_url_safety(url)
        if not safe:
            return TransportFailure(
                TransportFailureCode.SSRF_BLOCKED,
                f"SSRF_BLOCKED:{reason}",
            )

        try:
            response = await self._get_once(url, headers=headers, verify=True, tls_mode="standard")
        except httpx.HTTPError as exc:
            failure_code = classify_transport_error(exc)
        else:
            return self._bounded(response)

        if failure_code != TransportFailureCode.TLS_COMPATIBILITY:
            return self._failure(failure_code, tls_mode="standard")
        if not self.legacy_tls_fallback_enabled:
            return TransportFailure(
                failure_code,
                "TLS_COMPATIBILITY_ERROR:LEGACY_FALLBACK_DISABLED",
                tls_mode="standard",
            )

        # DNS/IP policy is deliberately re-evaluated before the second handshake.
        safe, reason = validate_url_safety(url)
        if not safe:
            return TransportFailure(
                TransportFailureCode.SSRF_BLOCKED,
                f"SSRF_BLOCKED:{reason}",
                tls_mode="legacy",
            )
        legacy_context = build_legacy_tls_context(self.legacy_tls_security_level)
        try:
            response = await self._get_once(
                url,
                headers=headers,
                verify=legacy_context,
                tls_mode="legacy",
            )
        except httpx.HTTPError as exc:
            legacy_code = classify_transport_error(exc)
            return self._failure(legacy_code, tls_mode="legacy")
        return self._bounded(response)

    async def _get_once(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        verify: bool | ssl.SSLContext,
        tls_mode: str,
    ) -> TransportResponse:
        async with (
            self._domain_lease(url),
            httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=False,
                verify=verify,
            ) as client,
        ):
            response = await client.get(url, headers=headers)
        return TransportResponse(
            status_code=response.status_code,
            url=str(response.url or url),
            headers=response.headers,
            content=response.content,
            tls_mode=tls_mode,
        )

    @staticmethod
    def _failure(code: TransportFailureCode, *, tls_mode: str) -> TransportFailure:
        messages = {
            TransportFailureCode.TIMEOUT: "HTTP_REQUEST_TIMEOUT",
            TransportFailureCode.CONNECT_ERROR: "CONNECT_ERROR",
            TransportFailureCode.TLS_COMPATIBILITY: "TLS_COMPATIBILITY_ERROR",
            TransportFailureCode.TLS_CERTIFICATE: "TLS_CERTIFICATE_VERIFICATION_FAILED",
            TransportFailureCode.TLS_HANDSHAKE: "TLS_HANDSHAKE_FAILED",
            TransportFailureCode.RESPONSE_TOO_LARGE: "RESPONSE_SIZE_LIMIT_EXCEEDED",
            TransportFailureCode.HTTP_CLIENT: "HTTP_CLIENT_ERROR",
            TransportFailureCode.SSRF_BLOCKED: "SSRF_BLOCKED",
        }
        retryable = code in {
            TransportFailureCode.TIMEOUT,
            TransportFailureCode.CONNECT_ERROR,
            TransportFailureCode.HTTP_CLIENT,
        }
        return TransportFailure(code, messages[code], retryable=retryable, tls_mode=tls_mode)

    def _bounded(self, response: TransportResponse) -> TransportResponse | TransportFailure:
        if len(response.content) > self.max_response_bytes:
            return self._failure(
                TransportFailureCode.RESPONSE_TOO_LARGE,
                tls_mode=response.tls_mode,
            )
        return response

    @asynccontextmanager
    async def _domain_lease(self, url: str) -> AsyncIterator[None]:
        """Bound per-domain concurrency and spacing for every network attempt."""
        domain = (urlparse(url).hostname or "unknown").lower()
        semaphore = self._semaphores.setdefault(
            domain, asyncio.Semaphore(self.max_concurrency_per_domain)
        )
        await semaphore.acquire()
        try:
            async with self._rate_lock:
                elapsed = time.monotonic() - self._last_request.get(domain, 0.0)
                wait_for = self.rate_limit_seconds - elapsed
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
                self._last_request[domain] = time.monotonic()
            yield
        finally:
            semaphore.release()


def _exception_chain(exc: BaseException) -> tuple[BaseException, ...]:
    """Return a bounded exception chain without exposing it outside classification."""
    chain: list[BaseException] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(chain) < 8:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return tuple(chain)
