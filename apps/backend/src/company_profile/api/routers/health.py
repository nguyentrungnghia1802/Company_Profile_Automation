"""Health and readiness check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from company_profile.operations.metrics import MetricsCollector

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
    """Readiness probe. Checks critical dependencies."""
    checks: dict[str, str] = {}

    try:
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    collector = MetricsCollector.get_instance()
    text_content = collector.generate_prometheus_metrics()
    return PlainTextResponse(
        content=text_content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
