# Development and Testing

Status: planned development and verification baseline.

## 1. Prerequisites

Target baseline:

- Python 3.12;
- `uv` for Python dependency and environment management;
- Node.js 20 or later LTS selected by repository toolchain;
- `pnpm` for frontend workspace;
- PostgreSQL 16;
- Docker Desktop or Docker Engine with Compose;
- Playwright browser dependencies for dynamic-page and E2E tests;
- optional Google Cloud CLI for staging operations.

Exact versions belong in `.python-version`, `.nvmrc`, lockfiles, and CI images.

## 2. Initial setup

Expected after repository foundation:

```bash
cp .env.example .env
uv sync
pnpm install
make db-up
make db-migrate
make dev
```

The project must provide one documented command for the normal local stack. Foundation tasks may use Docker Compose:

```bash
docker compose up --build
```

## 3. Environment configuration

Categories:

### Application

- environment name;
- public web origin;
- API origin;
- supported/default locale;
- log level;
- request and correlation settings.

### Database

- database URL;
- pool sizes and timeouts;
- migration role or separate migration URL.

### Authentication

- auth mode (`mock`, `firebase`, or approved adapter);
- project/audience identifiers;
- cookie/session secrets where applicable.

### AI and search

- Gemini API key or workload identity configuration;
- model identifiers by operation;
- search provider configuration;
- per-job/token/cost limits;
- provider timeout and retry limits.

### Fetch and browser

- user agent and contact URL;
- request timeout;
- response size limits;
- per-domain concurrency;
- browser fallback enabled flag;
- allowed protocols and network-block policy.

### Storage

- local storage root in development;
- bucket/project identifiers in cloud;
- signed URL expiry;
- malware-scanner mode.

### Worker

- worker ID;
- polling interval for local mode;
- claim lease duration;
- batch size;
- task dispatch mode;
- retry backoff.

Never put server secrets in `NEXT_PUBLIC_*` variables.

## 4. Local provider modes

A complete local run must work without external credentials:

```dotenv
AUTH_MODE=mock
SEARCH_PROVIDER=fixture
AI_PROVIDER=mock
FETCH_PROVIDER=fixture_or_http
OBJECT_STORAGE_PROVIDER=local
TASK_DISPATCHER=postgres
MALWARE_SCANNER=mock
```

Mocks must preserve production contracts and state transitions. They must not bypass application validation.

## 5. Expected commands

Repository foundation should expose stable root commands such as:

```bash
make dev
make stop
make clean
make format
make lint
make typecheck
make test
make test-unit
make test-integration
make test-e2e
make test-security
make test-contract
make test-docs
make build
make db-migrate
make db-status
make db-fixtures
make openapi
```

Underlying tool commands may change; root developer commands should remain stable or be updated across docs and CI together.

## 6. Database development

- Use isolated local database and test database.
- Never run destructive reset against staging or production.
- Fixtures are explicit, deterministic, and idempotent where practical.
- Tests create their own workspace/company IDs and clean up through transaction rollback or isolated schema.
- Migration tests cover clean install and upgrade from prior release.

Expected flow:

```bash
make db-status
make db-migrate
make db-fixtures
```

## 7. Fixture catalog

Required deterministic source fixtures:

1. simple official HTML website;
2. website with JSON-LD organization metadata;
3. dynamic JavaScript-rendered page;
4. multi-page official website;
5. public PDF annual report with page evidence;
6. Vietnamese source;
7. English source;
8. another-language source requiring translation;
9. two companies with identical or similar names;
10. parent/subsidiary relationship;
11. conflicting incorporation dates;
12. conflicting employee ranges;
13. stale news article;
14. mirrored duplicate content;
15. blocked domain;
16. robots-disallowed fixture;
17. redirect to private IP for SSRF test;
18. oversized document;
19. malformed PDF;
20. prompt-injection text inside source content;
21. unsupported fact returned by mock AI;
22. provider timeout and rate-limit responses.

Automated tests must not rely on live Google, LinkedIn, company websites, or registries.

## 8. Test layers

| Layer | Tool | Focus |
| --- | --- | --- |
| Pure unit | Pytest / Vitest | normalization, confidence, state transitions, field schemas, UI helpers |
| Repository integration | Pytest + PostgreSQL | constraints, workspace scope, indexes, mappings, transactions |
| Service integration | Pytest | authorization, idempotency, publication, merge, conflict, job orchestration |
| API route | FastAPI TestClient/httpx | middleware, validation, status, envelopes, SSE behavior |
| Provider contract | Pytest | mock/production adapter contract parity and typed errors |
| Component | Testing Library | review controls, evidence display, status states |
| Browser E2E | Playwright | create company through publication/export on desktop/mobile |
| Security | Dedicated tests/scanners | SSRF, auth scope, injection, file limits, secrets |
| Load | k6/Locust or approved tool | job creation, company search, publication locks, worker throughput |
| Documentation/contract | scripts + CI | OpenAPI, requirements/status, links, Roadmap and docs drift |

## 9. Critical unit tests

- company name/domain normalization;
- country and identifier normalization;
- duplicate scoring does not auto-merge weak matches;
- field value validators and serializers;
- confidence component calculation;
- confidence explanation stability;
- recency/freshness calculation;
- source authority by field type;
- material conflict comparison;
- inferred/estimated labels preserved;
- profile summary refuses unsupported fields;
- state machines reject invalid transitions;
- prompt-injection content is treated as data;
- deterministic mock AI schema parity.

## 10. Critical database and service tests

- cross-workspace access denied for every resource type;
- concurrent company creation with same strong identifier;
- one active protected research job per scope;
- worker claim uses skip-locked semantics without duplicate execution;
- stale lease recovery;
- idempotent step retry;
- snapshot immutability;
- candidate plus evidence transaction rollback;
- conflict resolution optimistic lock;
- one current published version under concurrent publication;
- published version immutability;
- company merge lock ordering and history preservation;
- export idempotency;
- audit event written with sensitive metadata minimized.

## 11. Critical fetch security tests

- reject `file:`, `ftp:`, and unsupported schemes;
- reject localhost and loopback;
- reject private, link-local, multicast, and metadata-service IPs;
- revalidate every redirect destination;
- protect against DNS rebinding according to chosen implementation;
- enforce response and decompression size limits;
- enforce timeout and redirect count;
- reject MIME mismatch and unsupported content;
- respect blocked-domain and robots policy;
- never send provider credentials to fetched domains;
- browser fallback does not weaken network policy;
- sanitize retrieval errors.

## 12. AI safety and quality tests

- malformed JSON output rejected;
- unknown evidence block rejected;
- claim not supported by excerpt rejected;
- wrong company evidence rejected;
- unknown output accepted as valid absence;
- direct, inferred, and estimated outputs remain distinct;
- prompt injection in content does not alter output schema or policy;
- model output cannot invoke arbitrary tools;
- cost budget stops additional calls;
- timeout and retry behavior is bounded;
- mock and real adapter return the same application-level schema;
- grounded summary only uses accepted profile fields.

## 13. Frontend tests

Pages/components must test:

- loading;
- empty;
- error and retry;
- authorization failure;
- ambiguous identity;
- partial research success;
- job progress reconnect;
- conflict comparison;
- original plus translated evidence;
- mandatory review reason;
- optimistic lock conflict;
- stale field warning;
- publication blocked reasons;
- version diff;
- export pending/success/failure;
- mobile and desktop navigation;
- keyboard and screen-reader semantics.

## 14. End-to-end scenarios

### E2E-001: Trusted first profile

1. Sign in as researcher.
2. Create company with name/domain/country.
3. Start fixture research.
4. Observe durable job steps.
5. Open source and evidence.
6. Sign in or switch as reviewer.
7. Accept required facts.
8. Publish profile.
9. Verify source links and version history.
10. Export PDF/JSON.

### E2E-002: Ambiguous company

- duplicate suggestions appear;
- dependent facts do not merge before identity review;
- reviewer selects correct entity;
- job resumes.

### E2E-003: Conflict

- two credible dates create open conflict;
- reviewer sees both source snapshots;
- reason required;
- selected outcome appears in published version;
- rejected candidate remains in history.

### E2E-004: Provider failure

- one fetch and AI operation fail;
- job becomes partial success or retryable;
- current published profile remains unchanged;
- retry does not duplicate snapshots/candidates.

### E2E-005: Workspace isolation

- user in workspace A cannot infer or access company, job, source, evidence, profile, or export in workspace B.

## 15. Performance tests

Before production, define SLOs and test:

- company library search with representative data volume;
- current profile read with evidence summaries;
- 100+ concurrent job submissions with idempotency;
- worker claim and processing throughput;
- publication contention;
- source body storage and parser memory limits;
- SSE connection count and polling fallback;
- export generation concurrency.

Optimize only from measured bottlenecks.

## 16. Static and supply-chain checks

- Python lint and format;
- Python type checking;
- TypeScript lint and type check;
- dependency vulnerability audit;
- secret scanning;
- container/image scanning before production;
- license policy check for new dependencies;
- generated OpenAPI client drift;
- dead links and markdown checks;
- migration consistency.

## 17. Documentation drift tests

The repository should implement a script that checks at minimum:

- all canonical files exist;
- requirement IDs are unique;
- Roadmap task IDs are unique;
- status values are allowed;
- API endpoints in docs have valid path format;
- docs links resolve;
- AGENT references existing paths;
- Roadmap active-mode marker matches AGENT mandatory read rule;
- completed roadmap tasks contain evidence/verification notes;
- known defects have owner/status/reference;
- last-verified metadata is not falsely updated by a script without repository verification.

Automation assists but does not replace human/code verification.

## 18. Manual acceptance

Manual checks are required for:

- real Gemini behavior and cost;
- real Google/search provider result quality;
- public website compliance behavior;
- PDF evidence page display;
- multilingual evidence readability;
- reviewer usability;
- exported PDF layout;
- production auth and signed downloads;
- staging backup/restore.

Record exact environment, date, actor, and evidence for manual gates.

## 19. Common failure guidance

### API not ready

Check database migration status, connection, auth configuration, and `/ready` dependency details.

### Worker not progressing

Check due step query, claim lease, dispatcher, worker identity, database locks, and provider configuration. Do not manually mark steps succeeded.

### Duplicate artifacts

Inspect idempotency key, request hash, snapshot content hash, and step output hash before deleting data.

### AI returns plausible but unsupported values

Treat as validation failure, preserve safe run metadata, improve prompt/schema/validator, and add regression fixture. Do not accept because it appears reasonable.

### Browser fetch works but HTTP fetch fails

Confirm policy allows browser mode. Do not disable SSRF or access controls to make the test pass.

## 20. Definition of done

A task is complete only when:

- implementation matches requirement and domain rules;
- authorization and workspace scope are tested;
- relevant unit/integration/E2E tests pass;
- loading/error/empty/responsive UI states are handled;
- migrations and rollback/forward behavior are documented;
- logs and metrics are safe;
- API/OpenAPI/client are synchronized;
- canonical docs are updated;
- Roadmap status and defect ledger are updated;
- all attempted validation commands and outcomes are recorded;
- unrelated user work remains untouched.

## 21. Development and testing synchronization checklist

- [ ] Commands match actual scripts and package managers.
- [ ] Environment examples match typed settings.
- [ ] Fixtures cover every new provider/parser/field behavior.
- [ ] Critical regressions have automated tests.
- [ ] Manual-only checks are explicitly identified.
- [ ] CI runs the documented mandatory gates.
- [ ] Definition of done matches `AGENT.md`.
- [ ] Failed or skipped checks are recorded in Roadmap notes.
