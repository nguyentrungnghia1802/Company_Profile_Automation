# Codebase Guide

Status: planned repository and layering conventions.

## 1. Repository layout

```text
.
|-- apps/
|   |-- web/                       Next.js application
|   \-- backend/                   Shared Python backend package and process entrypoints
|       |-- src/company_profile/
|       |   |-- api/               FastAPI app, routers, dependencies, middleware
|       |   |-- modules/           Domain/application modules
|       |   |-- db/                SQLAlchemy base, sessions, repositories
|       |   |-- worker/            Job claim loop and task entrypoints
|       |   |-- integrations/      Search, fetch, AI, auth, storage adapters
|       |   |-- operations/        Logs, metrics, tracing, health
|       |   \-- config/            Typed environment configuration
|       \-- tests/
|-- packages/
|   |-- api-client/                Generated TypeScript client from OpenAPI
|   \-- ui/                        Optional framework-safe shared UI components
|-- db/
|   |-- migrations/                Alembic migrations
|   \-- fixtures/                  Deterministic development and E2E fixtures
|-- docs/project/                  Canonical technical documents
|-- scripts/                       Contract, docs-sync, fixture, and maintenance scripts
|-- deploy/                        Cloud and Compose deployment files
|-- .github/workflows/             CI/CD
|-- docker-compose.yml
|-- Makefile
|-- pyproject.toml
|-- pnpm-workspace.yaml
|-- README.md
|-- AGENT.md
\-- Roadmap.md
```

Do not create a second competing source tree without an ADR.

## 2. Backend layout

```text
apps/backend/src/company_profile/
|-- api/
|   |-- app.py
|   |-- dependencies.py
|   |-- errors.py
|   |-- middleware/
|   \-- routers/
|-- modules/
|   |-- auth/
|   |-- workspaces/
|   |-- companies/
|   |-- research/
|   |-- discovery/
|   |-- sources/
|   |-- documents/
|   |-- ai/
|   |-- facts/
|   |-- conflicts/
|   |-- reviews/
|   |-- profiles/
|   |-- exports/
|   |-- policies/
|   \-- audit/
|-- db/
|   |-- base.py
|   |-- session.py
|   |-- transaction.py
|   \-- models/
|-- worker/
|   |-- main.py
|   |-- claimer.py
|   |-- executor.py
|   \-- tasks/
|-- integrations/
|   |-- auth/
|   |-- search/
|   |-- fetch/
|   |-- browser/
|   |-- ai/
|   \-- storage/
|-- operations/
|   |-- logging.py
|   |-- metrics.py
|   |-- tracing.py
|   \-- health.py
\-- config/
    \-- settings.py
```

Each domain module may contain:

```text
<module>/
|-- domain.py              Entities, value objects, state rules
|-- schemas.py             Pydantic transport/application schemas
|-- service.py             Use-case orchestration
|-- repository.py          Interface/protocol
|-- sqlalchemy_repository.py
|-- policies.py            Deterministic policy functions
|-- errors.py
\-- tests/
```

Avoid creating files only to satisfy a pattern when a module is small, but preserve responsibility boundaries.

## 3. Layer rules

| Layer | May do | Must not do |
| --- | --- | --- |
| Router | Define endpoint, dependencies, input/output mapping | Business policy, SQL, provider calls |
| Middleware/dependency | Authentication, request context, cross-cutting checks | Hidden domain decisions |
| Schema | Validate and serialize typed contracts | Database access or provider calls |
| Application service | Authorize use case, orchestrate transactions and providers | Render HTTP responses or import React |
| Domain policy | Pure state, normalization, confidence, conflict rules | Network, database, environment access |
| Repository | Parameterized persistence and mapping | Decide actor authorization or call AI/search |
| Provider adapter | External protocol and transport | Accept/publish facts or bypass policy |
| Worker task | Claim work and invoke application service | Duplicate domain logic |
| React page | Compose queries, forms, and components | Own server authority or confidence math |

## 4. Frontend layout

```text
apps/web/src/
|-- app/                         Next.js routes/layouts
|   |-- (auth)/
|   |-- companies/
|   |-- reviews/
|   |-- operations/
|   \-- admin/
|-- components/
|   |-- ui/
|   |-- company/
|   |-- evidence/
|   |-- facts/
|   |-- conflicts/
|   |-- profile/
|   \-- jobs/
|-- features/                    Feature hooks and orchestration
|-- services/                    Generated client wrapper, SSE, auth adapter
|-- stores/                      Minimal browser-only UI state
|-- i18n/                        vi/en resources
|-- utils/                       Pure formatting and safe helpers
|-- types/                       Frontend-only types not in generated client
\-- tests/
```

Frontend rules:

- TanStack Query owns server state.
- Forms use a typed schema and field-level API errors.
- Browser storage stores only safe drafts/preferences, never authorization or accepted fact truth.
- Evidence rendering escapes/sanitizes untrusted text.
- Source HTML is never rendered unsanitized.
- Status is communicated with text and icon, not color alone.
- Every page handles loading, empty, error, retry, unauthorized, and stale states.

## 5. Naming conventions

### Python

- modules and files: `snake_case`;
- classes and Pydantic models: `PascalCase`;
- functions and variables: `snake_case`;
- constants: `UPPER_SNAKE_CASE`;
- database columns: `snake_case`;
- test files: `test_<behavior>.py`.

### TypeScript/React

- components: `PascalCase.tsx`;
- hooks: `useSomething.ts`;
- utilities: `camelCase.ts` or project-consistent kebab case selected in foundation phase;
- generated API types are not manually edited.

### API and domain IDs

- requirement IDs remain stable after publication;
- error codes use `UPPER_SNAKE_CASE`;
- field keys use versioned dotted names such as `company.legal_name`, `company.employee_range`;
- event names use dotted lowercase such as `research.step.succeeded`.

## 6. Company field schema

Field definitions belong in one versioned backend registry, not duplicated across prompts, UI, and database code.

A field definition includes:

- key;
- section;
- value type and validation schema;
- cardinality;
- normalization function;
- display format;
- high-impact flag;
- freshness policy key;
- source preference rule;
- conflict comparator;
- allowed statuses;
- localization labels.

Frontend receives field metadata through API or generated shared contract.

## 7. Provider interfaces

Required protocols:

```text
AuthProvider
SearchProvider
HttpFetcher
BrowserFetcher
DocumentParser
AiProvider
ObjectStorage
MalwareScanner
TaskDispatcher
Clock
```

Every production provider has:

- mock or fixture implementation;
- timeout and retry policy;
- typed errors;
- safe logging;
- health/configuration signal;
- cost/privacy notes in operations docs;
- contract tests where practical.

Application services depend on protocols, not vendor SDK classes.

## 8. Error conventions

Backend domain/application errors contain:

- stable code;
- safe diagnostic message;
- HTTP mapping at API boundary;
- structured safe details;
- retryable flag when relevant.

Do not branch frontend behavior on arbitrary English messages.

Expected examples:

- `COMPANY_DUPLICATE_REVIEW_REQUIRED`;
- `COMPANY_ENTITY_AMBIGUOUS`;
- `RESEARCH_JOB_ALREADY_ACTIVE`;
- `SOURCE_BLOCKED_BY_POLICY`;
- `SOURCE_FETCH_SSRF_BLOCKED`;
- `AI_OUTPUT_UNGROUNDED`;
- `FACT_EVIDENCE_REQUIRED`;
- `CONFLICT_REVIEW_REQUIRED`;
- `PROFILE_PUBLICATION_BLOCKED`;
- `REVIEW_VERSION_CONFLICT`.

## 9. Transaction conventions

- Application service opens transactions.
- Repository methods accept an explicit session/unit of work.
- External calls do not occur while holding long database locks unless unavoidable and documented.
- Prepare external artifact, then commit metadata with reconciliation strategy.
- Use stable lock ordering for company merge/publication.
- After-commit dispatch may retry independently.
- Cache invalidation occurs after commit.

## 10. Adding a backend endpoint

1. Identify requirement and business rule IDs.
2. Update domain flow if behavior is new.
3. Add Pydantic input/output schemas.
4. Add application service authorization and transaction behavior.
5. Add repository methods with workspace scope.
6. Add provider interaction behind interface if needed.
7. Add router and response mapping.
8. Add unit, integration, authorization, and route tests.
9. Regenerate OpenAPI/client.
10. Update `05_API.md`, status documents, Roadmap, and sync checklist.

## 11. Adding a database capability

1. Confirm domain invariant and query path.
2. Add Alembic migration; do not edit applied history.
3. Define FKs, checks, indexes, uniqueness, retention, and downgrade.
4. Update SQLAlchemy model and repository.
5. Add clean migration and upgrade tests.
6. Add transaction/concurrency tests.
7. Update `04_DATABASE.md`, Roadmap, and affected API/domain docs.

## 12. Adding a profile field

1. Add field registry definition and schema version decision.
2. Define normalization, comparator, source preference, freshness, and review policy.
3. Update extraction structured schema and deterministic validators.
4. Update frontend labels for `vi` and `en`.
5. Add examples and tests for direct, unknown, inferred, estimated, and conflict cases.
6. Decide migration/backfill strategy for published profiles.
7. Update requirements and domain documentation.

## 13. Adding an AI operation

1. Document the use case and why deterministic logic is insufficient.
2. Define provider-neutral input/output schema.
3. Define evidence and unknown behavior.
4. Add prompt-injection and data-minimization controls.
5. Add mock fixtures and schema-validation tests.
6. Add budget, timeout, retry, and fallback.
7. Record provider/model/prompt version in `ai_runs`.
8. Update architecture, operations, risks, and Roadmap.

## 14. Adding a fetch source type

1. Confirm legal/policy allowance.
2. Add source classifier rule.
3. Implement fetch adapter or parser without bypassing access controls.
4. Add SSRF, size, MIME, timeout, and rate-limit tests.
5. Preserve stable evidence location.
6. Add fixture content; automated tests must not depend on live websites.
7. Update source requirements, operations, and risk register.

## 15. Localization

- Product UI: Vietnamese default and English.
- Technical docs, code, logs, and commits: English.
- Source text: preserve original.
- Translation keys are semantic and grouped by feature.
- Every new visible key must exist in both locales before handoff.
- Dates, numbers, currency, and ranges use locale-aware formatting.
- Field values are stored locale-neutral.

## 16. Files requiring extra care

- `.env.example`: placeholders only; no real tokens or secret-shaped examples.
- `db/migrations/**`: immutable after application.
- field registry and schema versions: affect extraction, conflicts, API, UI, and exports.
- research job claimer/executor: concurrency and idempotency critical.
- source fetch URL validation: SSRF boundary.
- snapshot object reconciliation: evidence integrity boundary.
- AI prompts and validators: hallucination and injection boundary.
- publication service: immutable profile and audit boundary.
- merge service: irreversible identity-history boundary.
- generated API client: never hand edit.
- `Roadmap.md`: implementation status and defect ledger, not product truth by itself.

## 17. Documentation update markers

Every material pull request or agent task should include a short mapping:

```text
Requirements: FR-..., BR-...
Roadmap: PHASE-TASK
Docs updated: 00/01/02/...
Tests: commands and result
Known defects: none | DEF-...
```

This may live in a commit message, pull request template, or agent completion note, but canonical documents must still be updated.

## 18. Codebase synchronization checklist

- [ ] Repository tree matches this guide.
- [ ] Layer responsibilities are preserved.
- [ ] No business rules are duplicated in route/UI/provider layers.
- [ ] New provider has mock, timeout, safe error, and documentation.
- [ ] Generated files are regenerated, not edited manually.
- [ ] Field registry remains the single schema authority.
- [ ] All visible copy exists in Vietnamese and English.
- [ ] Sensitive files and local artifacts are ignored.
- [ ] Affected docs and Roadmap entries are updated.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

Actual ownership for the verified pipeline is:

- `modules/research/dispatcher.py`: durable ordered task creation and job finalization;
- `modules/research/pipeline.py`: application-level step orchestration and optional-provider handling;
- `modules/sources/fetcher.py`: safe fetch, immutable snapshot persistence, and idempotent parsing;
- `modules/facts/deterministic.py`: high-precision structured/labeled extraction with evidence;
- `worker/runner.py`: task claim execution, output persistence, and step advancement;
- `integrations/ai/*`, `integrations/search/*`, and storage adapters: provider boundaries and deterministic test doubles.

## Verified implementation addendum — TASK-CRAWL-002 (2026-08-08)

Source-discovery ownership is:

- `modules/sources/discovery.py`: canonical candidate model, provider outcome contract, source aggregation, tenant-scoped history reuse, deterministic selection, and persisted provenance;
- `modules/sources/trusted_sources.py`: `TrustedSourceProvider`, `CountrySourceRegistry`, Vietnam definitions, and the no-fabrication configured adapter;
- `modules/sources/policy.py`: domain classification and compatibility authority tier defaults;
- `db/models/source.py`: discovery/provider/reason metadata and field-specific authority lookup;
- `modules/research/pipeline.py`: only step orchestration and provider injection.

New country providers register through `CountrySourceRegistry` and do not require edits to the discovery core. Provider adapters may return explicit public structured results only; no adapter is allowed to turn a blocked/unavailable response into guessed data.

The worker does not place source-of-truth or publication decisions in AI/provider adapters. Every AI fact is validated and linked to an allowed document block; deterministic facts are created before optional AI processing.

## Verified implementation addendum — TASK-CRAWL-003 (2026-08-08)

Relevant source-discovery boundaries are:

- `modules/sources/official_discovery.py`: robots-aware bounded website discovery, HTML link extraction, sitemap location parsing, canonicalization, and discovery budgets;
- `modules/sources/ranking.py`: multilingual page-group classification and deterministic URL relevance scores;
- `modules/sources/query_builder.py`: provider-neutral deterministic query templates;
- `integrations/fetch/website_discovery.py`: direct HTTP adapter with SSRF-safe redirect validation and response limits;
- `db/models/search.py` and migration `20260808_0019_search_discovery_metadata.py`: durable query/result metadata.

These components return discovery metadata only. They do not publish facts, treat snippets as evidence, bypass robots/access controls, or import Gemini.

## Verified implementation addendum — TASK-CRAWL-004 (2026-08-09)

The crawl/parser ownership is:

- `modules/sources/fetcher.py`: `WebFetcher`, per-domain limiter, bounded retry/redirect/MIME/size policy, immutable snapshot persistence, and `CrawlCoordinator`;
- `modules/sources/coordinator.py`: public coordinator import boundary;
- `modules/sources/validator.py`: HTTP(S), DNS/IP, reserved-network, credential, and redirect safety validation;
- `modules/sources/parser.py`: deterministic HTML, structured JSON, and bounded page-aware PDF parsing;
- `modules/sources/browser_adapter.py`: Playwright fallback with initial, subresource, final-URL, and response-size safety checks;
- `modules/facts/deterministic.py`: direct structured/labelled fact extraction and evidence linking;
- `db/models/source.py` and migration `20260809_0020_crawl_parse_metadata.py`: parser, language, evidence-location, fetch-policy, and retry audit metadata.

The source body remains untrusted data. No parser executes scripts, no browser fallback bypasses access controls, and no deterministic regex infers broad semantic fields.
