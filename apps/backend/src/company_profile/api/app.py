"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from company_profile.api.errors import register_error_handlers
from company_profile.api.routers import health
from company_profile.config.settings import get_settings
from company_profile.operations.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown."""
    settings = get_settings()
    setup_logging(settings.log_level)
    # Startup: initialize DB pool, providers, etc.
    yield
    # Shutdown: close DB pool, flush metrics, etc.


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Verified Company Profile API",
        version="0.1.0",
        docs_url="/api/v1/docs" if settings.environment != "production" else None,
        redoc_url="/api/v1/redoc" if settings.environment != "production" else None,
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    register_error_handlers(app)

    # Routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    return app
