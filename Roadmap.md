# Implementation Roadmap

**Roadmap mode:** `ACTIVE_DEVELOPMENT`

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

- [ ] **P1-006** Define `AuthProvider` protocol.
- [ ] **P1-007** Implement mock auth adapter for local/CI.
- [ ] **P1-008** Implement production Firebase/Identity Platform token verification after resolving OD-001.
- [ ] **P1-009** Add current-user synchronization and active-status checks.
- [ ] **P1-010** Add request actor context containing user, workspace membership, role, and capabilities.
- [ ] **P1-011** Add `/auth/exchange`, `/auth/logout`, and `/me` routes.
- [ ] **P1-012** Add frontend auth bootstrap, protected routes, and session-ending behavior.

## Block 1C — Workspace administration

- [ ] **P1-013** Add workspace list/detail APIs.
- [ ] **P1-014** Add member invite/add, role update, and deactivation APIs.
- [ ] **P1-015** Add admin member-management UI.
- [ ] **P1-016** Add active workspace selector for multi-workspace users.
- [ ] **P1-017** Add immutable audit records for membership changes.

## Block 1D — Security verification

- [ ] **P1-018** Add route, service, and repository workspace-isolation tests.
- [ ] **P1-019** Add disabled user and revoked membership tests.
- [ ] **P1-020** Add role-capability matrix tests.
- [ ] **P1-021** Add browser E2E for researcher, reviewer, officer, and workspace admin navigation.
- [ ] **P1-022** Review secure cookie/bearer handling and browser token storage.

### Phase 1 completion gate

- [ ] Users authenticate in mock and staging modes.
- [ ] Every protected resource can require workspace scope.
- [ ] Cross-workspace test matrix passes.
- [ ] Membership changes take effect without relying on stale browser role claims.

---

# Phase 2 — Company Identity and Entity Resolution

**Goal:** Create canonical company records safely and prevent same-name contamination.

## Block 2A — Company schema and field registry

- [ ] **P2-001** Add `companies`, `company_aliases`, `company_identifiers`, and `company_relationships` migrations.
- [ ] **P2-002** Add company states and relationship constraints.
- [ ] **P2-003** Implement versioned company field registry baseline.
- [ ] **P2-004** Add name, domain, country, registration identifier, and URL normalization.
- [ ] **P2-005** Add company repositories with workspace scope and search indexes.

## Block 2B — Duplicate and identity resolution

- [ ] **P2-006** Implement duplicate-candidate scoring using strong and weak identity signals.
- [ ] **P2-007** Implement `/companies/resolve` preview endpoint.
- [ ] **P2-008** Implement company creation with idempotency and duplicate conflict behavior.
- [ ] **P2-009** Implement ambiguous company state and identity-confidence explanation.
- [ ] **P2-010** Add alias and identifier management APIs.
- [ ] **P2-011** Add relationship management with evidence placeholder support.

## Block 2C — Company library and detail UI

- [ ] **P2-012** Add paginated company library search by name, alias, domain, country, identifier, and status.
- [ ] **P2-013** Add create-company flow with duplicate suggestions.
- [ ] **P2-014** Add company identity header and ambiguity warnings.
- [ ] **P2-015** Add alias, identifier, and relationship views.
- [ ] **P2-016** Add empty, loading, error, unauthorized, and mobile states.

## Block 2D — Merge, archive, and restore

- [ ] **P2-017** Implement archive and restore with audit.
- [ ] **P2-018** Implement merge preview.
- [ ] **P2-019** Implement transactional merge with stable lock ordering and redirect.
- [ ] **P2-020** Define and implement supported split behavior or mark blocked with an ADR if unsafe for MVP.
- [ ] **P2-021** Add comprehensive identity/merge regression tests.

### Phase 2 completion gate

- [ ] Same-name foreign companies are not auto-merged.
- [ ] Strong-identifier duplicates are detected.
- [ ] Merge preserves history and audit.
- [ ] Company library and identity workflow pass E2E.

---

# Phase 3 — Durable Research Jobs and Progress

**Goal:** Build the asynchronous backbone before connecting real search, fetch, or AI.

## Block 3A — Job schema and planning

- [ ] **P3-001** Add `research_jobs`, `research_job_steps`, and idempotency migrations.
- [ ] **P3-002** Add job and step state enums/constraints.
- [ ] **P3-003** Implement job-scope hashing and active-job uniqueness policy.
- [ ] **P3-004** Implement job planner for initial, refresh, and targeted scopes.
- [ ] **P3-005** Implement job creation transaction and after-commit dispatch interface.

## Block 3B — Worker claim and execution

- [ ] **P3-006** Define `TaskDispatcher` and local PostgreSQL dispatcher.
- [ ] **P3-007** Implement row-lock claim with lease owner and expiry.
- [ ] **P3-008** Implement dependency-aware step execution.
- [ ] **P3-009** Implement bounded retry and exponential backoff.
- [ ] **P3-010** Implement stale-lease recovery.
- [ ] **P3-011** Implement cancellation at safe boundaries.
- [ ] **P3-012** Implement partial-success and critical-failure aggregation.
- [ ] **P3-013** Add worker graceful shutdown and in-flight lease behavior.

## Block 3C — API and progress UI

- [ ] **P3-014** Add research job create/list/detail/cancel/retry endpoints.
- [ ] **P3-015** Add SSE event stream with sequence and reconnect behavior.
- [ ] **P3-016** Add polling fallback.
- [ ] **P3-017** Add job progress UI with durable steps and partial-success states.
- [ ] **P3-018** Add operational job list for administrators.

## Block 3D — Verification

- [ ] **P3-019** Add concurrent claim and duplicate delivery tests.
- [ ] **P3-020** Add retry, cancellation, crash, and lease-expiry tests.
- [ ] **P3-021** Add SSE reconnect and browser progress E2E.
- [ ] **P3-022** Add metrics for queue depth, age, attempts, and step duration.

### Phase 3 completion gate

- [ ] Fixture-only job can run end-to-end through planned steps.
- [ ] Worker restart does not lose or duplicate completed work.
- [ ] UI shows accurate progress after page reload.

---

# Phase 4 — Source Discovery and Policy

**Goal:** Discover relevant public sources with transparent selection and compliance controls.

## Block 4A — Query and search persistence

- [ ] **P4-001** Add `research_queries`, `search_results`, `sources`, and domain-policy migrations.
- [ ] **P4-002** Define `SearchProvider` protocol and result schema.
- [ ] **P4-003** Implement fixture search provider.
- [ ] **P4-004** Implement query generation for official, registry, product, news, and relationship sources.
- [ ] **P4-005** Record generated/user queries and provider results.

## Block 4B — Source normalization and ranking

- [ ] **P4-006** Implement URL/domain normalization and canonicalization.
- [ ] **P4-007** Implement source-type classification baseline.
- [ ] **P4-008** Implement authority tiers and field-specific source policy model.
- [ ] **P4-009** Implement entity-match scoring.
- [ ] **P4-010** Implement duplicate URL and mirror candidate detection.
- [ ] **P4-011** Implement selected/rejected/blocked decision reasons.
- [ ] **P4-012** Prevent search snippets from becoming accepted evidence directly.

## Block 4C — Policy administration

- [ ] **P4-013** Add allowed/blocked domain rules.
- [ ] **P4-014** Add source policy APIs and admin UI.
- [ ] **P4-015** Add manual public URL addition with policy validation.
- [ ] **P4-016** Add quick domain block operation and audit.
- [ ] **P4-017** Resolve OD-002 and implement approved real search adapter.

## Block 4D — UI and tests

- [ ] **P4-018** Add source list with authority, entity match, language, status, and reason.
- [ ] **P4-019** Add query/result inspection view.
- [ ] **P4-020** Add official-site selection review workflow.
- [ ] **P4-021** Add duplicate, wrong-entity, blocked, and zero-result tests.
- [ ] **P4-022** Add search quota/cost/selection metrics.

### Phase 4 completion gate

- [ ] Fixture and staging search produce auditable source candidates.
- [ ] Official-source choice is explainable.
- [ ] Blocked domains cannot proceed to fetch.

---

# Phase 5 — Safe Content Acquisition and Document Parsing

**Goal:** Capture reproducible public evidence without weakening security or access policy.

## Block 5A — Fetch and snapshot schema

- [ ] **P5-001** Add `source_fetch_attempts`, `source_snapshots`, and `document_blocks` migrations.
- [ ] **P5-002** Define fetch, storage, scanner, and parser protocols.
- [ ] **P5-003** Implement local private object-storage adapter.
- [ ] **P5-004** Implement snapshot metadata, content hash, and immutability guards.
- [ ] **P5-005** Implement orphan object reconciliation baseline.

## Block 5B — HTTP safety boundary

- [ ] **P5-006** Implement public `http/https` URL validation.
- [ ] **P5-007** Block loopback, private, link-local, reserved, and metadata IP ranges.
- [ ] **P5-008** Revalidate redirect destinations and DNS results.
- [ ] **P5-009** Enforce timeout, redirect, byte, decompression, and content-type limits.
- [ ] **P5-010** Implement per-domain rate and concurrency limits.
- [ ] **P5-011** Implement robots and source-policy decision recording.
- [ ] **P5-012** Sanitize errors and response metadata.

## Block 5C — Parsers

- [ ] **P5-013** Implement HTML metadata, visible text, and structured JSON-LD parser.
- [ ] **P5-014** Implement stable document-block segmentation and location references.
- [ ] **P5-015** Implement PDF parser with page references.
- [ ] **P5-016** Implement language detection and encoding preservation.
- [ ] **P5-017** Implement unsupported/encrypted/malformed document outcomes.
- [ ] **P5-018** Resolve OD-005 and implement malware/quarantine production adapter or block production PDF acceptance.

## Block 5D — Browser fallback

- [ ] **P5-019** Implement Playwright browser adapter with resource/time limits.
- [ ] **P5-020** Apply the same URL/network policy to browser navigation and subresources.
- [ ] **P5-021** Define when browser fallback is allowed and record reason.
- [ ] **P5-022** Add browser worker sandbox guidance and metrics.

## Block 5E — UI and verification

- [ ] **P5-023** Add source snapshot history and fetch-attempt view.
- [ ] **P5-024** Add parsed-block viewer with page/section context.
- [ ] **P5-025** Add SSRF, redirect, MIME, size, timeout, and robots security tests.
- [ ] **P5-026** Add HTML/PDF/dynamic/multilingual parser fixtures and tests.
- [ ] **P5-027** Add source integrity and object-reconciliation tests.

### Phase 5 completion gate

- [ ] Official HTML and PDF fixtures create immutable evidence blocks.
- [ ] SSRF and unsafe redirects are blocked.
- [ ] Browser fallback cannot weaken network policy.
- [ ] Snapshots remain reproducible after source changes.

---

# Phase 6 — Gemini Structured Extraction and Translation

**Goal:** Generate grounded candidate facts while treating AI output as untrusted.

## Block 6A — AI run infrastructure

- [ ] **P6-001** Add `ai_runs` migration and provider usage metadata.
- [ ] **P6-002** Define provider-neutral AI operation schemas.
- [ ] **P6-003** Implement deterministic mock AI adapter.
- [ ] **P6-004** Implement Gemini adapter behind `AiProvider`.
- [ ] **P6-005** Add per-operation model, timeout, retry, and budget configuration.
- [ ] **P6-006** Add safe prompt/result retention policy and request hashes.

## Block 6B — Extraction schemas

- [ ] **P6-007** Implement identity and legal-information extraction schema.
- [ ] **P6-008** Implement overview, industry, and business-model schema.
- [ ] **P6-009** Implement products/services schema.
- [ ] **P6-010** Implement size and footprint schema.
- [ ] **P6-011** Implement markets, customers, and partners schema.
- [ ] **P6-012** Implement leadership/ownership schema.
- [ ] **P6-013** Implement innovation, awards, certifications, funding, and recent-activity schema.
- [ ] **P6-014** Require evidence block IDs and explicit unknown behavior in every schema.

## Block 6C — Validation and injection defense

- [ ] **P6-015** Validate structured output and reject malformed responses.
- [ ] **P6-016** Validate every evidence block reference.
- [ ] **P6-017** Validate entity match and field type/unit.
- [ ] **P6-018** Add deterministic support check between claim and evidence.
- [ ] **P6-019** Add fetched-content prompt-injection defenses.
- [ ] **P6-020** Ensure AI cannot select tools, publish profiles, or change policy directly.
- [ ] **P6-021** Add unknown, unsupported, and wrong-entity regression cases.

## Block 6D — Translation

- [ ] **P6-022** Implement original-language preservation.
- [ ] **P6-023** Implement derived evidence translation with provider/version metadata.
- [ ] **P6-024** Show original and translated evidence together.
- [ ] **P6-025** Add translation-quality and missing-translation fallback tests.

## Block 6E — Operational verification

- [ ] **P6-026** Add token/cost/latency/validation metrics.
- [ ] **P6-027** Add per-job/workspace budget enforcement and kill switch.
- [ ] **P6-028** Add staging real-Gemini acceptance cases and record model/prompt version.
- [ ] **P6-029** Add model-change regression procedure.

### Phase 6 completion gate

- [ ] AI candidate output always references valid evidence or is rejected.
- [ ] Unknown fields remain unknown rather than fabricated.
- [ ] Prompt-injection fixtures cannot change system behavior.
- [ ] Provider cost and version are observable.

---

# Phase 7 — Facts, Confidence, Freshness, and Conflicts

**Goal:** Convert validated candidates into explainable, reviewable company knowledge.

## Block 7A — Fact and evidence persistence

- [ ] **P7-001** Add `fact_candidates` and `evidences` migrations.
- [ ] **P7-002** Implement candidate/evidence transaction.
- [ ] **P7-003** Implement typed value serialization and field normalization.
- [ ] **P7-004** Implement direct, inferred, estimated, and unknown status handling.
- [ ] **P7-005** Implement duplicate candidate/evidence prevention.

## Block 7B — Confidence and source agreement

- [ ] **P7-006** Implement versioned confidence policy components.
- [ ] **P7-007** Implement field-specific source authority lookup.
- [ ] **P7-008** Implement recency/freshness calculation.
- [ ] **P7-009** Implement evidence-quality and extraction-reliability components.
- [ ] **P7-010** Implement source-agreement adjustment.
- [ ] **P7-011** Persist human-readable confidence explanation.
- [ ] **P7-012** Add calibration fixture dataset and baseline evaluation report.

## Block 7C — Conflict engine

- [ ] **P7-013** Add `conflicts` and `conflict_candidates` migrations.
- [ ] **P7-014** Implement field-specific equivalence and material-difference comparators.
- [ ] **P7-015** Create conflicts without overwriting candidates.
- [ ] **P7-016** Support multiple time-scoped valid values.
- [ ] **P7-017** Reopen resolved conflict when new material evidence arrives.
- [ ] **P7-018** Add targeted re-research request creation.

## Block 7D — Fact and conflict UI

- [ ] **P7-019** Add grouped fact-candidate view.
- [ ] **P7-020** Add evidence context panel.
- [ ] **P7-021** Add confidence component explanation.
- [ ] **P7-022** Add conflict comparison and status UI.
- [ ] **P7-023** Add stale and missing-information indicators.

## Block 7E — Verification

- [ ] **P7-024** Add exact/range/date/name/unit conflict tests.
- [ ] **P7-025** Add source priority and recency tests.
- [ ] **P7-026** Add inferred/estimated display regression tests.
- [ ] **P7-027** Add confidence non-guarantee copy and accessibility review.

### Phase 7 completion gate

- [ ] Every candidate has typed value and valid evidence status.
- [ ] Confidence is explainable, not a magic number.
- [ ] Material disagreements create visible conflicts.
- [ ] Stale and unknown states are explicit.

---

# Phase 8 — Human Review and Publication

**Goal:** Make trusted publication a controlled, auditable human decision.

## Block 8A — Review workflow

- [ ] **P8-001** Add `review_tasks` and append-only `review_decisions` migrations.
- [ ] **P8-002** Implement task creation rules for identity, high-impact facts, conflicts, and publication.
- [ ] **P8-003** Implement claim, release, request changes, complete, cancel, and reopen transitions.
- [ ] **P8-004** Implement optimistic row-version protection.
- [ ] **P8-005** Require reason for rejection, override, and reopen.
- [ ] **P8-006** Resolve OD-006 and configure mandatory-review field set.

## Block 8B — Draft profile assembly

- [ ] **P8-007** Add `profile_drafts` and `draft_field_selections` migrations.
- [ ] **P8-008** Implement draft assembly from accepted/recommended candidates.
- [ ] **P8-009** Implement missing-section and unresolved-conflict blockers.
- [ ] **P8-010** Implement manual human-origin candidate workflow.
- [ ] **P8-011** Implement request-review and changes-requested flow.

## Block 8C — Immutable publication

- [ ] **P8-012** Add `profile_versions`, `profile_field_values`, and `profile_field_evidences` migrations.
- [ ] **P8-013** Implement publication transaction with one-current-version constraint.
- [ ] **P8-014** Snapshot confidence, status, evidence, policy, and schema versions.
- [ ] **P8-015** Implement supersede and withdraw behavior.
- [ ] **P8-016** Implement grounded summary generation from accepted field payload only.
- [ ] **P8-017** Add publication audit event and content hash.

## Block 8D — Review and profile UI

- [ ] **P8-018** Add review inbox with filters, priority, assignment, and age.
- [ ] **P8-019** Add identity review workspace.
- [ ] **P8-020** Add fact/conflict review workspace with source context.
- [ ] **P8-021** Add draft profile editor/selector.
- [ ] **P8-022** Add publication blocker summary.
- [ ] **P8-023** Add published profile view with field-level evidence.
- [ ] **P8-024** Add withdrawal/superseded warnings.

## Block 8E — Verification

- [ ] **P8-025** Add concurrent reviewer overwrite tests.
- [ ] **P8-026** Add concurrent publication and immutability tests.
- [ ] **P8-027** Add mandatory evidence/high-impact blocker tests.
- [ ] **P8-028** Add end-to-end trusted first profile scenario.
- [ ] **P8-029** Add end-to-end conflict review and corrected-version scenario.

### Phase 8 completion gate

- [ ] No high-impact fact publishes without required review.
- [ ] Published versions are immutable and auditable.
- [ ] Every field exposes accepted evidence or permitted exception.
- [ ] Current profile survives failed refresh/publication attempts.

---

# Phase 9 — Company Library, History, Meeting Brief, and Export

**Goal:** Turn trusted profiles into reusable institutional knowledge.

## Block 9A — Search and filters

- [ ] **P9-001** Expand company search by industry, market, product keyword, freshness, conflict, and profile status.
- [ ] **P9-002** Add indexed query paths and query-plan tests.
- [ ] **P9-003** Add saved tags/bookmarks if retained in MVP scope.
- [ ] **P9-004** Add attention-required and stale profile dashboards.

## Block 9B — Profile history

- [ ] **P9-005** Add profile version list and current/historical state.
- [ ] **P9-006** Implement field-level diff service.
- [ ] **P9-007** Add source/evidence change summary.
- [ ] **P9-008** Add refresh comparison against current published version.

## Block 9C — Meeting brief

- [ ] **P9-009** Implement one-minute brief from published fields only.
- [ ] **P9-010** Add key products, markets, size, recent activity, missing data, and suggested verification questions.
- [ ] **P9-011** Ensure suggested questions are clearly generated guidance, not facts.
- [ ] **P9-012** Add Vietnamese and English brief presentation.

## Block 9D — Export

- [ ] **P9-013** Add `export_jobs` migration and idempotent worker flow.
- [ ] **P9-014** Implement structured JSON export.
- [ ] **P9-015** Implement PDF export with version, generated time, status labels, and source appendix.
- [ ] **P9-016** Add private object storage and authorized download.
- [ ] **P9-017** Resolve OD-008 for internal-note export policy.
- [ ] **P9-018** Add export audit and expiry behavior.
- [ ] **P9-019** Add PDF layout/manual acceptance and download E2E.

### Phase 9 completion gate

- [ ] Staff can find and reuse a prior company profile quickly.
- [ ] History and diffs remain understandable.
- [ ] Meeting brief introduces no unsupported fact.
- [ ] Exports remain tied to immutable profile version and source appendix.

---

# Phase 10 — Policies, Administration, Privacy, and Audit

**Goal:** Make the system governable and safe for institutional operation.

## Block 10A — Versioned policy sets

- [ ] **P10-001** Add `policy_sets` migration and immutable version model.
- [ ] **P10-002** Implement source authority, confidence, freshness, mandatory-review, fetch, AI budget, and retention policy schemas.
- [ ] **P10-003** Implement policy creation, validation, activation, and audit APIs.
- [ ] **P10-004** Ensure jobs and published profiles snapshot policy version.
- [ ] **P10-005** Add policy administration UI with safe explanations.

## Block 10B — Audit

- [ ] **P10-006** Add append-only `audit_logs` migration.
- [ ] **P10-007** Audit membership, identity, source block/reject, manual fact, conflict, review, publication, merge, export, and policy changes.
- [ ] **P10-008** Add audit list/filter/detail API and UI.
- [ ] **P10-009** Add redaction and no-secret audit tests.
- [ ] **P10-010** Add audit retention and access policy.

## Block 10C — Privacy and retention

- [ ] **P10-011** Resolve OD-003 and OD-004 for source retention.
- [ ] **P10-012** Implement retention classes and object lifecycle jobs.
- [ ] **P10-013** Implement legal hold metadata if required.
- [ ] **P10-014** Implement takedown/domain block operational flow.
- [ ] **P10-015** Implement personal-data minimization review for AI and logs.
- [ ] **P10-016** Add deletion/reconciliation tests.

## Block 10D — Provider operations

- [ ] **P10-017** Add safe provider configuration status UI.
- [ ] **P10-018** Add job/provider usage and cost dashboard.
- [ ] **P10-019** Add workspace budget limits and emergency kill switches.
- [ ] **P10-020** Add failed job/retry operations with audit.

### Phase 10 completion gate

- [ ] Policies are versioned and reproducible.
- [ ] Sensitive actions are auditable.
- [ ] Retention and provider budgets have approved behavior.
- [ ] Administration APIs expose no provider secrets.

---

# Phase 11 — Observability, Security Hardening, and Performance

**Goal:** Validate the trusted-profile system under realistic failure, attack, and load conditions.

## Block 11A — Observability

- [ ] **P11-001** Finalize structured logs across API and worker.
- [ ] **P11-002** Finalize metrics listed in operations docs.
- [ ] **P11-003** Add distributed trace propagation.
- [ ] **P11-004** Create staging dashboards for API, jobs, fetch, AI, review, publication, and cost.
- [ ] **P11-005** Add alerts for queue age, failures, quota, cost, integrity, and audit-write failure.

## Block 11B — Security hardening

- [ ] **P11-006** Complete threat model for auth, workspace isolation, SSRF, parser, browser, AI injection, object storage, and export.
- [ ] **P11-007** Run dependency, secret, container, and license scans.
- [ ] **P11-008** Run targeted SSRF and authorization penetration tests.
- [ ] **P11-009** Validate browser sandbox and egress restrictions.
- [ ] **P11-010** Validate object storage private access and signed URL expiry.
- [ ] **P11-011** Validate no sensitive provider data appears in logs, traces, API, or audit.
- [ ] **P11-012** Add security incident runbook exercises.

## Block 11C — Performance and resilience

- [ ] **P11-013** Resolve OD-009 and record approved SLO/RPO/RTO.
- [ ] **P11-014** Generate representative staging dataset.
- [ ] **P11-015** Load-test company search and profile reads.
- [ ] **P11-016** Load-test job creation, worker claim, and retries.
- [ ] **P11-017** Test publication and merge contention.
- [ ] **P11-018** Test large PDF/browser memory limits.
- [ ] **P11-019** Test provider outage, quota, timeout, and duplicate task delivery.
- [ ] **P11-020** Optimize measured queries/indexes and document changes.

## Block 11D — Accessibility and UX acceptance

- [ ] **P11-021** Run automated accessibility checks.
- [ ] **P11-022** Run keyboard and screen-reader manual checks.
- [ ] **P11-023** Run desktop/mobile responsive acceptance.
- [ ] **P11-024** Conduct researcher/reviewer usability test.
- [ ] **P11-025** Review Vietnamese product copy and English fallback.

### Phase 11 completion gate

- [ ] Security and isolation controls have evidence.
- [ ] SLO/load tests are recorded.
- [ ] Observability and incident response are usable.
- [ ] Critical user workflows pass accessibility and responsive checks.

---

# Phase 12 — Cloud Deployment and Competition Demo

**Goal:** Deploy a reliable staging/production-like environment and prepare a compelling AI Riser demonstration.

## Block 12A — Cloud infrastructure

- [ ] **P12-001** Create separate staging and production Google Cloud projects/environments.
- [ ] **P12-002** Configure Cloud SQL, private connectivity, backups, and PITR.
- [ ] **P12-003** Configure private Cloud Storage buckets and lifecycle rules.
- [ ] **P12-004** Configure Cloud Run web/API/worker services.
- [ ] **P12-005** Configure Cloud Tasks with authenticated worker delivery.
- [ ] **P12-006** Configure Secret Manager and least-privilege service accounts.
- [ ] **P12-007** Configure managed HTTPS, domain, CORS, and protected operations endpoints.
- [ ] **P12-008** Configure Cloud Logging, Monitoring, Trace, dashboards, and alerts.

## Block 12B — CI/CD and migration release

- [ ] **P12-009** Build immutable commit-tagged images.
- [ ] **P12-010** Add protected staging deployment workflow.
- [ ] **P12-011** Add protected production deployment workflow with approval.
- [ ] **P12-012** Add explicit migration job and rollback metadata.
- [ ] **P12-013** Add staging smoke and post-deploy checks.
- [ ] **P12-014** Add release notes/changelog workflow.

## Block 12C — Real-provider acceptance

- [ ] **P12-015** Verify production auth in staging.
- [ ] **P12-016** Verify approved real search provider with quota limits.
- [ ] **P12-017** Verify Gemini operations with budget and regression cases.
- [ ] **P12-018** Verify approved public HTML and PDF sources under policy.
- [ ] **P12-019** Verify malware scanner and private storage flow.
- [ ] **P12-020** Verify provider failure and kill-switch operation.

## Block 12D — Backup, restore, and readiness

- [ ] **P12-021** Perform documented staging restore drill.
- [ ] **P12-022** Verify profile/evidence integrity after restore.
- [ ] **P12-023** Verify incident runbooks and on-call ownership.
- [ ] **P12-024** Complete production readiness checklist in `08_DEPLOYMENT_AND_OPERATIONS.md`.
- [ ] **P12-025** Complete legal/privacy/source-acquisition review gates.

## Block 12E — Competition demo package

- [ ] **P12-026** Prepare deterministic demo companies including multilingual and conflict cases.
- [ ] **P12-027** Prepare live demo flow from company input to published profile.
- [ ] **P12-028** Demonstrate evidence click-through and confidence explanation.
- [ ] **P12-029** Demonstrate conflict resolution and version history.
- [ ] **P12-030** Demonstrate meeting brief and export.
- [ ] **P12-031** Prepare fallback video/screenshots and offline mock mode.
- [ ] **P12-032** Prepare architecture, trust, AI, privacy, and impact explanation.
- [ ] **P12-033** Rehearse time-boxed demo and failure fallback.

### Phase 12 completion gate

- [ ] Deployed environment passes smoke, security, provider, backup, and readiness checks.
- [ ] Competition demo works in live and fallback modes.
- [ ] Documentation reflects exact deployed behavior and limitations.

---

# Optional Phase 13 — Post-MVP Fit Assessment

**Goal:** Add transparent support for assessing relevance to innovation-center programs only after profile trust is proven.

This phase does not block trusted-profile Roadmap completion unless stakeholders explicitly move it into required scope.

- [ ] **P13-001** Define program criteria and decision ownership.
- [ ] **P13-002** Separate profile facts from assessment rules and generated recommendations.
- [ ] **P13-003** Implement rules-based explainable fit assessment.
- [ ] **P13-004** Require evidence references for every assessment reason.
- [ ] **P13-005** Add reviewer override and no-automatic-rejection policy.
- [ ] **P13-006** Add meeting-question suggestions labeled as guidance.
- [ ] **P13-007** Evaluate fairness, false certainty, and misuse risks.
- [ ] **P13-008** Add assessment history and audit.

---

# Final Completion Gate

The required Roadmap is complete only when all required tasks in Phases 0–12 satisfy the following. Optional Phase 13 is excluded unless formally moved into required scope.

## Product completeness

- [ ] Company identity, research, source acquisition, AI extraction, evidence, conflicts, review, publication, library, history, brief, and export meet acceptance criteria.
- [ ] No required feature is only a placeholder or mock in production mode.
- [ ] Known limitations are explicit and accepted.

## Quality completeness

- [ ] Mandatory lint, format, typecheck, unit, integration, security, contract, frontend, and E2E suites pass.
- [ ] Load and concurrency tests meet approved targets.
- [ ] Accessibility and responsive acceptance pass.
- [ ] No open critical/high release-blocking defect remains.

## Trust and safety completeness

- [ ] Published facts have required evidence.
- [ ] High-impact fields require review.
- [ ] SSRF, parser, browser, AI injection, workspace isolation, and secret controls pass.
- [ ] Source-acquisition and privacy policies are approved.

## Operations completeness

- [ ] Deployment, migrations, monitoring, alerts, backup, restore, rollback, and incident runbooks are verified.
- [ ] Provider cost/quota limits and kill switches are operational.
- [ ] Production readiness checklist is complete.

## Documentation completeness

- [ ] All canonical documents match the final codebase and deployment.
- [ ] Requirement and Roadmap statuses are verified.
- [ ] API/OpenAPI, database migrations, environment, and operations docs are synchronized.
- [ ] Defect and debt ledgers are current.
- [ ] Completion evidence includes release, commit, date, validation commands, and deployment environment.

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

No defects are recorded in this initial specification baseline.
