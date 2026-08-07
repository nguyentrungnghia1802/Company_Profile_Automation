# Verified Company Profile System — Backend (API + Worker)
# Multi-stage build for Python 3.12 with uv

# === Builder stage ===
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Copy source code
COPY apps/backend/src/ apps/backend/src/

# Install the project itself
RUN uv sync --no-dev

# === Runtime stage ===
FROM python:3.12-slim AS runtime

# Security: run as non-root
RUN groupadd --gid 1001 vcps && \
    useradd --uid 1001 --gid vcps --shell /bin/bash --create-home vcps

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY apps/backend/src/ apps/backend/src/

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/backend/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Create local storage directory
RUN mkdir -p /app/data/storage && chown -R vcps:vcps /app/data

USER vcps

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()" || exit 1

# Default: API server
EXPOSE 8000
CMD ["uvicorn", "company_profile.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
