"""Global error handling and standard error envelope."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi.responses import JSONResponse

from company_profile.api.middleware.correlation import CORRELATION_ID_HEADER

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with stable code and HTTP mapping."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, code: str = "NOT_FOUND", message: str = "Resource not found") -> None:
        super().__init__(code=code, message=message, status_code=404)


class ForbiddenError(AppError):
    """Authorization denied."""

    def __init__(self, code: str = "FORBIDDEN", message: str = "Access denied") -> None:
        super().__init__(code=code, message=message, status_code=403)


class ConflictError(AppError):
    """State or version conflict."""

    def __init__(
        self,
        code: str = "CONFLICT",
        message: str = "Conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=409, details=details)


class ValidationError(AppError):
    """Validation or bad request error."""

    def __init__(
        self,
        code: str = "VALIDATION_ERROR",
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=400, details=details)


def _error_response(error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unavailable")
        logger.exception(
            "Unhandled API exception",
            extra={
                "error_code": "INTERNAL_ERROR",
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            headers={CORRELATION_ID_HEADER: correlation_id},
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected server error occurred. Use the correlation ID to "
                        "inspect the API logs."
                    ),
                    "details": {
                        "correlation_id": correlation_id,
                        "operation": f"{request.method} {request.url.path}",
                        "next_step": (
                            "Retry once. If the error persists, search the backend logs for "
                            "this correlation ID."
                        ),
                    },
                    "retryable": True,
                }
            },
        )
