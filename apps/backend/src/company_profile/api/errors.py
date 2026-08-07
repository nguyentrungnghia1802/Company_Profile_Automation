"""Global error handling and standard error envelope."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI, Request


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
    async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        # Log the actual exception via structured logging in production.
        # Never expose stack traces or internal details.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                    "retryable": False,
                }
            },
        )
