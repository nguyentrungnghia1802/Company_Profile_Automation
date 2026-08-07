# Verified Company Profile System — root command facade
# All documented developer commands should be stable.
# Underlying tools may change; update docs and CI together.

.PHONY: help dev stop clean format format-check lint typecheck \
        test test-unit test-integration test-security test-contract \
        test-frontend test-e2e test-docs build \
        db-up db-migrate db-status db-fixtures openapi

SHELL := /bin/bash

# --- Development lifecycle ---

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start the full local stack (Docker Compose)
	docker compose up --build

stop: ## Stop the local stack
	docker compose down

clean: ## Stop and remove all local data (volumes)
	docker compose down -v

# --- Code quality ---

format: ## Auto-format Python and TypeScript
	uv run ruff format apps/backend/src apps/backend/tests
	@echo "TypeScript formatting requires pnpm — run inside web container or install Node.js locally"

format-check: ## Check formatting without changes
	uv run ruff format --check apps/backend/src apps/backend/tests

lint: ## Lint Python code
	uv run ruff check apps/backend/src apps/backend/tests

typecheck: ## Type-check Python code
	uv run mypy apps/backend/src

# --- Testing ---

test: test-unit ## Run default test suite (unit)

test-unit: ## Run unit tests
	uv run pytest apps/backend/tests -m "not integration and not security and not e2e" -v

test-integration: ## Run integration tests (requires database)
	uv run pytest apps/backend/tests -m "integration" -v

test-security: ## Run security-focused tests
	uv run pytest apps/backend/tests -m "security" -v

test-contract: ## Run API contract tests
	@echo "Contract tests will be available after OpenAPI generation (P0-017)"

test-frontend: ## Run frontend tests
	@echo "Frontend tests will be available after test runner setup (P0-013)"

test-e2e: ## Run end-to-end browser tests
	@echo "E2E tests will be available after Playwright setup (P0-013)"

test-docs: ## Run documentation drift checks
	@echo "Doc checks will be available after sync script (P0-029)"

# --- Build ---

build: ## Build Docker images
	docker compose build

# --- Database ---

db-up: ## Start PostgreSQL only
	docker compose up -d postgres

db-migrate: ## Run Alembic migrations
	@echo "Migrations will be available after Alembic setup (P0-022)"

db-status: ## Show current migration status
	@echo "Migration status will be available after Alembic setup (P0-022)"

db-fixtures: ## Load development fixtures
	@echo "Fixtures will be available after fixture setup (P0-023)"

# --- API ---

openapi: ## Generate OpenAPI schema and TypeScript client
	@echo "OpenAPI generation will be available after setup (P0-017)"
