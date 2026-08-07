"""Health and readiness check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Liveness check response."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response with dependency status."""

    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe. Returns 200 if the process is running."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe. Checks critical dependencies.

    Currently checks:
    - database: placeholder until DB session is configured in P0-021
    """
    checks: dict[str, str] = {}

    # Database check — placeholder until real session is available
    try:
        # TODO(P0-021): Replace with actual async DB ping
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)
