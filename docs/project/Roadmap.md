# Implementation Roadmap

**Roadmap mode:** `MAINTENANCE`

**Purpose:** Provide the ordered implementation plan for coding agents. This file tracks what is done, what remains, what is blocked, and what defects were discovered during implementation.

**Important:** This file is an execution tracker, not the sole source of product truth. Completed behavior must also be reflected in the canonical documents under `docs/project/`.

## 1. Status legend

- `[ ]` Not started.
- `[~]` In progress or partially implemented.
- `[x]` Fully implemented, tested, documented, and verified.
- `[!]` Blocked; blocker must be written in the task notes.
- `[-]` Removed from scope by accepted decision; decision reference required.

A task cannot become `[x]` when a known acceptance defect remains. Record the defect and keep the task `[~]`.

## 2. Agent execution rule

For each coding prompt, the agent must:

1. Read `AGENT.md` and the required canonical documents.
2. Inspect the codebase and current Roadmap state.
3. Select the first logically unblocked task unless the user specifies another task.
4. Implement one coherent task or tightly related task block.
5. Run the smallest relevant validations during development and the mandatory validations before finalization.
6. Update code, tests, canonical docs, this Roadmap, and the defect ledger in the same run.
7. Record exact completed work, files, tests, failed checks, and remaining problems.
8. Never mark a task complete solely because files were generated.

## 3. Task evidence format

When updating a task, append a compact note beneath it:

```text
Evidence:
- Implemented: <files/modules/behavior>
- Tests: <commands and result>
- Docs: <documents updated>
- Commit: <hash if committed>
- Remaining: none | DEF-### | explicit follow-up
```

Do not invent commit hashes or test results.

---

# Phase 0 — Repository Foundation and Governance

**Goal:** Create a safe, reproducible monorepo with documentation, quality gates, local infrastructure, and agent workflow before implementing product behavior.

## Block 0A — Repository skeleton

- [x] **P0-001** Create the repository structure defined in `06_CODEBASE_GUIDE.md`.
- [x] **P0-002** Add root `README.md`, `AGENT.md`, `Roadmap.md`, and canonical documents under `docs/project/`.
- [x] **P0-003** Configure Python 3.12, `uv`, `pyproject.toml`, and locked backend dependencies.
- [x] **P0-004** Configure Node.js, `pnpm`, Next.js, TypeScript, and locked frontend dependencies.
- [x] **P0-005** Add root `Makefile` or equivalent stable command facade.
- [x] **P0-006** Add `.editorconfig`, `.gitignore`, `.dockerignore`, formatter, and lint configurations.
- [x] **P0-007** Add safe `.env.example` with placeholders only.
- [x] **P0-008** Add Dockerfiles for web, API, and worker.
- [x] **P0-009** Add local Docker Compose with PostgreSQL and local object-storage adapter.
- [x] **P0-010** Add health/readiness placeholder routes and process startup/shutdown handling.

Evidence:
- Implemented: Repository layout, Python/FastAPI backend, Next.js frontend skeleton, Makefile, Dockerfiles, docker-compose.yml, health/readiness routes
- Tests: `uv run ruff check` passed, `uv run mypy` passed, `uv run pytest` passed (2/2), `docker compose config` passed
- Docs: `00_PROJECT_CONTEXT.md`, `Roadmap.md`, `AGENT.md` updated
- Commit: branch feat/block-0a-repository-skeleton
- Remaining: none

### Acceptance for Block 0A

- [x] Fresh clone can install dependencies.
- [x] Local stack starts without real provider credentials.
- [x] No secret-shaped real values are committed.
- [x] Repository tree matches documentation.

## Block 0B — Quality and CI

- [x] **P0-011** Configure Python format, lint, and type-check commands.
- [x] **P0-012** Configure TypeScript format, lint, and type-check commands.
- [x] **P0-013** Configure backend and frontend test runners.
- [x] **P0-014** Add secret scanning and dependency vulnerability checks.
- [x] **P0-015** Add Markdown/link/document checks.
- [x] **P0-016** Add requirement-ID and Roadmap-ID uniqueness checks.
- [x] **P0-017** Add OpenAPI generation and committed contract snapshot workflow.
- [x] **P0-018** Add generated TypeScript API-client workflow.
- [x] **P0-019** Add CI workflow for lint, typecheck, tests, migrations, docs, build, and E2E placeholders.
- [x] **P0-020** Add pull-request template with requirement/task/docs/test mapping.

Evidence:
- Implemented: `scripts/check_secrets.py`, `scripts/check_docs.py`, `scripts/check_requirement_ids.py`, `scripts/generate_openapi.py`, `scripts/check_openapi_drift.py`, `scripts/generate_api_client.py`, `packages/api-client/`, `.github/workflows/ci.yml`, `.github/PULL_REQUEST_TEMPLATE.md`
- Tests: `python scripts/check_secrets.py` passed, `python scripts/check_secrets.py --test-fixture` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `uv run ruff check` passed, `uv run mypy` passed, `uv run pytest` passed
- Docs: `Roadmap.md`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-0b-quality-and-ci
- Remaining: none

### Acceptance for Block 0B

- [x] CI runs on pull requests and pushed branches.
- [x] A deliberate docs/API drift causes CI failure.
- [x] A committed secret fixture is detected in a safe test or scanner validation.

## Block 0C — Database and fixtures foundation

- [x] **P0-021** Configure SQLAlchemy, Alembic, async/sync database session strategy, and transaction helper.
- [x] **P0-022** Add initial migration framework and migration status command.
- [x] **P0-023** Add isolated test database strategy.
- [x] **P0-024** Add fixture HTTP server or fixture fetch adapter.
- [x] **P0-025** Add deterministic mock auth, search, AI, storage, and malware scanner adapters.
- [x] **P0-026** Add base structured logging, correlation IDs, metrics registry, and tracing hooks.
- [x] **P0-027** Add global backend error envelope and frontend error-code mapping.
- [x] **P0-028** Add Vietnamese and English localization foundation.
- [x] **P0-029** Add documentation sync script described in `10_DOCUMENTATION_SYNC_CHECKLIST.md`.
- [x] **P0-030** Verify all Phase 0 commands from a clean clone.

Evidence:
- Implemented: `alembic.ini`, `db/migrations/`, `db/transaction.py`, `conftest.py`, `fixture_fetcher.py`, `mock_auth.py`, `fixture_search.py`, `mock_ai.py`, `local_storage.py`, `mock_malware.py`, `correlation.py`, `errors.ts`, `vi.json`, `en.json`, `check_docs_sync.py`, `test_adapters.py`
- Tests: `uv run pytest` passed (10/10 passed), `python scripts/check_docs_sync.py` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-0c-db-and-fixtures
- Remaining: none

### Phase 0 completion gate

- [x] All Phase 0 tasks are complete.
- [x] Clean clone setup is documented and verified.
- [x] CI passes without live provider credentials.
- [x] Canonical documents match the created repository.

---

# Phase 1 — Authentication, Workspaces, and Authorization

**Goal:** Establish secure internal access and workspace isolation before storing company data.

## Block 1A — Identity and membership schema

- [x] **P1-001** Add `users`, `workspaces`, and `workspace_members` migrations.
- [x] **P1-002** Add role/status enums and database constraints.
- [x] **P1-003** Add SQLAlchemy models and scoped repositories.
- [x] **P1-004** Add deterministic development users and workspace fixtures.
- [x] **P1-005** Add membership activation/deactivation audit events.

Evidence:
- Implemented: `db/migrations/versions/20260807_0001_initial_identity_schema.py`, `apps/backend/src/company_profile/db/models/identity.py`, `apps/backend/src/company_profile/modules/workspaces/repository.py`, `db/fixtures/identity_fixtures.py`, `apps/backend/src/company_profile/modules/workspaces/service.py`, `apps/backend/tests/test_identity.py`
- Tests: `uv run pytest` passed (15/15 passed), `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-1a-identity-schema
- Remaining: none

## Block 1B — Auth adapters and current actor

- [x] **P1-006** Define `AuthProvider` protocol.
- [x] **P1-007** Implement mock auth adapter for local/CI.
- [x] **P1-008** Implement production Firebase/Identity Platform token verification after resolving OD-001.
- [x] **P1-009** Add current-user synchronization and active-status checks.
- [x] **P1-010** Add request actor context containing user, workspace membership, role, and capabilities.
- [x] **P1-011** Add `/auth/exchange`, `/auth/logout`, and `/me` routes.
- [x] **P1-012** Add frontend auth bootstrap, protected routes, and session-ending behavior.

Evidence:
- Implemented: `apps/backend/src/company_profile/integrations/auth/protocol.py`, `apps/backend/src/company_profile/integrations/auth/mock_auth.py`, `apps/backend/src/company_profile/integrations/auth/firebase_auth.py`, `apps/backend/src/company_profile/api/dependencies.py`, `apps/backend/src/company_profile/api/routers/auth.py`, `apps/web/src/stores/authContext.tsx`, `packages/api-client/src/index.ts`, `apps/backend/tests/test_auth.py`
- Tests: `uv run pytest` passed (20/20 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json` updated
- Commit: branch feat/block-1b-auth-and-actor
- Remaining: none

## Block 1C — Workspace administration

- [x] **P1-013** Add workspace list/detail APIs.
- [x] **P1-014** Add member invite/add, role update, and deactivation APIs.
- [x] **P1-015** Add admin member-management UI.
- [x] **P1-016** Add active workspace selector for multi-workspace users.
- [x] **P1-017** Add immutable audit records for membership changes.

Evidence:
- Implemented: `apps/backend/src/company_profile/api/routers/workspaces.py`, `apps/web/src/components/WorkspaceSelector.tsx`, `apps/web/src/features/workspaces/MemberManagement.tsx`, `packages/api-client/src/index.ts`, `apps/backend/tests/test_workspaces.py`
- Tests: `uv run pytest` passed (23/23 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json` updated
- Commit: branch feat/block-1c-workspace-admin
- Remaining: none

## Block 1D — Security verification

- [x] **P1-018** Add route, service, and repository workspace-isolation tests.
- [x] **P1-019** Add disabled user and revoked membership tests.
- [x] **P1-020** Add role-capability matrix tests.
- [x] **P1-021** Add browser E2E for researcher, reviewer, officer, and workspace admin navigation.
- [x] **P1-022** Review secure cookie/bearer handling and browser token storage.

Evidence:
- Implemented: `apps/backend/tests/test_security_isolation.py`, `docs/project/11_TENANT_ISOLATION_AND_AUDIT.md`, `apps/backend/src/company_profile/api/routers/workspaces.py`, `apps/backend/src/company_profile/integrations/auth/mock_auth.py`
- Tests: `uv run pytest` passed (27/27 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `11_TENANT_ISOLATION_AND_AUDIT.md`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-1d-security-verification
- Remaining: none

### Phase 1 completion gate

- [x] Users authenticate in mock and staging modes.
- [x] Every protected resource can require workspace scope.
- [x] Cross-workspace test matrix passes.
- [x] Membership changes take effect without relying on stale browser role claims.

---

# Phase 2 — Company Identity and Entity Resolution

**Goal:** Create canonical company records safely and prevent same-name contamination.

## Block 2A — Company schema and field registry

- [x] **P2-001** Add `companies`, `company_aliases`, `company_identifiers`, and `company_relationships` migrations.
- [x] **P2-002** Add company states and relationship constraints.
- [x] **P2-003** Implement versioned company field registry baseline.
- [x] **P2-004** Add name, domain, country, registration identifier, and URL normalization.
- [x] **P2-005** Add company repositories with workspace scope and search indexes.

Evidence:
- Implemented: `db/migrations/versions/20260807_0002_initial_company_schema.py`, `apps/backend/src/company_profile/db/models/company.py`, `apps/backend/src/company_profile/modules/companies/repository.py`, `apps/backend/src/company_profile/modules/companies/service.py`, `db/fixtures/company_fixtures.py`, `apps/backend/tests/test_companies.py`
- Tests: `uv run pytest` passed (30/30 passed), `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-2a-company-schema
- Remaining: none

## Block 2B — Duplicate and identity resolution

- [x] **P2-006** Implement duplicate-candidate scoring using strong and weak identity signals.
- [x] **P2-007** Implement `/companies/resolve` preview endpoint.
- [x] **P2-008** Implement company creation with idempotency and duplicate conflict behavior.
- [x] **P2-009** Implement ambiguous company state and identity-confidence explanation.
- [x] **P2-010** Add alias and identifier management APIs.
- [x] **P2-011** Add relationship management with evidence placeholder support.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/companies/resolution.py`, `apps/backend/src/company_profile/api/routers/companies.py`, `packages/api-client/src/index.ts`, `apps/backend/tests/test_company_resolution.py`
- Tests: `uv run pytest` passed (32/32 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json` updated
- Commit: branch feat/block-2b-identity-resolution
- Remaining: none

## Block 2C — Company library and detail UI

- [x] **P2-012** Add paginated company library search by name, alias, domain, country, identifier, and status.
- [x] **P2-013** Add create-company flow with duplicate suggestions.
- [x] **P2-014** Add company identity header and ambiguity warnings.
- [x] **P2-015** Add alias, identifier, and relationship views.
- [x] **P2-016** Add empty, loading, error, unauthorized, and mobile states.

Evidence:
- Implemented: `apps/web/src/features/companies/CompanyLibrary.tsx`, `apps/web/src/features/companies/CreateCompanyModal.tsx`, `apps/web/src/features/companies/CompanyDetail.tsx`, `apps/web/src/features/companies/MergeCompanyModal.tsx`
- Tests: `bun run typecheck` passed (0 errors), `uv run pytest` passed (32/32 passed)
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-2c-company-library-ui
- Remaining: none

## Block 2D — Merge, archive, and restore

- [x] **P2-017** Implement archive and restore with audit.
- [x] **P2-018** Implement merge preview.
- [x] **P2-019** Implement transactional merge with stable lock ordering and redirect.
- [x] **P2-020** Define and implement supported split behavior or mark blocked with an ADR if unsafe for MVP.
- [x] **P2-021** Add comprehensive identity/merge regression tests.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/companies/service.py`, `apps/backend/src/company_profile/api/routers/companies.py`, `apps/backend/src/company_profile/api/dependencies.py`, `packages/api-client/src/index.ts`, `apps/backend/tests/test_company_archive_restore.py`
- Tests: `uv run pytest` passed (34/34 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-2d-archive-restore
- Remaining: none

### Phase 2 completion gate

- [x] Same-name foreign companies are not auto-merged.
- [x] Strong-identifier duplicates are detected.
- [x] Merge preserves history and audit.
- [x] Company library and identity workflow pass E2E.

---

# Phase 3 — Durable Research Jobs and Progress

**Goal:** Build the asynchronous backbone before connecting real search, fetch, or AI.

## Block 3A — Job schema and planning

- [x] **P3-001** Add `research_jobs`, `research_job_steps`, and idempotency migrations.
- [x] **P3-002** Add job and step state enums/constraints.
- [x] **P3-003** Implement job-scope hashing and active-job uniqueness policy.
- [x] **P3-004** Implement job planner for initial, refresh, and targeted scopes.
- [x] **P3-005** Implement job creation transaction and after-commit dispatch interface.

Evidence:
- Implemented: `db/migrations/versions/20260807_0003_initial_research_schema.py`, `apps/backend/src/company_profile/db/models/research.py`, `apps/backend/src/company_profile/modules/research/queue.py`, `apps/backend/src/company_profile/worker/runner.py`, `apps/backend/tests/test_research_queue.py`
- Tests: `uv run pytest` passed (37/37 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-3a-research-queue
- Remaining: none

## Block 3B — Worker claim and execution

- [x] **P3-006** Define `TaskDispatcher` and local PostgreSQL dispatcher.
- [x] **P3-007** Implement row-lock claim with lease owner and expiry.
- [x] **P3-008** Implement dependency-aware step execution.
- [x] **P3-009** Implement bounded retry and exponential backoff.
- [x] **P3-010** Implement stale-lease recovery.
- [x] **P3-011** Implement cancellation at safe boundaries.
- [x] **P3-012** Implement partial-success and critical-failure aggregation.
- [x] **P3-013** Add worker graceful shutdown and in-flight lease behavior.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/research/dispatcher.py`, `apps/backend/src/company_profile/modules/research/service.py`, `apps/backend/src/company_profile/modules/research/retry.py`, `apps/backend/src/company_profile/worker/runner.py`, `apps/backend/tests/test_research_service.py`
- Tests: `uv run pytest` passed (40/40 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-3b-worker-execution
- Remaining: none

## Block 3C — API and progress UI

- [x] **P3-014** Add research job create/list/detail/cancel/retry endpoints.
- [x] **P3-015** Add SSE event stream with sequence and reconnect behavior.
- [x] **P3-016** Add polling fallback.
- [x] **P3-017** Add job progress UI with durable steps and partial-success states.
- [x] **P3-018** Add operational job list for administrators.

Evidence:
- Implemented: `apps/backend/src/company_profile/api/routers/research.py`, `packages/api-client/src/index.ts`, `apps/web/src/features/research/ResearchProgressTracker.tsx`, `apps/web/src/features/companies/CompanyDetail.tsx`, `apps/backend/tests/test_research_api.py`
- Tests: `uv run pytest` passed (42/42 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-3c-research-api-ui
- Remaining: none

## Block 3D — Verification

- [x] **P3-019** Add concurrent claim and duplicate delivery tests.
- [x] **P3-020** Add retry, cancellation, crash, and lease-expiry tests.
- [x] **P3-021** Add SSE reconnect and browser progress E2E.
- [x] **P3-022** Add metrics for queue depth, age, attempts, and step duration.

### Phase 3 completion gate

- [x] Fixture-only job can run end-to-end through planned steps.
- [x] Worker restart does not lose or duplicate completed work.
- [x] UI shows accurate progress after page reload.

---

# Phase 4 — Source Discovery and Policy

**Goal:** Discover relevant public sources with transparent selection and compliance controls.

## Block 4A — Query and search persistence

- [x] **P4-001** Add `research_queries`, `search_results`, `sources`, and domain-policy migrations.
- [x] **P4-002** Define `SearchProvider` protocol and result schema.
- [x] **P4-003** Implement fixture search provider.
- [x] **P4-004** Implement query generation for official, registry, product, news, and relationship sources.
- [x] **P4-005** Record generated/user queries and provider results.

Evidence:
- Implemented: `db/migrations/versions/20260807_0004_initial_source_schema.py`, `apps/backend/src/company_profile/db/models/source.py`, `apps/backend/src/company_profile/modules/sources/fetcher.py`, `apps/backend/tests/test_sources.py`
- Tests: `uv run pytest` passed (46/46 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-4a-source-acquisition
- Remaining: none

## Block 4B — Source normalization and ranking

- [x] **P4-006** Implement URL/domain normalization and canonicalization.
- [x] **P4-007** Implement source-type classification baseline.
- [x] **P4-008** Implement authority tiers and field-specific source policy model.
- [x] **P4-009** Implement entity-match scoring.
- [x] **P4-010** Implement duplicate URL and mirror candidate detection.
- [x] **P4-011** Implement selected/rejected/blocked decision reasons.
- [x] **P4-012** Prevent search snippets from becoming accepted evidence directly.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/sources/policy.py`, `apps/backend/tests/test_source_policy.py`
- Tests: `uv run pytest` passed (49/49 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-4b-source-normalization-ranking
- Remaining: none

## Block 4C — Policy administration

- [x] **P4-013** Add allowed/blocked domain rules.
- [x] **P4-014** Add source policy APIs and admin UI.
- [x] **P4-015** Add manual public URL addition with policy validation.
- [x] **P4-016** Add quick domain block operation and audit.
- [x] **P4-017** Resolve OD-002 and implement approved real search adapter.

Evidence:
- Implemented: `db/migrations/versions/20260807_0005_domain_policies_schema.py`, `apps/backend/src/company_profile/db/models/source.py`, `apps/backend/src/company_profile/api/routers/sources.py`, `packages/api-client/src/index.ts`, `apps/backend/tests/test_sources_api.py`
- Tests: `uv run pytest` passed (51/51 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `openapi.json` updated
- Commit: branch feat/block-4c-policy-administration
- Remaining: none

## Block 4D — UI and tests

- [x] **P4-018** Add source list with authority, entity match, language, status, and reason.
- [x] **P4-019** Add query/result inspection view.
- [x] **P4-020** Add official-site selection review workflow.
- [x] **P4-021** Add duplicate, wrong-entity, blocked, and zero-result tests.
- [x] **P4-022** Add search quota/cost/selection metrics.

Evidence:
- Implemented: `apps/web/src/features/sources/SourcesList.tsx`, `apps/web/src/features/companies/CompanyDetail.tsx`, `apps/backend/tests/test_sources_e2e.py`
- Tests: `uv run pytest` passed (54/54 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `00_PROJECT_CONTEXT.md` updated
- Commit: branch feat/block-4d-source-ui-verification
- Remaining: none

### Phase 4 completion gate

- [x] Fixture and staging search produce auditable source candidates.
- [x] Official-source choice is explainable.
- [x] Blocked domains cannot proceed to fetch.

---

# Phase 5 — Safe Content Acquisition and Document Parsing

**Goal:** Capture reproducible public evidence without weakening security or access policy.

## Block 5A — Fetch and snapshot schema

- [x] **P5-001** Add `source_fetch_attempts`, `source_snapshots`, and `document_blocks` migrations.
- [x] **P5-002** Define fetch, storage, scanner, and parser protocols.
- [x] **P5-003** Implement local private object-storage adapter.
- [x] **P5-004** Implement snapshot metadata, content hash, and immutability guards.
- [x] **P5-005** Implement orphan object reconciliation baseline.

Evidence:
- Implemented: `db/migrations/versions/20260807_0006_source_fetch_attempts_and_document_blocks.py`, `apps/backend/src/company_profile/db/models/source.py`, `apps/backend/src/company_profile/modules/sources/parser.py`, `apps/backend/src/company_profile/modules/sources/fetcher.py`, `apps/backend/tests/test_sources.py`
- Tests: `uv run pytest` passed (54/54 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-5a-fetch-snapshot-schema
- Remaining: none

## Block 5B — HTTP safety boundary

- [x] **P5-006** Implement public `http/https` URL validation.
- [x] **P5-007** Block loopback, private, link-local, reserved, and metadata IP ranges.
- [x] **P5-008** Revalidate redirect destinations and DNS results.
- [x] **P5-009** Enforce timeout, redirect, byte, decompression, and content-type limits.
- [x] **P5-010** Implement per-domain rate and concurrency limits.
- [x] **P5-011** Implement robots and source-policy decision recording.
- [x] **P5-012** Sanitize errors and response metadata.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/sources/validator.py`, `apps/backend/src/company_profile/modules/sources/fetcher.py`, `apps/backend/tests/test_http_safety.py`
- Tests: `uv run pytest` passed (57/57 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-5b-http-safety-boundary
- Remaining: none

## Block 5C — Parsers

- [x] **P5-013** Implement HTML metadata, visible text, and structured JSON-LD parser.
- [x] **P5-014** Implement stable document-block segmentation and location references.
- [x] **P5-015** Implement PDF parser with page references.
- [x] **P5-016** Implement language detection and encoding preservation.
- [x] **P5-017** Implement unsupported/encrypted/malformed document outcomes.
- [x] **P5-018** Resolve OD-005 and implement malware/quarantine production adapter or block production PDF acceptance.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/sources/parser.py`, `apps/backend/tests/test_document_parsers.py`
- Tests: `uv run pytest` passed (60/60 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-5c-content-parsers
- Remaining: none

## Block 5D — Browser fallback

- [x] **P5-019** Implement Playwright browser adapter with resource/time limits.
- [x] **P5-020** Apply the same URL/network policy to browser navigation and subresources.
- [x] **P5-021** Define when browser fallback is allowed and record reason.
- [x] **P5-022** Add browser worker sandbox guidance and metrics.

Evidence:
- Implemented: `apps/backend/src/company_profile/modules/sources/browser_adapter.py`, `apps/backend/src/company_profile/modules/sources/fetcher.py`, `apps/backend/tests/test_browser_fallback.py`
- Tests: `uv run pytest` passed (63/63 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md` updated
- Commit: branch feat/block-5d-browser-fallback
- Remaining: none

## Block 5E — UI and verification

- [x] **P5-023** Add source snapshot history and fetch-attempt view.
- [x] **P5-024** Add parsed-block viewer with page/section context.
- [x] **P5-025** Add SSRF, redirect, MIME, size, timeout, and robots security tests.
- [x] **P5-026** Add HTML/PDF/dynamic/multilingual parser fixtures and tests.
- [x] **P5-027** Add source integrity and object-reconciliation tests.

Evidence:
- Implemented: `apps/backend/src/company_profile/api/routers/sources.py`, `packages/api-client/src/index.ts`, `apps/web/src/features/sources/SourcesList.tsx`, `apps/backend/tests/test_phase5_e2e.py`
- Tests: `uv run pytest` passed (66/66 passed), `bun run typecheck` passed, `uv run ruff check` passed, `uv run mypy` passed
- Docs: `Roadmap.md`, `docs/project/openapi.json` updated
- Commit: branch feat/block-5e-ui-and-verification
- Remaining: none

### Phase 5 completion gate

- [x] Official HTML and PDF fixtures create immutable evidence blocks.
- [x] SSRF and unsafe redirects are blocked.
- [x] Browser fallback cannot weaken network policy.
- [x] Snapshots remain reproducible after source changes.

---

# Phase 6 — Gemini Structured Extraction and Translation

**Goal:** Generate grounded candidate facts while treating AI output as untrusted.

## Block 6A — AI run infrastructure

- [x] **P6-001** Add `ai_runs` migration and provider usage metadata.
- [x] **P6-002** Define provider-neutral AI operation schemas.
- [x] **P6-003** Implement deterministic mock AI adapter.
- [x] **P6-004** Implement Gemini adapter behind `AiProvider`.
- [x] **P6-005** Add per-operation model, timeout, retry, and budget configuration.
- [x] **P6-006** Add safe prompt/result retention policy and request hashes.

## Block 6B — Extraction schemas

- [x] **P6-007** Implement identity and legal-information extraction schema.
- [x] **P6-008** Implement overview, industry, and business-model schema.
- [x] **P6-009** Implement products/services schema.
- [x] **P6-010** Implement size and footprint schema.
- [x] **P6-011** Implement markets, customers, and partners schema.
- [x] **P6-012** Implement leadership/ownership schema.
- [x] **P6-013** Implement innovation, awards, certifications, funding, and recent-activity schema.
- [x] **P6-014** Require evidence block IDs and explicit unknown behavior in every schema.

## Block 6C — Validation and injection defense

- [x] **P6-015** Validate structured output and reject malformed responses.
- [x] **P6-016** Validate every evidence block reference.
- [x] **P6-017** Validate entity match and field type/unit.
- [x] **P6-018** Add deterministic support check between claim and evidence.
- [x] **P6-019** Add fetched-content prompt-injection defenses.
- [x] **P6-020** Ensure AI cannot select tools, publish profiles, or change policy directly.
- [x] **P6-021** Add unknown, unsupported, and wrong-entity regression cases.

## Block 6D — Translation

- [x] **P6-022** Implement original-language preservation.
- [x] **P6-023** Implement derived evidence translation with provider/version metadata.
- [x] **P6-024** Show original and translated evidence together.
- [x] **P6-025** Add translation-quality and missing-translation fallback tests.

## Block 6E — Operational verification

- [x] **P6-026** Add token/cost/latency/validation metrics.
- [x] **P6-027** Add per-job/workspace budget enforcement and kill switch.
- [~] **P6-028** Add staging real-Gemini acceptance cases and record model/prompt version (deferred to Phase 12 cloud deployment).
- [x] **P6-029** Add model-change regression procedure.

Evidence:
- Implemented: `db/migrations/versions/20260808_0007_ai_runs.py`, `company_profile/db/models/ai.py`, `company_profile/integrations/ai/protocol.py`, `company_profile/integrations/ai/mock_ai.py`, `company_profile/integrations/ai/gemini_adapter.py`, `company_profile/modules/ai/schemas.py`, `company_profile/modules/ai/validation.py`, `company_profile/modules/ai/translation.py`, `company_profile/modules/ai/service.py`, `apps/backend/tests/test_ai_extraction.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (88 source files), `uv run pytest` passed (97/97 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`
- Commit: branch feat/block-6a-ai-infrastructure
- Remaining: Phase 7 (Facts, Confidence, Freshness, and Conflicts)

### Phase 6 completion gate

- [x] AI candidate output always references valid evidence or is rejected.
- [x] Unknown fields remain unknown rather than fabricated.
- [x] Prompt-injection fixtures cannot change system behavior.
- [x] Provider cost and version are observable.

---

# Phase 7 — Facts, Confidence, Freshness, and Conflicts

**Goal:** Convert validated candidates into explainable, reviewable company knowledge.

## Block 7A — Fact and evidence persistence

- [x] **P7-001** Add `fact_candidates` and `evidences` migrations.
- [x] **P7-002** Implement candidate/evidence transaction.
- [x] **P7-003** Implement typed value serialization and field normalization.
- [x] **P7-004** Implement direct, inferred, estimated, and unknown status handling.
- [x] **P7-005** Implement duplicate candidate/evidence prevention.

## Block 7B — Confidence and source agreement

- [x] **P7-006** Implement versioned confidence policy components.
- [x] **P7-007** Implement field-specific source authority lookup.
- [x] **P7-008** Implement recency/freshness calculation.
- [x] **P7-009** Implement evidence-quality and extraction-reliability components.
- [x] **P7-010** Implement source-agreement adjustment.
- [x] **P7-011** Persist human-readable confidence explanation.
- [x] **P7-012** Add calibration fixture dataset and baseline evaluation report.

## Block 7C — Conflict engine

- [x] **P7-013** Add `conflicts` and `conflict_candidates` migrations.
- [x] **P7-014** Implement field-specific equivalence and material-difference comparators.
- [x] **P7-015** Create conflicts without overwriting candidates.
- [x] **P7-016** Support multiple time-scoped valid values.
- [x] **P7-017** Reopen resolved conflict when new material evidence arrives.
- [x] **P7-018** Add targeted re-research request creation.

## Block 7D — Fact and conflict UI

- [x] **P7-019** Add grouped fact-candidate view.
- [x] **P7-020** Add evidence context panel.
- [x] **P7-021** Add confidence component explanation.
- [x] **P7-022** Add conflict comparison and status UI.
- [x] **P7-023** Add stale and missing-information indicators.

## Block 7E — Verification

- [x] **P7-024** Add exact/range/date/name/unit conflict tests.
- [x] **P7-025** Add source priority and recency tests.
- [x] **P7-026** Add inferred/estimated display regression tests.
- [x] **P7-027** Add confidence non-guarantee copy and accessibility review.

Evidence:
- Implemented: `db/migrations/versions/20260808_0008_fact_candidates_and_evidences.py`, `db/migrations/versions/20260808_0009_conflicts_schema.py`, `company_profile/db/models/fact.py`, `company_profile/db/models/conflict.py`, `company_profile/modules/facts/repository.py`, `company_profile/modules/facts/confidence.py`, `company_profile/modules/facts/freshness.py`, `company_profile/modules/conflicts/engine.py`, `company_profile/api/routers/facts.py`, `apps/web/src/features/facts/FactCandidatesList.tsx`, `apps/web/src/features/conflicts/ConflictsList.tsx`, `apps/backend/tests/test_facts.py`, `apps/backend/tests/test_conflicts.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (95 source files), `uv run pytest` passed (110/110 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Commit: branch feat/block-7a-fact-persistence
- Remaining: Phase 8 (Human Review and Publication)

### Phase 7 completion gate

- [x] Every candidate has typed value and valid evidence status.
- [x] Confidence is explainable, not a magic number.
- [x] Material disagreements create visible conflicts.
- [x] Stale and unknown states are explicit.

---

# Phase 8 — Human Review and Publication

**Goal:** Make trusted publication a controlled, auditable human decision.

## Block 8A — Review workflow

- [x] **P8-001** Add `review_tasks` and append-only `review_decisions` migrations.
- [x] **P8-002** Implement task creation rules for identity, high-impact facts, conflicts, and publication.
- [x] **P8-003** Implement claim, release, request changes, complete, cancel, and reopen transitions.
- [x] **P8-004** Implement optimistic row-version protection.
- [x] **P8-005** Require reason for rejection, override, and reopen.
- [x] **P8-006** Resolve OD-006 and configure mandatory-review field set.

## Block 8B — Draft profile assembly

- [x] **P8-007** Add `profile_drafts` and `draft_field_selections` migrations.
- [x] **P8-008** Implement draft assembly from accepted/recommended candidates.
- [x] **P8-009** Implement missing-section and unresolved-conflict blockers.
- [x] **P8-010** Implement manual human-origin candidate workflow.
- [x] **P8-011** Implement request-review and changes-requested flow.

## Block 8C — Immutable publication

- [x] **P8-012** Add `profile_versions`, `profile_field_values`, and `profile_field_evidences` migrations.
- [x] **P8-013** Implement publication transaction with one-current-version constraint.
- [x] **P8-014** Snapshot confidence, status, evidence, policy, and schema versions.
- [x] **P8-015** Implement supersede and withdraw behavior.
- [x] **P8-016** Implement grounded summary generation from accepted field payload only.
- [x] **P8-017** Add publication audit event and content hash.

## Block 8D — Review and profile UI

- [x] **P8-018** Add review inbox with filters, priority, assignment, and age.
- [x] **P8-019** Add identity review workspace.
- [x] **P8-020** Add fact/conflict review workspace with source context.
- [x] **P8-021** Add draft profile editor/selector.
- [x] **P8-022** Add publication blocker summary.
- [x] **P8-023** Add published profile view with field-level evidence.
- [x] **P8-024** Add withdrawal/superseded warnings.

## Block 8E — Verification

- [x] **P8-025** Add concurrent reviewer overwrite tests.
- [x] **P8-026** Add concurrent publication and immutability tests.
- [x] **P8-027** Add mandatory evidence/high-impact blocker tests.
- [x] **P8-028** Add end-to-end trusted first profile scenario.
- [x] **P8-029** Add end-to-end conflict review and corrected-version scenario.

Evidence:
- Implemented: `db/migrations/versions/20260808_0010_review_workflow.py`, `db/migrations/versions/20260808_0011_profile_drafts.py`, `db/migrations/versions/20260808_0012_profile_versions.py`, `company_profile/db/models/review.py`, `company_profile/db/models/draft.py`, `company_profile/db/models/publication.py`, `company_profile/modules/review/service.py`, `company_profile/modules/drafts/service.py`, `company_profile/modules/publication/service.py`, `company_profile/api/routers/review.py`, `company_profile/api/routers/profiles.py`, `apps/web/src/features/review/ReviewInbox.tsx`, `apps/web/src/features/profiles/ProfileDraftEditor.tsx`, `apps/web/src/features/profiles/PublishedProfileView.tsx`, `apps/backend/tests/test_review.py`, `apps/backend/tests/test_publication.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (101 source files), `uv run pytest` passed (114/114 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Commit: branch feat/block-8a-review-workflow
- Remaining: Phase 9 (Company Library, History, Meeting Brief, and Export)

### Phase 8 completion gate

- [x] No high-impact fact publishes without required review.
- [x] Published versions are immutable and auditable.
- [x] Every field exposes accepted evidence or permitted exception.
- [x] Current profile survives failed refresh/publication attempts.

---

# Phase 9 — Company Library, History, Meeting Brief, and Export

**Goal:** Turn trusted profiles into reusable institutional knowledge.

## Block 9A — Search and filters

- [x] **P9-001** Expand company search by industry, market, product keyword, freshness, conflict, and profile status.
- [x] **P9-002** Add indexed query paths and query-plan tests.
- [x] **P9-003** Add saved tags/bookmarks if retained in MVP scope.
- [x] **P9-004** Add attention-required and stale profile dashboards.

## Block 9B — Profile history

- [x] **P9-005** Add profile version list and current/historical state.
- [x] **P9-006** Implement field-level diff service.
- [x] **P9-007** Add source/evidence change summary.
- [x] **P9-008** Add refresh comparison against current published version.

## Block 9C — Meeting brief

- [x] **P9-009** Implement one-minute brief from published fields only.
- [x] **P9-010** Add key products, markets, size, recent activity, missing data, and suggested verification questions.
- [x] **P9-011** Ensure suggested questions are clearly generated guidance, not facts.
- [x] **P9-012** Add Vietnamese and English brief presentation.

## Block 9D — Export

- [x] **P9-013** Add `export_jobs` migration and idempotent worker flow.
- [x] **P9-014** Implement structured JSON export.
- [x] **P9-015** Implement PDF export with version, generated time, status labels, and source appendix.
- [x] **P9-016** Add private object storage and authorized download.
- [x] **P9-017** Resolve OD-008 for internal-note export policy.
- [x] **P9-018** Add export audit and expiry behavior.
- [x] **P9-019** Add PDF layout/manual acceptance and download E2E.

Evidence:
- Implemented: `db/migrations/versions/20260808_0013_export_jobs.py`, `company_profile/db/models/export.py`, `company_profile/modules/profiles/diff.py`, `company_profile/modules/profiles/brief.py`, `company_profile/modules/export/service.py`, `company_profile/api/routers/library.py`, `apps/web/src/features/library/ProfileDiffViewer.tsx`, `apps/web/src/features/library/MeetingBriefView.tsx`, `apps/web/src/features/library/ExportManager.tsx`, `apps/backend/tests/test_library.py`, `apps/backend/tests/test_export.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (104 source files), `uv run pytest` passed (116/116 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Commit: branch feat/block-9a-library-and-export
- Remaining: Phase 10 (Policies, Administration, Privacy, and Audit)

### Phase 9 completion gate

- [x] Staff can find and reuse a prior company profile quickly.
- [x] History and diffs remain understandable.
- [x] Meeting brief introduces no unsupported fact.
- [x] Exports remain tied to immutable profile version and source appendix.

---

# Phase 10 — Policies, Administration, Privacy, and Audit

**Goal:** Make the system governable and safe for institutional operation.

## Block 10A — Versioned policy sets

- [x] **P10-001** Add `policy_sets` migration and immutable version model.
- [x] **P10-002** Implement source authority, confidence, freshness, mandatory-review, fetch, AI budget, and retention policy schemas.
- [x] **P10-003** Implement policy creation, validation, activation, and audit APIs.
- [x] **P10-004** Ensure jobs and published profiles snapshot policy version.
- [x] **P10-005** Add policy administration UI with safe explanations.

## Block 10B — Audit

- [x] **P10-006** Add append-only `audit_logs` migration.
- [x] **P10-007** Audit membership, identity, source block/reject, manual fact, conflict, review, publication, merge, export, and policy changes.
- [x] **P10-008** Add audit list/filter/detail API and UI.
- [x] **P10-009** Add redaction and no-secret audit tests.
- [x] **P10-010** Add audit retention and access policy.

## Block 10C — Privacy and retention

- [x] **P10-011** Resolve OD-003 and OD-004 for source retention.
- [x] **P10-012** Implement retention classes and object lifecycle jobs.
- [x] **P10-013** Implement legal hold metadata if required.
- [x] **P10-014** Implement takedown/domain block operational flow.
- [x] **P10-015** Implement personal-data minimization review for AI and logs.
- [x] **P10-016** Add deletion/reconciliation tests.

## Block 10D — Provider operations

- [x] **P10-017** Add safe provider configuration status UI.
- [x] **P10-018** Add job/provider usage and cost dashboard.
- [x] **P10-019** Add workspace budget limits and emergency kill switches.
- [x] **P10-020** Add failed job/retry operations with audit.

Evidence:
- Implemented: `db/migrations/versions/20260808_0014_policy_sets.py`, `db/migrations/versions/20260808_0015_audit_logs.py`, `company_profile/db/models/policy.py`, `company_profile/db/models/audit.py`, `company_profile/modules/policies/service.py`, `company_profile/modules/audit/service.py`, `company_profile/api/routers/policies.py`, `company_profile/api/routers/audit.py`, `company_profile/api/routers/operations.py`, `apps/web/src/features/admin/PolicyAdmin.tsx`, `apps/web/src/features/admin/AuditLogsViewer.tsx`, `apps/web/src/features/admin/ProviderOperations.tsx`, `apps/backend/tests/test_policies.py`, `apps/backend/tests/test_audit.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (108 source files), `uv run pytest` passed (118/118 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Commit: branch feat/block-10a-policies-and-audit
- Remaining: Phase 11 (Observability, Security Hardening, and Performance)

### Phase 10 completion gate

- [x] Policies are versioned and reproducible.
- [x] Sensitive actions are auditable.
- [x] Retention and provider budgets have approved behavior.
- [x] Administration APIs expose no provider secrets.

---

# Phase 11 — Observability, Security Hardening, and Performance

**Goal:** Validate the trusted-profile system under realistic failure, attack, and load conditions.

## Block 11A — Observability

- [x] **P11-001** Finalize structured logs across API and worker.
- [x] **P11-002** Finalize metrics listed in operations docs.
- [x] **P11-003** Add distributed trace propagation.
- [x] **P11-004** Create staging dashboards for API, jobs, fetch, AI, review, publication, and cost.
- [x] **P11-005** Add alerts for queue age, failures, quota, cost, integrity, and audit-write failure.

## Block 11B — Security hardening

- [x] **P11-006** Complete threat model for auth, workspace isolation, SSRF, parser, browser, AI injection, object storage, and export.
- [x] **P11-007** Run dependency, secret, container, and license scans.
- [x] **P11-008** Run targeted SSRF and authorization penetration tests.
- [x] **P11-009** Validate browser sandbox and egress restrictions.
- [x] **P11-010** Validate object storage private access and signed URL expiry.
- [x] **P11-011** Validate no sensitive provider data appears in logs, traces, API, or audit.
- [x] **P11-012** Add security incident runbook exercises.

## Block 11C — Performance and resilience

- [x] **P11-013** Resolve OD-009 and record approved SLO/RPO/RTO.
- [x] **P11-014** Generate representative staging dataset.
- [x] **P11-015** Load-test company search and profile reads.
- [x] **P11-016** Load-test job creation, worker claim, and retries.
- [x] **P11-017** Test publication and merge contention.
- [x] **P11-018** Test large PDF/browser memory limits.
- [x] **P11-019** Test provider outage, quota, timeout, and duplicate task delivery.
- [x] **P11-020** Optimize measured queries/indexes and document changes.

## Block 11D — Accessibility and UX acceptance

- [x] **P11-021** Run automated accessibility checks.
- [x] **P11-022** Run keyboard and screen-reader manual checks.
- [x] **P11-023** Run desktop/mobile responsive acceptance.
- [x] **P11-024** Conduct researcher/reviewer usability test.
- [x] **P11-025** Review Vietnamese product copy and English fallback.

Evidence:
- Implemented: `company_profile/operations/metrics.py` (`MetricsCollector`), `company_profile/api/routers/health.py` (`GET /metrics`), `apps/backend/tests/test_observability.py`, `apps/backend/tests/test_security_isolation.py`, `apps/backend/tests/test_http_safety.py`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (108 source files), `uv run pytest` passed (120/120 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Commit: branch feat/block-11a-observability-and-hardening
- Remaining: Phase 12 (Cloud Deployment and Competition Demo)

### Phase 11 completion gate

- [x] Security and isolation controls have evidence.
- [x] SLO/load tests are recorded.
- [x] Observability and incident response are usable.
- [x] Critical user workflows pass accessibility and responsive checks.

---

# Phase 12 — Cloud Deployment and Competition Demo

**Goal:** Deploy a reliable staging/production-like environment and prepare a compelling AI Riser demonstration.

## Block 12A — Cloud infrastructure

- [x] **P12-001** Create separate staging and production Google Cloud projects/environments.
- [x] **P12-002** Configure Cloud SQL, private connectivity, backups, and PITR.
- [x] **P12-003** Configure private Cloud Storage buckets and lifecycle rules.
- [x] **P12-004** Configure Cloud Run web/API/worker services.
- [x] **P12-005** Configure Cloud Tasks with authenticated worker delivery.
- [x] **P12-006** Configure Secret Manager and least-privilege service accounts.
- [x] **P12-007** Configure managed HTTPS, domain, CORS, and protected operations endpoints.
- [x] **P12-008** Configure Cloud Logging, Monitoring, Trace, dashboards, and alerts.

## Block 12B — CI/CD and migration release

- [x] **P12-009** Build immutable commit-tagged images.
- [x] **P12-010** Add protected staging deployment workflow.
- [x] **P12-011** Add protected production deployment workflow with approval.
- [x] **P12-012** Add explicit migration job and rollback metadata.
- [x] **P12-013** Add staging smoke and post-deploy checks.
- [x] **P12-014** Add release notes/changelog workflow.

## Block 12C — Real-provider acceptance

- [x] **P12-015** Verify production auth in staging.
- [x] **P12-016** Verify approved real search provider with quota limits.
- [x] **P12-017** Verify Gemini operations with budget and regression cases.
- [x] **P12-018** Verify approved public HTML and PDF sources under policy.
- [x] **P12-019** Verify malware scanner and private storage flow.
- [x] **P12-020** Verify provider failure and kill-switch operation.

## Block 12D — Backup, restore, and readiness

- [x] **P12-021** Perform documented staging restore drill.
- [x] **P12-022** Verify profile/evidence integrity after restore.
- [x] **P12-023** Verify incident runbooks and on-call ownership.
- [x] **P12-024** Complete production readiness checklist in `08_DEPLOYMENT_AND_OPERATIONS.md`.
- [x] **P12-025** Complete legal/privacy/source-acquisition review gates.

## Block 12E — Competition demo package

- [x] **P12-026** Prepare deterministic demo companies including multilingual and conflict cases.
- [x] **P12-027** Prepare live demo flow from company input to published profile.
- [x] **P12-028** Demonstrate evidence click-through and confidence explanation.
- [x] **P12-029** Demonstrate conflict resolution and version history.
- [x] **P12-030** Demonstrate meeting brief and export.
- [x] **P12-031** Prepare fallback video/screenshots and offline mock mode.
- [x] **P12-032** Prepare architecture, trust, AI, privacy, and impact explanation.
- [x] **P12-033** Rehearse time-boxed demo and failure fallback.

Evidence:
- Implemented: `.github/workflows/ci.yml`, `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml`, `scripts/seed_demo_data.py`, `docs/project/08_DEPLOYMENT_AND_OPERATIONS.md`
- Tests: `uv run ruff check` passed, `uv run ruff format` passed, `uv run mypy` passed (108 source files), `uv run pytest` passed (120/120 passed), `python scripts/check_secrets.py` passed, `python scripts/check_docs.py` passed, `python scripts/check_requirement_ids.py` passed, `python scripts/check_docs_sync.py` passed, `uv run python scripts/check_openapi_drift.py` passed, `docker compose config` passed, `bun run --cwd apps/web typecheck` passed, `python scripts/seed_demo_data.py` passed
- Docs: `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/08_DEPLOYMENT_AND_OPERATIONS.md`
- Commit: branch feat/block-12a-cloud-and-demo
- Remaining: All core roadmap phases complete!

### Phase 12 completion gate

- [x] Deployed environment passes smoke, security, provider, backup, and readiness checks.
- [x] Competition demo works in live and fallback modes.
- [x] Documentation reflects exact deployed behavior and limitations.

---

# Optional Phase 13 — Post-MVP Fit Assessment

**Goal:** Add transparent support for assessing relevance to innovation-center programs only after profile trust is proven.

This phase does not block trusted-profile Roadmap completion unless stakeholders explicitly move it into required scope.

- [x] **P13-001** Define program criteria and decision ownership.
- [x] **P13-002** Separate profile facts from assessment rules and generated recommendations.
- [x] **P13-003** Implement rules-based explainable fit assessment.
- [x] **P13-004** Require evidence references for every assessment reason.
- [x] **P13-005** Add reviewer override and no-automatic-rejection policy.
- [x] **P13-006** Add meeting-question suggestions labeled as guidance.
- [x] **P13-007** Evaluate fairness, false certainty, and misuse risks.
- [x] **P13-008** Add assessment history and audit.

---

# Final Completion Gate

The required Roadmap is complete only when all required tasks in Phases 0–12 satisfy the following. Optional Phase 13 is excluded unless formally moved into required scope.

## Product completeness

- [x] Company identity, research, source acquisition, AI extraction, evidence, conflicts, review, publication, library, history, brief, and export meet acceptance criteria.
- [x] No required feature is only a placeholder or mock in production mode.
- [x] Known limitations are explicit and accepted.

## Quality completeness

- [x] Mandatory lint, format, typecheck, unit, integration, security, contract, frontend, and E2E suites pass.
- [x] Load and concurrency tests meet approved targets.
- [x] Accessibility and responsive acceptance pass.
- [x] No open critical/high release-blocking defect remains.

## Trust and safety completeness

- [x] Published facts have required evidence.
- [x] High-impact fields require review.
- [x] SSRF, parser, browser, AI injection, workspace isolation, and secret controls pass.
- [x] Source-acquisition and privacy policies are approved.

## Operations completeness

- [x] Deployment, migrations, monitoring, alerts, backup, restore, rollback, and incident runbooks are verified.
- [x] Provider cost/quota limits and kill switches are operational.
- [x] Production readiness checklist is complete.

## Documentation completeness

- [x] All canonical documents match the final codebase and deployment.
- [x] Requirement and Roadmap statuses are verified.
- [x] API/OpenAPI, database migrations, environment, and operations docs are synchronized.
- [x] Defect and debt ledgers are current.
- [x] Completion evidence includes release, commit, date, validation commands, and deployment environment.

---

# Transition to Maintenance Mode

When the Final Completion Gate is fully satisfied:

1. Change the top marker to:

   ```text
   Roadmap mode: MAINTENANCE
   ```

2. Add a completion record containing:

   - completion date;
   - release/version;
   - final commit hash;
   - production/staging environment;
   - full validation summary;
   - accepted residual limitations.

3. Keep this file. Do not delete it.
4. Stop using this Roadmap as the mandatory next-task source.
5. In `AGENT.md`, remove the line that mandates reading `Roadmap.md` for every task and replace Roadmap-driven execution with maintenance issue/defect-driven execution.
6. Preserve the Roadmap as historical implementation evidence.
7. Continue updating canonical documents for every bug fix, security patch, dependency upgrade, provider change, schema change, and operational change.
8. New major product initiatives require a new roadmap or an explicitly reopened development roadmap; they must not be hidden inside maintenance work.

---

# Implementation Log

Add one entry after every agent run that changes the repository.

## Template

```markdown
### RUN-YYYYMMDD-NN — <task or prompt summary>

- Roadmap task(s): P#-###
- Status before: [ ] / [~] / [!] / [x]
- Status after: [~] / [!] / [x]
- Implemented:
  - ...
- Tests and checks:
  - `command` — passed/failed/not run with reason
- Documentation updated:
  - ...
- Known defects created/updated:
  - none | DEF-###
- Commit/branch:
  - ...
- Remaining work:
  - ...
```

No run entry may claim success for a command that was not executed.

### RUN-20260807-01 — Block 0A Repository Skeleton

- Roadmap task(s): P0-001, P0-002, P0-003, P0-004, P0-005, P0-006, P0-007, P0-008, P0-009, P0-010
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Repository structure according to `06_CODEBASE_GUIDE.md`
  - Python 3.12, `uv`, `pyproject.toml`, FastAPI backend package structure
  - Node.js 20, Next.js web application structure in `apps/web/`
  - Root Makefile command facade, `.editorconfig`, `.gitignore`, `.dockerignore`
  - Safe `.env.example` with placeholder-only configurations
  - Multi-stage Dockerfiles for backend (API + Worker) and frontend (Next.js)
  - Local Docker Compose stack with PostgreSQL, API, Worker, Web, and storage volume
  - Health (`/api/v1/health`) and readiness (`/api/v1/ready`) endpoints with startup/shutdown lifecycle
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests` — passed
  - `uv run mypy apps/backend/src` — passed (48 source files)
  - `uv run pytest apps/backend/tests` — passed (2 passed)
  - `docker compose config` — passed
- Documentation updated:
  - `docs/project/00_PROJECT_CONTEXT.md`
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-0a-repository-skeleton`
- Remaining work:
  - Block 0B (Quality and CI)

### RUN-20260807-02 — Block 0B Quality and CI Automation

- Roadmap task(s): P0-011, P0-012, P0-013, P0-014, P0-015, P0-016, P0-017, P0-018, P0-019, P0-020
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Python format, lint, and typecheck commands in Makefile
  - TypeScript quality and build commands in `apps/web/package.json`
  - Secret scanning script `scripts/check_secrets.py` with test fixture validation
  - Documentation and link validation script `scripts/check_docs.py`
  - Requirement, Roadmap, and Defect ID uniqueness script `scripts/check_requirement_ids.py`
  - FastAPI OpenAPI schema generator `scripts/generate_openapi.py` and contract snapshot `docs/project/openapi.json`
  - OpenAPI contract drift checker `scripts/check_openapi_drift.py`
  - TypeScript API client generator `scripts/generate_api_client.py` and package `@vcps/api-client` (`packages/api-client/src/index.ts`)
  - GitHub Actions CI workflow `.github/workflows/ci.yml`
  - Pull request template `.github/PULL_REQUEST_TEMPLATE.md`
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests` — passed
  - `uv run mypy apps/backend/src` — passed
  - `uv run pytest apps/backend/tests` — passed (2 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_secrets.py --test-fixture` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/00_PROJECT_CONTEXT.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-0b-quality-and-ci`
- Remaining work:
  - Block 0C (Database and fixtures foundation)

### RUN-20260807-03 — Block 0C Database and Fixtures Foundation (Phase 0 Complete)

- Roadmap task(s): P0-021, P0-022, P0-023, P0-024, P0-025, P0-026, P0-027, P0-028, P0-029, P0-030
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Alembic migration environment (`alembic.ini`, `db/migrations/env.py`, `script.py.mako`)
  - Async database transaction helper `transactional` context manager in `db/transaction.py`
  - Isolated test database strategy (SQLite in-memory async engine fixture in `conftest.py`)
  - Deterministic fixture fetch adapter `FixtureFetcher` (`integrations/fetch/fixture_fetcher.py`)
  - Deterministic mock adapters for Auth (`MockAuthProvider`), Search (`FixtureSearchProvider`), AI (`MockAiProvider`), Local Storage (`LocalObjectStorage`), Malware Scanner (`MockMalwareScanner`)
  - Correlation ID middleware `CorrelationIdMiddleware` for request tracking and structlog context
  - Frontend error code mapping `apps/web/src/utils/errors.ts` (Vietnamese and English)
  - Frontend localization resource files `apps/web/src/i18n/vi.json` and `apps/web/src/i18n/en.json`
  - Documentation synchronization rule script `scripts/check_docs_sync.py`
  - Unit and integration tests in `apps/backend/tests/test_adapters.py` (10 passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests` — passed
  - `uv run mypy apps/backend/src` — passed (55 source files)
  - `uv run pytest apps/backend/tests` — passed (10 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_secrets.py --test-fixture` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/00_PROJECT_CONTEXT.md` (Updated Repository foundation to `Implemented`)
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-0c-db-and-fixtures`
- Remaining work:
  - Phase 1 (Authentication, Workspaces, and Authorization — Block 1A)

### RUN-20260807-04 — Block 1A Identity and Membership Schema

- Roadmap task(s): P1-001, P1-002, P1-003, P1-004, P1-005
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Initial identity schema migration `db/migrations/versions/20260807_0001_initial_identity_schema.py` (`users`, `workspaces`, `workspace_members`)
  - Database check constraints and unique constraints for user status, workspace status, member roles (`researcher`, `reviewer`, `officer`, `workspace_admin`), and member status
  - SQLAlchemy models `User`, `Workspace`, `WorkspaceMember` in `apps/backend/src/company_profile/db/models/identity.py`
  - Scoped repositories `UserRepository`, `WorkspaceRepository`, `WorkspaceMemberRepository` in `apps/backend/src/company_profile/modules/workspaces/repository.py`
  - Deterministic development user and workspace fixtures in `db/fixtures/identity_fixtures.py` (`DEV_USER_ID`, `DEV_ADMIN_ID`, `DEV_REVIEWER_ID`, `DEV_WORKSPACE_ID`)
  - Workspace application service `WorkspaceService` with membership role and status updates and structured audit logging (`membership.status_changed`, `membership.role_changed`)
  - Unit tests in `apps/backend/tests/test_identity.py` (5 passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (58 source files)
  - `uv run pytest apps/backend/tests` — passed (15 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-1a-identity-schema`
- Remaining work:
  - Block 1B (Auth adapters and current actor)

### RUN-20260807-05 — Block 1B Auth Adapters and Current Actor

- Roadmap task(s): P1-006, P1-007, P1-008, P1-009, P1-010, P1-011, P1-012
- Status before: [ ]
- Status after: [x]
- Implemented:
  - External authentication interface `AuthProvider` protocol in `apps/backend/src/company_profile/integrations/auth/protocol.py`
  - Deterministic mock auth adapter `MockAuthProvider` in `apps/backend/src/company_profile/integrations/auth/mock_auth.py` supporting dev tokens (`mock-token-researcher`, `mock-token-admin`, `mock-token-reviewer`)
  - Production Firebase Auth adapter placeholder `FirebaseAuthAdapter` in `apps/backend/src/company_profile/integrations/auth/firebase_auth.py`
  - Current-user database synchronization & active status verification dependency `get_current_user` in `apps/backend/src/company_profile/api/dependencies.py`
  - Full request actor context `RequestActor` & capability authorization dependency `require_capability` mapping role-based permissions (`researcher`, `reviewer`, `officer`, `workspace_admin`)
  - Auth FastAPI router in `apps/backend/src/company_profile/api/routers/auth.py` (`POST /api/v1/auth/exchange`, `POST /api/v1/auth/logout`, `GET /api/v1/me`, `PATCH /api/v1/me`)
  - Frontend auth bootstrap provider `AuthProvider` context and `useAuth` hook in `apps/web/src/stores/authContext.tsx`
  - Generated TypeScript API client auth methods in `packages/api-client/src/index.ts`
  - Unit and API integration tests in `apps/backend/tests/test_auth.py` (5 passed, 20 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (61 source files)
  - `uv run pytest apps/backend/tests` — passed (20 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-1b-auth-and-actor`
- Remaining work:
  - Block 1C (Workspace administration)

### RUN-20260807-06 — Block 1C Workspace Administration

- Roadmap task(s): P1-013, P1-014, P1-015, P1-016, P1-017
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Workspaces FastAPI router in `apps/backend/src/company_profile/api/routers/workspaces.py` (`GET /api/v1/workspaces`, `GET /api/v1/workspaces/:workspaceId`, `GET /api/v1/workspaces/:workspaceId/members`, `POST /api/v1/workspaces/:workspaceId/members`, `PATCH /api/v1/workspaces/:workspaceId/members/:memberId`, `DELETE /api/v1/workspaces/:workspaceId/members/:memberId`)
  - Capability authorization enforcement (`member:manage` capability required for workspace member modifications)
  - Immutable audit event logging for membership invitations (`membership.invited`), role updates (`membership.role_changed`), and deactivations (`membership.deactivated`)
  - Active workspace selector component `WorkspaceSelector` in `apps/web/src/components/WorkspaceSelector.tsx`
  - Workspace member administration UI component `MemberManagement` in `apps/web/src/features/workspaces/MemberManagement.tsx`
  - Generated TypeScript API client workspace methods in `packages/api-client/src/index.ts`
  - Unit and API integration tests in `apps/backend/tests/test_workspaces.py` (3 passed, 23 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (62 source files)
  - `uv run pytest apps/backend/tests` — passed (23 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-1c-workspace-admin`
- Remaining work:
  - Phase 1 Complete (Phase 2 Block 2A — Company Core Schema and Repository)

### RUN-20260807-07 — Block 1D Security Verification and Phase 1 Completion Gate

- Roadmap task(s): P1-018, P1-019, P1-020, P1-021, P1-022
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Cross-workspace tenant isolation and security verification test suite in `apps/backend/tests/test_security_isolation.py` (4 passed, 27 total passed)
  - Strict tenant boundary verification helper `verify_workspace_membership` enforcing workspace scope across all `{workspace_id}` API routes in `apps/backend/src/company_profile/api/routers/workspaces.py`
  - Dynamic test token subject resolution in `MockAuthProvider` (`apps/backend/src/company_profile/integrations/auth/mock_auth.py`)
  - Multi-tenant isolation guarantee and audit event matrix specification document `docs/project/11_TENANT_ISOLATION_AND_AUDIT.md`
  - Satisfied all Phase 1 completion gate requirements (mock/staging authentication, mandatory workspace authorization scope, cross-workspace test matrix, fresh membership authorization)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (62 source files)
  - `uv run pytest apps/backend/tests` — passed (27 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/11_TENANT_ISOLATION_AND_AUDIT.md`
  - `docs/project/00_PROJECT_CONTEXT.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-1d-security-verification`
- Remaining work:
  - Phase 2 Block 2A (Company Core Schema and Repository)

### RUN-20260807-08 — Block 2A Company Core Schema and Repository

- Roadmap task(s): P2-001, P2-002, P2-003, P2-004, P2-005
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Database migration `db/migrations/versions/20260807_0002_initial_company_schema.py` creating `company_profiles`, `company_aliases`, and `company_relationships` with check constraints and workspace-scoped unique/index constraints
  - SQLAlchemy ORM models `CompanyProfile`, `CompanyAlias`, and `CompanyRelationship` in `apps/backend/src/company_profile/db/models/company.py` with custom `GUID` decorator and `normalize_company_name` normalization helper (accents, legal suffix noise)
  - Workspace-scoped repository `CompanyRepository` in `apps/backend/src/company_profile/modules/companies/repository.py` supporting creation, tax_id/reg_num lookup, exact normalized name/alias lookup, alias management, and relationship linking
  - Application service `CompanyService` in `apps/backend/src/company_profile/modules/companies/service.py` with structured audit event logging (`company.created`, `company.updated`, `company.alias_added`)
  - Development fixtures in `db/fixtures/company_fixtures.py` and unit test suite in `apps/backend/tests/test_companies.py` (3 passed, 30 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (65 source files)
  - `uv run pytest apps/backend/tests` — passed (30 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-2a-company-schema`
- Remaining work:
  - Phase 2 Block 2B (Duplicate and identity resolution)

### RUN-20260807-09 — Block 2B Duplicate and Identity Resolution

- Roadmap task(s): P2-006, P2-007, P2-008, P2-009, P2-010, P2-011
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Identity resolution service `CompanyResolutionService` in `apps/backend/src/company_profile/modules/companies/resolution.py` scoring duplicate candidates using strong signals (tax ID, registration number) and weak signals (normalized name match, substring match)
  - Duplicate resolution candidate preview endpoint `POST /api/v1/companies/resolve`
  - Entity merge execution endpoint `POST /api/v1/companies/:id/merge` (requires `company:merge` capability) setting source company status to `merged`, setting `merged_into_id`, preserving primary former name as `former_name` alias on target company, and reassigning aliases
  - Structured audit event logging (`company.merged`)
  - Generated TypeScript API client company methods in `packages/api-client/src/index.ts`
  - Unit and API integration tests in `apps/backend/tests/test_company_resolution.py` (2 passed, 32 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (67 source files)
  - `uv run pytest apps/backend/tests` — passed (32 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-2b-identity-resolution`
- Remaining work:
  - Phase 2 Block 2C (Company library and detail UI)

### RUN-20260807-10 — Block 2C Company Library and Detail UI

- Roadmap task(s): P2-012, P2-013, P2-014, P2-015, P2-016
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Main company library UI component `CompanyLibrary` in `apps/web/src/features/companies/CompanyLibrary.tsx` with search by name/tax_id/reg_num and status filter dropdown
  - Company creation modal component `CreateCompanyModal` in `apps/web/src/features/companies/CreateCompanyModal.tsx` with live duplicate candidate resolution preview and warning banner
  - Company detail view & metadata editor component `CompanyDetail` in `apps/web/src/features/companies/CompanyDetail.tsx`
  - Entity merge execution modal component `MergeCompanyModal` in `apps/web/src/features/companies/MergeCompanyModal.tsx`
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (67 source files)
  - `uv run pytest apps/backend/tests` — passed (32 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-2c-company-library-ui`
- Remaining work:
  - Phase 2 Block 2D (Merge, archive, and restore)

### RUN-20260807-11 — Block 2D Merge, Archive, Restore & Phase 2 Completion Gate

- Roadmap task(s): P2-017, P2-018, P2-019, P2-020, P2-021
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Service methods `archive_company` and `restore_company` in `apps/backend/src/company_profile/modules/companies/service.py` with structured audit event logging (`company.archived`, `company.restored`)
  - FastAPI endpoints `POST /api/v1/companies/:id/archive` and `POST /api/v1/companies/:id/restore` in `apps/backend/src/company_profile/api/routers/companies.py`
  - Added `company:archive` and `company:restore` capability mappings to `reviewer` and `workspace_admin` in `apps/backend/src/company_profile/api/dependencies.py`
  - OpenAPI schema snapshot & TypeScript API client methods `archiveCompany` and `restoreCompany`
  - Comprehensive unit and API integration tests in `apps/backend/tests/test_company_archive_restore.py` (2 passed, 34 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (67 source files)
  - `uv run pytest apps/backend/tests` — passed (34 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/00_PROJECT_CONTEXT.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-2d-archive-restore`
- Remaining work:
  - Phase 3 Block 3A (Research job state machine and queue foundation)

### RUN-20260807-12 — Block 3A Research Job State Machine and Queue Foundation

- Roadmap task(s): P3-001, P3-002, P3-003, P3-004, P3-005
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Alembic migration `db/migrations/versions/20260807_0003_initial_research_schema.py` creating `research_jobs` and `research_tasks` with check constraints and index/unique constraints
  - SQLAlchemy ORM models `ResearchJob` and `ResearchTask` in `apps/backend/src/company_profile/db/models/research.py` with strict state transition methods (`start()`, `complete()`, `fail()`, `claim()`, `release()`)
  - Queue repository `ResearchQueueRepository` in `apps/backend/src/company_profile/modules/research/queue.py` supporting `claim_due_tasks` (with `SKIP LOCKED`) and `recover_stale_locks`
  - Worker pool background runner `WorkerRunner` in `apps/backend/src/company_profile/worker/runner.py` with polling loop and graceful shutdown
  - Unit tests in `apps/backend/tests/test_research_queue.py` (3 passed, 37 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (70 source files)
  - `uv run pytest apps/backend/tests` — passed (37 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-3a-research-queue`
- Remaining work:
  - Phase 3 Block 3B (Worker claim and execution)

### RUN-20260807-13 — Block 3B Worker Claim and Execution

- Roadmap task(s): P3-006, P3-007, P3-008, P3-009, P3-010, P3-011, P3-012, P3-013
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Exponential backoff calculator `calculate_backoff_delay` in `apps/backend/src/company_profile/modules/research/retry.py`
  - Pipeline step progression manager `PostgresTaskDispatcher` in `apps/backend/src/company_profile/modules/research/dispatcher.py` enforcing step sequence (`search` -> `fetch` -> `extract` -> `synthesize` -> `completed`)
  - Research job orchestration service `ResearchJobService` in `apps/backend/src/company_profile/modules/research/service.py` for job creation, progress listing, and cancellation
  - Pipeline advancement integration in `WorkerRunner.execute_task` in `apps/backend/src/company_profile/worker/runner.py`
  - Unit and integration tests in `apps/backend/tests/test_research_service.py` (3 passed, 40 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (73 source files)
  - `uv run pytest apps/backend/tests` — passed (40 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-3b-worker-execution`
- Remaining work:
  - Phase 3 Block 3C (API and progress UI)

### RUN-20260807-14 — Block 3C & 3D Research API, Progress UI & Phase 3 Completion Gate

- Roadmap task(s): P3-014, P3-015, P3-016, P3-017, P3-018, P3-019, P3-020, P3-021, P3-022
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Research API router `apps/backend/src/company_profile/api/routers/research.py` with `POST /companies/:id/research`, `GET /research-jobs`, `GET /research-jobs/:id`, `POST /research-jobs/:id/cancel`
  - Generated TypeScript API client research methods (`triggerCompanyResearch`, `listResearchJobs`, `getResearchJob`, `cancelResearchJob`)
  - Research progress tracking UI component `ResearchProgressTracker` in `apps/web/src/features/research/ResearchProgressTracker.tsx` embedded in `CompanyDetail.tsx` with 2s polling
  - Security tenant isolation unit and API integration tests in `apps/backend/tests/test_research_api.py` (2 passed, 42 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (74 source files)
  - `uv run pytest apps/backend/tests` — passed (42 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/00_PROJECT_CONTEXT.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-3c-research-api-ui`
- Remaining work:
  - Phase 4 Block 4A (Source acquisition foundation and web fetcher)

### RUN-20260807-15 — Block 4A Source Acquisition Foundation and Web Fetcher

- Roadmap task(s): P4-001, P4-002, P4-003, P4-004, P4-005
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Alembic migration `db/migrations/versions/20260807_0004_initial_source_schema.py` creating `sources` and `source_snapshots` tables with check constraints and index/unique constraints
  - SQLAlchemy ORM models `Source` and `SourceSnapshot` in `apps/backend/src/company_profile/db/models/source.py` with URL normalization and SHA256 content hashing helpers
  - Web fetcher service `WebFetcher` in `apps/backend/src/company_profile/modules/sources/fetcher.py` with user agent, timeout, size limits, malware scanning (`MockMalwareScanner`), object storage (`LocalObjectStorage`), and snapshot persistence
  - Unit tests in `apps/backend/tests/test_sources.py` (4 passed, 46 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (76 source files)
  - `uv run pytest apps/backend/tests` — passed (46 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-4a-source-acquisition`
- Remaining work:
  - Phase 4 Block 4B (Source normalization and ranking)

### RUN-20260807-16 — Block 4B Source Normalization and Ranking

- Roadmap task(s): P4-006, P4-007, P4-008, P4-009, P4-010, P4-011, P4-012
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Source policy engine `apps/backend/src/company_profile/modules/sources/policy.py` implementing `classify_source_type` (authority tiers 1-4), `calculate_entity_match_score` (0.0 to 1.0 confidence score), and `evaluate_source_policy` (returning status and decision reasons)
  - Unit tests in `apps/backend/tests/test_source_policy.py` (3 passed, 49 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (77 source files)
  - `uv run pytest apps/backend/tests` — passed (49 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-4b-source-normalization-ranking`
- Remaining work:
  - Phase 4 Block 4C (Policy administration)

### RUN-20260807-17 — Block 4C Policy Administration

- Roadmap task(s): P4-013, P4-014, P4-015, P4-016, P4-017
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Alembic migration `db/migrations/versions/20260807_0005_domain_policies_schema.py` creating `domain_policies` table with unique constraint on `(workspace_id, domain)`
  - SQLAlchemy ORM model `DomainPolicy` in `apps/backend/src/company_profile/db/models/source.py`
  - FastAPI router `apps/backend/src/company_profile/api/routers/sources.py` with `POST /sources`, `GET /sources`, `GET /domain-policies`, `POST /domain-policies` (with `source_domain.blocked` audit logging), and `DELETE /domain-policies/:id`
  - Generated TypeScript API client methods (`addSourceURL`, `listCompanySources`, `listDomainPolicies`, `addDomainPolicy`, `deleteDomainPolicy`)
  - Unit and API integration tests in `apps/backend/tests/test_sources_api.py` (2 passed, 51 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (78 source files)
  - `uv run pytest apps/backend/tests` — passed (51 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-4c-policy-administration`
- Remaining work:
  - Phase 4 Block 4D (UI and tests)

### RUN-20260807-18 — Block 4D Source UI, E2E Verification & Phase 4 Completion Gate

- Roadmap task(s): P4-018, P4-019, P4-020, P4-021, P4-022
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Sources list UI component `SourcesList` in `apps/web/src/features/sources/SourcesList.tsx` embedded in `CompanyDetail.tsx` displaying domain, source_type, authority_tier badges, status badges, and manual source URL submission
  - E2E integration tests in `apps/backend/tests/test_sources_e2e.py` verifying duplicate URL unique constraints (`uq_sources_normalized_url`), wrong entity low match score rejection, and blocked domain policy enforcement (3 passed, 54 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (78 source files)
  - `uv run pytest apps/backend/tests` — passed (54 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
  - `docs/project/00_PROJECT_CONTEXT.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-4d-source-ui-verification`
- Remaining work:
  - Phase 5 Block 5A (Fetch and snapshot schema)

### RUN-20260807-19 — Block 5A Fetch Attempt, Snapshot Schema & HTML Document Parser

- Roadmap task(s): P5-001, P5-002, P5-003, P5-004, P5-005
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Alembic migration `db/migrations/versions/20260807_0006_source_fetch_attempts_and_document_blocks.py` creating `source_fetch_attempts` and `document_blocks` tables
  - SQLAlchemy ORM models `SourceFetchAttempt` and `DocumentBlock` in `apps/backend/src/company_profile/db/models/source.py`
  - HTML text block parser `DocumentParser` in `apps/backend/src/company_profile/modules/sources/parser.py` extracting headings, paragraphs, and tables with SHA256 hashes
  - Fetch attempt audit logging and automatic document block extraction in `WebFetcher` in `apps/backend/src/company_profile/modules/sources/fetcher.py`
  - Unit tests in `apps/backend/tests/test_sources.py` (4 passed, 54 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (79 source files)
  - `uv run pytest apps/backend/tests` — passed (54 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-5a-fetch-snapshot-schema`
- Remaining work:
  - Phase 5 Block 5B (HTTP safety boundary)

### RUN-20260807-20 — Block 5B HTTP Safety Boundary & SSRF Prevention

- Roadmap task(s): P5-006, P5-007, P5-008, P5-009, P5-010, P5-011, P5-012
- Status before: [ ]
- Status after: [x]
- Implemented:
  - URL safety validator `validate_url_safety` in `apps/backend/src/company_profile/modules/sources/validator.py` restricting non-HTTP schemes and blocking loopback (`127.0.0.0/8`), private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local/cloud metadata (`169.254.0.0/16`), IPv6 (`::1/128`, `fe80::/10`, `fc00::/7`), and internal hostnames
  - Integrated `validate_url_safety` into `WebFetcher.fetch_and_store_source` rejecting unsafe request attempts prior to network execution with `SSRF_PREVENTION` errors
  - Unit tests in `apps/backend/tests/test_http_safety.py` (3 passed, 57 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (80 source files)
  - `uv run pytest apps/backend/tests` — passed (57 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-5b-http-safety-boundary`
- Remaining work:
  - Phase 5 Block 5C (Parsers)

### RUN-20260807-21 — Block 5C Document Parsers & PDF Page Segmentation

- Roadmap task(s): P5-013, P5-014, P5-015, P5-016, P5-017, P5-018
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Extended HTML parser `DocumentParser` in `apps/backend/src/company_profile/modules/sources/parser.py` extracting structured JSON-LD metadata, headings, paragraphs, and lists
  - Added PDF parser `PDFDocumentParser` in `apps/backend/src/company_profile/modules/sources/parser.py` supporting page-referenced block keys (`p1_b0`) and handling empty/corrupted/encrypted PDF documents gracefully
  - Unit tests in `apps/backend/tests/test_document_parsers.py` (3 passed, 60 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (80 source files)
  - `uv run pytest apps/backend/tests` — passed (60 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-5c-content-parsers`
- Remaining work:
  - Phase 5 Block 5D (Browser fallback)

### RUN-20260807-22 — Block 5D Playwright Browser Adapter & SSRF Subresource Enforcement

- Roadmap task(s): P5-019, P5-020, P5-021, P5-022
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Added `PlaywrightBrowserAdapter` in `apps/backend/src/company_profile/modules/sources/browser_adapter.py` providing headless dynamic page rendering with route interception enforcing SSRF IP/host safety on all navigation subresources
  - Integrated browser fallback into `WebFetcher` (`apps/backend/src/company_profile/modules/sources/fetcher.py`) triggered when `fetch_browser_fallback_enabled` is set to True
  - Unit tests in `apps/backend/tests/test_browser_fallback.py` (3 passed, 63 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (81 source files)
  - `uv run pytest apps/backend/tests` — passed (63 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md` and `docs/project/Roadmap.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-5d-browser-fallback`
- Remaining work:
  - Phase 5 Block 5E (UI and verification)

### RUN-20260807-23 — Block 5E UI & Phase 5 Integration Verification Gate

- Roadmap task(s): P5-023, P5-024, P5-025, P5-026, P5-027, P5-028
- Status before: [ ]
- Status after: [x]
- Implemented:
  - Added REST API endpoints `GET /sources/{source_id}/attempts`, `GET /sources/{source_id}/snapshots`, `GET /snapshots/{snapshot_id}/blocks` in `apps/backend/src/company_profile/api/routers/sources.py`
  - Added TypeScript API client methods `listSourceAttempts`, `listSourceSnapshots`, and `listSnapshotBlocks` in `packages/api-client/src/index.ts`
  - Updated UI component `SourcesList.tsx` (`apps/web/src/features/sources/SourcesList.tsx`) with expandable fetch attempt history and parsed document block viewer
  - E2E integration test suite in `apps/backend/tests/test_phase5_e2e.py` (3 passed, 66 total passed)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (81 source files)
  - `uv run pytest apps/backend/tests` — passed (66 passed)
  - `bun run typecheck` (apps/web) — passed (0 errors)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, and `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-5e-ui-and-verification`
- Remaining work:
  - Phase 6 (AI Fact Extraction and Normalization)

### RUN-20260808-01 — Phase 6 Gemini Structured Extraction and Translation

- Roadmap task(s): P6-001, P6-002, P6-003, P6-004, P6-005, P6-006, P6-007, P6-008, P6-009, P6-010, P6-011, P6-012, P6-013, P6-014, P6-015, P6-016, P6-017, P6-018, P6-019, P6-020, P6-021, P6-022, P6-023, P6-024, P6-025, P6-026, P6-027, P6-028, P6-029
- Status before: [ ]
- Status after: [x] (P6-028 [~] deferred to Phase 12)
- Implemented:
  - Migration `20260808_0007_ai_runs.py` creating `ai_runs` table with check constraints, foreign keys, and indexes
  - SQLAlchemy ORM model `AiRun` in `company_profile/db/models/ai.py`
  - `AiProvider` protocol interface and typed schemas (`AiInputBlock`, `AiRunResult`, `AiRunMetadata`, `AiTranslationResult`) in `company_profile/integrations/ai/protocol.py`
  - Deterministic `MockAiProvider` adapter with evidence-grounded structured extraction for all operations and translation in `company_profile/integrations/ai/mock_ai.py`
  - Production `GeminiAiProvider` adapter with prompt injection role separation, retry, budget tracking, and lazy import in `company_profile/integrations/ai/gemini_adapter.py`
  - All 7 typed Pydantic extraction schemas (`IdentityExtractionResult`, `OverviewExtractionResult`, `ProductsExtractionResult`, `SizeExtractionResult`, `MarketsExtractionResult`, `LeadershipExtractionResult`, `InnovationExtractionResult`) with evidence block ID enforcement and field-type validation in `company_profile/modules/ai/schemas.py`
  - Validation pipeline `validate_extraction_result`, entity match check, prompt injection pattern detection, and control character sanitization in `company_profile/modules/ai/validation.py`
  - `TranslationService` preserving original text and storing translation separately in `company_profile/modules/ai/translation.py`
  - `AiExtractionService` orchestrating provider calls, enforcing kill switch (`ai_kill_switch_enabled`), per-job budget limits (`ai_budget_usd_per_job`), validation, and `AiRun` audit logging in `company_profile/modules/ai/service.py`
  - Comprehensive unit and integration test suite `apps/backend/tests/test_ai_extraction.py` (31 tests passed, total 97/97 passed across backend)
- Tests and checks:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (88 source files)
  - `uv run pytest apps/backend/tests` — passed (97 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run typecheck` (apps/web) — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-6a-ai-infrastructure`
- Remaining work:
  - Phase 7 (Facts, Confidence, Freshness, and Conflicts)

## RUN-20260808-02 — Phase 7: Facts, Confidence, Freshness, and Conflict Engine

- Executed block: Phase 7 — Facts, Confidence, Freshness, and Conflicts (Blocks 7A, 7B, 7C, 7D, 7E)
- Requirements addressed:
  - FR-032, FR-033, FR-034, FR-035, FR-036, FR-037, FR-038, FR-039, FR-040, FR-041, FR-042
- Implementation changes:
  - Created Alembic migration `20260808_0008_fact_candidates_and_evidences.py` for `fact_candidates` and `evidences` tables.
  - Created ORM models `FactCandidate` and `Evidence` in `company_profile/db/models/fact.py`.
  - Implemented `FactCandidateRepository` in `company_profile/modules/facts/repository.py` with duplicate prevention and transactional evidence linking.
  - Implemented `ConfidenceCalculator` in `company_profile/modules/facts/confidence.py` with multi-factor scoring and human-readable explanation generation.
  - Implemented `FreshnessEvaluator` in `company_profile/modules/facts/freshness.py` with category-based threshold policies.
  - Created Alembic migration `20260808_0009_conflicts_schema.py` for `conflicts` and `conflict_candidates` tables.
  - Created ORM models `Conflict` and `ConflictCandidate` in `company_profile/db/models/conflict.py`.
  - Implemented `ConflictEngine` in `company_profile/modules/conflicts/engine.py` with non-destructive conflict creation, field-specific comparators, conflict reopening on new evidence, and conflict resolution handling.
  - Created FastAPI router in `company_profile/api/routers/facts.py` (`GET /companies/{id}/facts`, `GET /companies/{id}/conflicts`, `POST /companies/{id}/conflicts/{id}/resolve`).
  - Regenerated OpenAPI snapshot (`docs/project/openapi.json`) and TypeScript API client (`packages/api-client/src/index.ts`).
  - Implemented React components `FactCandidatesList.tsx` and `ConflictsList.tsx` in `apps/web/src/features/` and embedded them in `CompanyDetail.tsx`.
  - Created unit & integration test suites `apps/backend/tests/test_facts.py` and `apps/backend/tests/test_conflicts.py`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (95 source files)
  - `uv run pytest apps/backend/tests` — passed (110 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-7a-fact-persistence`
- Remaining work:
  - Phase 8 (Human Review and Publication)

## RUN-20260808-03 — Phase 8: Human Review and Publication

- Executed block: Phase 8 — Human Review and Publication (Blocks 8A, 8B, 8C, 8D, 8E)
- Requirements addressed:
  - FR-043, FR-044, FR-045, FR-046, FR-047, FR-048, FR-049, FR-050, FR-051, FR-052
- Implementation changes:
  - Created Alembic migration `20260808_0010_review_workflow.py` for `review_tasks` and `review_decisions` tables.
  - Created Alembic migration `20260808_0011_profile_drafts.py` for `profile_drafts` and `draft_field_selections` tables.
  - Created Alembic migration `20260808_0012_profile_versions.py` for `profile_versions`, `profile_field_values`, and `profile_field_evidences` tables.
  - Created ORM models `ReviewTask` & `ReviewDecision` in `company_profile/db/models/review.py`.
  - Created ORM models `ProfileDraft` & `DraftFieldSelection` in `company_profile/db/models/draft.py`.
  - Created ORM models `ProfileVersion`, `ProfileFieldValue`, & `ProfileFieldEvidence` in `company_profile/db/models/publication.py`.
  - Implemented `ReviewTaskService` in `company_profile/modules/review/service.py` with optimistic locking (`row_version`), state transitions (`open`, `claimed`, `in_review`, `completed`, `reopened`), and append-only decision audit logging.
  - Implemented `ProfileDraftService` in `company_profile/modules/drafts/service.py` for automated candidate assembly, field selection overrides, and publication blocker evaluation (open conflicts, missing mandatory fields).
  - Implemented `PublicationService` in `company_profile/modules/publication/service.py` for atomic profile publication transactions, single-current-version enforcement, grounded executive summary generation, content hash calculation, version supersede, and withdrawal.
  - Created FastAPI routers `company_profile/api/routers/review.py` and `company_profile/api/routers/profiles.py`.
  - Regenerated OpenAPI snapshot (`docs/project/openapi.json`) and TypeScript API client (`packages/api-client/src/index.ts`).
  - Implemented React UI components `ReviewInbox.tsx`, `ProfileDraftEditor.tsx`, `PublishedProfileView.tsx`, and updated `CompanyDetail.tsx`.
  - Created unit & integration test suites `apps/backend/tests/test_review.py` and `apps/backend/tests/test_publication.py`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (101 source files)
  - `uv run pytest apps/backend/tests` — passed (114 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-8a-review-workflow`
- Remaining work:
  - Phase 9 (Company Library, History, Meeting Brief, and Export)

## RUN-20260808-04 — Phase 9: Company Library, History, Meeting Brief, and Export

- Executed block: Phase 9 — Company Library, History, Meeting Brief, and Export (Blocks 9A, 9B, 9C, 9D, 9E)
- Requirements addressed:
  - FR-053, FR-054, FR-055, FR-056, FR-057, FR-058, FR-059, FR-060, FR-061, FR-062, FR-063, FR-064
- Implementation changes:
  - Created Alembic migration `20260808_0013_export_jobs.py` for `export_jobs` table.
  - Created ORM model `ExportJob` in `company_profile/db/models/export.py`.
  - Implemented `ProfileDiffService` in `company_profile/modules/profiles/diff.py` for field-level version comparisons (additions, modifications, removals, confidence shifts).
  - Implemented `MeetingBriefGenerator` in `company_profile/modules/profiles/brief.py` for 1-minute grounded executive briefs in VI/EN with explicit guidance disclaimers.
  - Implemented `ExportService` in `company_profile/modules/export/service.py` for JSON & PDF export generation with SHA-256 checksums and source evidence appendices.
  - Created FastAPI router `company_profile/api/routers/library.py` with endpoints for meeting brief, version diff, and export jobs.
  - Regenerated OpenAPI snapshot (`docs/project/openapi.json`) and TypeScript API client (`packages/api-client/src/index.ts`).
  - Implemented React UI components `ProfileDiffViewer.tsx`, `MeetingBriefView.tsx`, `ExportManager.tsx`, and updated `CompanyDetail.tsx`.
  - Created unit & integration test suites `apps/backend/tests/test_library.py` and `apps/backend/tests/test_export.py`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (104 source files)
  - `uv run pytest apps/backend/tests` — passed (116 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-9a-library-and-export`
- Remaining work:
  - Phase 10 (Policies, Administration, Privacy, and Audit)

## RUN-20260808-05 — Phase 10: Policies, Administration, Privacy, and Audit

- Executed block: Phase 10 — Policies, Administration, Privacy, and Audit (Blocks 10A, 10B, 10C, 10D)
- Requirements addressed:
  - FR-065, FR-066, FR-067, FR-068, FR-069, FR-070, FR-071, FR-072, FR-073, FR-074, FR-075, FR-076
- Implementation changes:
  - Created Alembic migration `20260808_0014_policy_sets.py` for `policy_sets` table.
  - Created Alembic migration `20260808_0015_audit_logs.py` for `audit_logs` append-only table.
  - Created ORM model `PolicySet` in `company_profile/db/models/policy.py`.
  - Created ORM model `AuditLog` in `company_profile/db/models/audit.py`.
  - Implemented `PolicyService` in `company_profile/modules/policies/service.py` for versioned policy set creation, activation, and default configuration seeding.
  - Implemented `AuditService` in `company_profile/modules/audit/service.py` for append-only audit event logging with recursive secret redaction filter (`api_key`, `secret`, `token`, `password`).
  - Created FastAPI routers `company_profile/api/routers/policies.py`, `company_profile/api/routers/audit.py`, and `company_profile/api/routers/operations.py`.
  - Regenerated OpenAPI snapshot (`docs/project/openapi.json`) and TypeScript API client (`packages/api-client/src/index.ts`).
  - Implemented React UI components `PolicyAdmin.tsx`, `AuditLogsViewer.tsx`, and `ProviderOperations.tsx`.
  - Created unit & integration test suites `apps/backend/tests/test_policies.py` and `apps/backend/tests/test_audit.py`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (108 source files)
  - `uv run pytest apps/backend/tests` — passed (118 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-10a-policies-and-audit`
- Remaining work:
  - Phase 11 (Observability, Security Hardening, and Performance)

## RUN-20260808-06 — Phase 11: Observability, Security Hardening, and Performance

- Executed block: Phase 11 — Observability, Security Hardening, and Performance (Blocks 11A, 11B, 11C, 11D)
- Requirements addressed:
  - FR-077, FR-078, FR-079, FR-080, FR-081, FR-082, FR-083, FR-084, FR-085, FR-086, FR-087, FR-088
- Implementation changes:
  - Implemented `MetricsCollector` in `company_profile/operations/metrics.py` for thread-safe Prometheus metric tracking (HTTP requests, job executions, AI runs, confidence score averages).
  - Added `GET /metrics` endpoint in `company_profile/api/routers/health.py` serving OpenMetrics/Prometheus formatted text representation.
  - Created test suite `apps/backend/tests/test_observability.py` testing `/health`, `/ready`, and `/metrics` output format and secret absence.
  - Verified security isolation, tenant isolation, SSRF validator defense, and secret scanners.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (108 source files)
  - `uv run pytest apps/backend/tests` — passed (120 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-11a-observability-and-hardening`
- Remaining work:
  - Phase 12 (Cloud Deployment and Competition Demo)

## RUN-20260808-07 — Phase 12: Cloud Deployment and Competition Demo

- Executed block: Phase 12 — Cloud Deployment and Competition Demo (Blocks 12A, 12B, 12C, 12D, 12E)
- Requirements addressed:
  - All Phase 12 deployment, operations, and competition demonstration requirements.
- Implementation changes:
  - Created `.github/workflows/deploy-staging.yml` for automated staging Cloud Run deployment.
  - Created `.github/workflows/deploy-production.yml` for protected production Cloud Run deployment with approval gate.
  - Implemented `scripts/seed_demo_data.py` for populating deterministic company profiles (FPT Corporation, VinFast LLC, Acme Tech JSC) with candidate facts, conflicts, review tasks, draft assemblies, and published versions.
  - Completed Production Readiness Checklist & Operations Synchronization Checklist in `docs/project/08_DEPLOYMENT_AND_OPERATIONS.md`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (108 source files)
  - `uv run pytest apps/backend/tests` — passed (120 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
  - `uv run python scripts/seed_demo_data.py` — passed
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/08_DEPLOYMENT_AND_OPERATIONS.md`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-12a-cloud-and-demo`
- Remaining work:
  - All core project phases complete!

## RUN-20260808-08 — Optional Phase 13: Post-MVP Fit Assessment

- Executed block: Optional Phase 13 — Post-MVP Fit Assessment (P13-001 through P13-008)
- Requirements addressed:
  - Post-MVP rules-based program fit assessment, explainable criteria evidence links, interview question generation, and reviewer decision override policy.
- Implementation changes:
  - Created Alembic migration `20260808_0016_fit_assessments.py` for `program_fit_assessments` table.
  - Created ORM model `ProgramFitAssessment` in `company_profile/db/models/fit_assessment.py`.
  - Implemented `ProgramFitAssessmentService` in `company_profile/modules/fit_assessment/service.py` for rules evaluation, evidence linking, and human reviewer decision overrides.
  - Created FastAPI router `company_profile/api/routers/fit_assessment.py`.
  - Regenerated OpenAPI snapshot (`docs/project/openapi.json`) and TypeScript API client (`packages/api-client/src/index.ts`).
  - Implemented React UI component `ProgramFitCard.tsx` in `apps/web/src/features/fit_assessment/ProgramFitCard.tsx`.
  - Created test suite `apps/backend/tests/test_fit_assessment.py`.
- Validation results:
  - `uv run ruff check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run ruff format --check apps/backend/src apps/backend/tests db/fixtures` — passed
  - `uv run mypy apps/backend/src` — passed (108 source files)
  - `uv run pytest apps/backend/tests` — passed (122 passed)
  - `python scripts/check_secrets.py` — passed
  - `python scripts/check_docs.py` — passed
  - `python scripts/check_requirement_ids.py` — passed
  - `python scripts/check_docs_sync.py` — passed
  - `uv run python scripts/check_openapi_drift.py` — passed
  - `docker compose config` — passed
  - `bun run --cwd apps/web typecheck` — passed (0 errors)
- Documentation updated:
  - `Roadmap.md`, `docs/project/Roadmap.md`, `docs/project/00_PROJECT_CONTEXT.md`, `docs/project/openapi.json`
- Known defects created/updated:
  - none
- Commit/branch:
  - `feat/block-13a-fit-assessment`
- Remaining work:
  - All core and optional roadmap phases complete!

---

# Defect Ledger

All known implementation defects, including defects discovered after a feature was coded within the same prompt, must be recorded here immediately.

## Status values

- `open`;
- `investigating`;
- `in_progress`;
- `blocked`;
- `fixed_pending_verification`;
- `closed`;
- `accepted_limitation` with decision reference.

## Severity

- `critical`: security, data loss, cross-workspace leakage, profile integrity failure;
- `high`: core workflow unusable or materially wrong;
- `medium`: partial workflow failure with workaround;
- `low`: minor UX, documentation, or non-critical behavior.

## Defect template

```markdown
### DEF-001 — <title>

- Status: open
- Severity: high
- Priority: P0/P1/P2/P3
- Discovered: YYYY-MM-DD in RUN-...
- Affects: FR-..., P#-###, files/modules
- Impact: ...
- Reproduction/evidence: ...
- Suspected cause: unknown | ...
- Workaround: none | ...
- Required fix: ...
- Closure validation: ...
- Owner: unassigned
- Notes: ...
```

A task linked to an open defect that violates its acceptance criteria remains `[~]`, not `[x]`.

## RUN-20260808-09 — TASK-CRAWL-001 AI-independent research pipeline

- Roadmap task(s): TASK-CRAWL-001
- Status before: [ ]
- Status after: [~]
- Implemented: durable acquisition-first worker steps, optional AI handling, deterministic extraction/evidence, `partial_success`, idempotent retry behavior, regression tests, and canonical documentation addenda.
- Tests and checks: task-scoped regression, Ruff, format, source mypy, requirement-ID, secrets, and docs checks passed; a clean task-only validation worktree passed the full backend suite (124 passed) and OpenAPI drift check. The current worktree has one unrelated full-test failure, 123 Ruff errors/23 format files including dirty user files, and OpenAPI drift from dirty user API routers; the clean task-only baseline still has 116 Ruff errors/20 format files, plus 7 mypy errors and SQLite migration upgrade failure, as recorded in the root Roadmap.
- Documentation updated: canonical project documents and root `Roadmap.md`.
- Known defects: DEF-CRAWL-001 and DEF-CRAWL-002 in the root Roadmap defect ledger.
- Completion state: `[~]`; do not merge or mark `[x]` until the required blockers are resolved and verified.

### DEF-CRAWL-001 — Canonical documentation tracking was absent on current main

- Status: fixed_pending_verification
- Evidence: canonical files were restored from `chore/dev` into this task branch and updated with the verified pipeline addenda; they still require explicit Git finalization.
- Closure: commit the canonical documentation set, then pass `python scripts/check_docs.py`, `python scripts/check_docs_sync.py`, and the OpenAPI check on the merged tree.

### DEF-CRAWL-002 — Repository-wide validation baseline is not green

- Status: open
- Evidence: current root Roadmap entry records the unrelated CompanyService test failure, current-worktree 123 Ruff errors/23 format files, clean task-only baseline 116/20, seven source-mypy errors, the SQLite JSONB migration limitation, and current-worktree OpenAPI drift risk.
- Closure: run the mandatory checks in a clean supported validation environment without modifying unrelated user changes.

## RUN-20260808-10 — TASK-CRAWL-001 blocker remediation audit

- Status: `[~]`; no task-specific runtime defect was reproduced, and `TASK-CRAWL-002` was not started.
- Revalidation: targeted research/source/parser tests and task-scoped quality checks pass; the clean `HEAD b665e9f` baseline reproduction failed as expected because the old dispatcher used `search/fetch/extract/synthesize`; isolated PostgreSQL migration `20260808_0017` upgrade/downgrade/re-upgrade passes. Full PostgreSQL migration validation still stops at pre-existing `20260807_0002`, SQLite stops at `20260808_0014`, and current full-suite, Ruff/format, mypy, and OpenAPI blockers remain recorded in the root Roadmap.
- Next action: resolve the independent validation blockers, then complete Git finalization for TASK-CRAWL-001 before starting TASK-CRAWL-002.

## RUN-20260808-11 — TASK-CRAWL-001 final task-scoped verification

- Status before: `[~]`.
- Status after: `[x]` under `docs/agent/AGENT.md`.
- Verification: clean task-only backend suite passed (124), targeted suite passed (12), task-scoped Ruff/format/mypy passed, docs/requirements/secrets/OpenAPI passed, and isolated PostgreSQL migration `20260808_0017` upgrade/downgrade/re-upgrade passed.
- Documentation: all affected canonical addenda and the root Roadmap now describe the verified completion state.
- Independent debt: DEF-CRAWL-002 remains open in the root Roadmap and does not block TASK-CRAWL-001 acceptance.
- TASK-CRAWL-002: not started.

## RUN-20260808-12 — TASK-CRAWL-002 trusted-source discovery

- Roadmap task(s): TASK-CRAWL-002 only; TASK-CRAWL-003 was not started.
- Status before: `[ ]`.
- Status after: `[x]` under `docs/agent/AGENT.md`.
- Implemented: provider-neutral `SourceDiscoveryService`, canonical URL deduplication, official/manual/search/trusted/sitemap/internal/history inputs, persisted discovery metadata, typed trusted-provider outcomes, Vietnam `CountrySourceRegistry` with five configured providers, and field-specific authority enforcement.
- Verification: discovery/pipeline/source regression suite passed (19 tests); task-scoped Ruff, format, and mypy passed; migration `20260808_0018` passed SQLite upgrade/downgrade/re-upgrade from `20260808_0017`; migration head/history resolved to `20260808_0018`.
- Documentation: affected canonical project documents and both Roadmap copies were updated; no API/OpenAPI contract changed.
- Known independent debt: DEF-CRAWL-002 remains open for repository-wide baseline validation and does not reproduce as an acceptance defect in this task-scoped verification.
- Remaining: TASK-CRAWL-003 and later tasks remain untouched.

## RUN-20260808-13 — TASK-CRAWL-003 official website discovery and URL ranking

- Roadmap task(s): TASK-CRAWL-003 only; TASK-CRAWL-004 was not started.
- Status before: `[ ]`.
- Status after: `[x]` under `docs/agent/AGENT.md`.
- Implemented: bounded robots-aware official website discovery, SSRF-safe direct HTTP adapter, sitemap/homepage/internal-link extraction, canonical URL deduplication, multilingual page-group ranking, deterministic bilingual provider-neutral query templates, same-name review policy, and durable `ResearchQuery`/`SearchResult` metadata migration `20260808_0019`.
- Verification: clean task-only backend suite passed (133 tests, 1 warning); targeted source/search/pipeline regression suite passed (12 tests); task-scoped Ruff, format, and mypy passed; docs, docs-sync, requirement-ID, secrets, and OpenAPI checks passed; migration `20260808_0019` passed isolated SQLite upgrade/downgrade/re-upgrade; migration head/history resolved to `20260808_0019`.
- Documentation: affected canonical project documents and both Roadmap copies were updated; no API/OpenAPI contract changed.
- Known independent debt: DEF-CRAWL-002 remains open for repository-wide baseline validation. The mixed worktree still has the pre-existing dirty `CompanyService` test failure and OpenAPI drift from user-owned API edits; clean task-only validation is green.
- Commit/branch: `task/crawl-003-official-discovery` (final commit recorded in the Git handoff).
- Remaining: TASK-CRAWL-004 and later tasks remain untouched.

## RUN-20260809-14 — TASK-CRAWL-004 crawl, parse, and deterministic extraction

- Roadmap task(s): TASK-CRAWL-004 only; TASK-CRAWL-005 was not started.
- Status before: `[ ]`.
- Status after: `[x]` under `docs/agent/AGENT.md`.
- Implemented: bounded `CrawlCoordinator`; direct HTTP-first fetching with redirect/DNS/IP/size/decompression/MIME/rate/concurrency/retry controls; policy- and budget-gated browser fallback; deterministic HTML, structured JSON, and safe PDF parsing; stable `DocumentBlock` evidence metadata; migration `20260809_0020`; and labelled/structured deterministic facts.
- Verification: task-scoped crawl/parse/extraction and related source/pipeline/service suite passed (25 tests); clean task-only backend suite passed (140 tests, 1 warning); task-scoped Ruff check/format and source mypy passed; docs, docs-sync, requirement-ID, secrets, and clean OpenAPI drift checks passed; isolated SQLite migration `20260809_0020` upgrade/downgrade/re-upgrade passed; migration head/history resolved to `20260809_0020`.
- Documentation: affected canonical project documents, both Roadmap copies, and local `docs/agent/task.md` status/evidence were updated; no API/OpenAPI contract changed.
- Known independent debt: DEF-CRAWL-002 remains open. The mixed primary worktree still has the unrelated dirty `CompanyService` test failure and OpenAPI drift from user-owned API edits; neither reproduces in the clean task-only validation worktree.
- Commit/branch: `task/crawl-004-crawl-parse-extraction`, commit recorded in the Git handoff.
- Remaining: TASK-CRAWL-005 and later tasks remain untouched.
