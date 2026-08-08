# System Architecture

Status: planned reference architecture. Source code becomes runtime truth after implementation; this document must be updated in the same change when architecture changes.

## 1. Architecture summary

The baseline is a modular monolith with separate API and background-worker processes sharing one domain model and one PostgreSQL database.

```text
Researcher / Reviewer / Officer Browser
                  |
                HTTPS
                  |
          Next.js Web Application
                  |
          REST /api/v1 + SSE events
                  |
             FastAPI API
       +----------+-----------+
       |          |           |
 PostgreSQL   Object Store   Auth Provider
       |
 Durable research jobs and state
       |
 Python Research Worker
       +-------------------------------+
       |              |                |
 Search Provider   Fetch/Parser     Gemini Provider
       |              |                |
 Public Web      HTML/PDF/JSON-LD  Extraction/Translation
```

The API handles interactive requests and durable state transitions. The worker performs slow or externally dependent research tasks. PostgreSQL is the authoritative workflow and profile store. Object storage holds large immutable source snapshots, extracted text, and generated exports.

## 2. Architectural goals

- Keep the first system understandable and deployable by a small team.
- Isolate web retrieval and AI provider failures from interactive API availability.
- Preserve source, evidence, and publication history even when jobs fail.
- Make every provider replaceable through an internal interface.
- Avoid Redis, microservices, and event-bus complexity until measured need exists.
- Support local deterministic development without real provider credentials.
- Make production deployment natural on Google Cloud for the competition context.

## 3. Runtime boundaries

| Process or service | Planned technology | Responsibility |
| --- | --- | --- |
| `web` | Next.js, React, TypeScript | UI routing, server-state queries, review interface, profile rendering, exports download |
| `api` | FastAPI, Pydantic, SQLAlchemy | HTTP/SSE contracts, authentication, authorization, command validation, transactions, query APIs |
| `worker` | Python process using shared backend modules | Research orchestration, source discovery, fetching, parsing, AI extraction, verification, export rendering |
| `postgres` | PostgreSQL 16 | Workspaces, companies, jobs, sources, facts, conflicts, profiles, reviews, audit, idempotency |
| `object storage` | Local adapter in development; GCS-compatible in production | Source bodies, PDFs, parsed text, screenshots when allowed, generated exports |
| `auth provider` | Firebase Authentication or Google Identity Platform adapter | User identity; backend remains authorization authority |
| `Gemini provider` | Server-side Gemini API adapter | Structured extraction, classification, translation, comparison, summary generation |
| `search provider` | Google Search grounding or approved search API adapter | Discovery of public source candidates |
| `browser renderer` | Playwright fallback | Render public JavaScript pages when allowed and necessary |

## 4. Deployment topology

### 4.1 Local development

```text
Docker Compose
  web:3000
  api:8000
  worker
  postgres:5432
  minio or local-volume storage
```

Real external providers are optional. Mock auth, mock search, fixture fetch, mock AI, and local storage must support complete automated tests.

### 4.2 Production reference

```text
Cloud Load Balancer / managed HTTPS
        |
Cloud Run Web + API
        |
Cloud SQL PostgreSQL
        |
Cloud Tasks -> Cloud Run Worker
        |
GCS + Gemini API + approved search/fetch providers
```

PostgreSQL remains the source of job truth even when Cloud Tasks performs delivery. Task retries must be mapped to idempotent job-step execution.

## 5. Backend module architecture

The backend package is divided by domain, not by transport alone.

| Module | Responsibility |
| --- | --- |
| `auth` | Identity token verification, current actor, session/capability resolution |
| `workspaces` | Workspace membership, roles, policy scope |
| `companies` | Canonical entity, aliases, identifiers, relationships, merge/split |
| `research` | Research jobs, steps, progress, retry, cancel, orchestration |
| `discovery` | Queries, search results, source candidate ranking |
| `sources` | Source metadata, snapshots, fetch attempts, parsers, domain policy |
| `documents` | HTML/PDF parsing, text blocks, language detection, page references |
| `ai` | Provider interface, prompts, schemas, usage, injection defenses |
| `facts` | Candidate normalization, evidence mapping, confidence, freshness |
| `conflicts` | Conflict grouping, materiality, resolution |
| `profiles` | Draft assembly, publication, versioning, summaries, meeting brief |
| `reviews` | Review task assignment, decisions, optimistic locking |
| `search` | Company library indexing and filters |
| `exports` | PDF/JSON generation and download metadata |
| `policies` | Authority tiers, blocked domains, freshness, mandatory review |
| `audit` | Immutable sensitive-action trail |
| `operations` | Health, readiness, metrics, job operations, usage summaries |

## 6. Dependency direction

```text
HTTP routes / worker commands
        |
Application services
        |
Domain policies and state transitions
        |
Repository interfaces + provider interfaces
        |
SQLAlchemy repositories / HTTP providers / object storage adapters
```

Rules:

- Routes translate transport only.
- Application services own use-case orchestration and transactions.
- Domain policies are deterministic and provider-independent.
- Repositories own persistence details but do not authorize actors by themselves.
- Provider adapters cannot publish facts or profiles directly.
- UI components cannot own source ranking, confidence, or publication policy.

## 7. Frontend architecture

Planned route domains:

```text
/login
/companies
/companies/new
/companies/:companyId
/companies/:companyId/research
/companies/:companyId/sources
/companies/:companyId/facts
/companies/:companyId/conflicts
/companies/:companyId/reviews
/companies/:companyId/profiles
/companies/:companyId/profiles/:versionId
/reviews
/operations/jobs
/admin/members
/admin/policies
/admin/providers
/audit
```

Frontend responsibilities:

- route-level orchestration;
- capability-aware navigation;
- TanStack Query server-state cache;
- form state and safe draft recovery;
- localized display copy;
- accessible evidence and conflict views;
- SSE subscription for progress with polling fallback.

The browser is never authoritative for workspace, role, source authority, confidence, evidence acceptance, profile publication, or provider state.

## 8. Data ownership

- PostgreSQL owns canonical structured state and all workflow transitions.
- Object storage owns large immutable artifacts referenced by PostgreSQL metadata.
- Auth provider owns identity authentication; application database owns roles and workspace authorization.
- External websites own their public content. The system stores snapshots according to policy and retention.
- AI provider owns model execution only; model output is stored as a versioned run artifact and must pass local validation.
- The browser owns temporary UI drafts only.

## 9. Research orchestration

### 9.1 Job graph

A full research job normally contains:

1. validate request and lock company scope;
2. resolve company identity;
3. generate discovery queries;
4. search and rank source candidates;
5. apply domain and policy rules;
6. fetch selected sources;
7. parse and segment documents;
8. extract candidate facts;
9. normalize and link evidence;
10. calculate confidence and detect conflicts;
11. create review tasks;
12. assemble draft profile;
13. finalize job result.

A failed non-critical step may produce `partial_success`. Identity failure, workspace loss, or integrity failure stops dependent steps.

### 9.2 Job claiming

Local worker baseline:

- due jobs are claimed with `FOR UPDATE SKIP LOCKED`;
- each step has an idempotency key;
- claim leases have expiration;
- stale running steps can be reclaimed safely;
- attempt counts and next retry time are durable;
- one active job per `(workspace, company, scope)` is enforced where required.

Production Cloud Tasks dispatch invokes the same idempotent step service. The task is a delivery mechanism, not the source of truth.

## 10. Source discovery architecture

`SearchProvider` returns result metadata only. The application then:

- normalizes URL and domain;
- checks block/allow policy;
- estimates source type and authority;
- checks entity match;
- deduplicates canonical URLs and content;
- selects candidates according to budget;
- records discarded results and reasons.

Search snippets are discovery artifacts. They are not accepted evidence when the destination is available.

## 11. Fetch and parser architecture

### 11.1 Fetch adapters

```text
FetchCoordinator
  |-- HttpFetcher
  |-- UrlContextFetcher, when approved
  |-- BrowserFetcher, allowed fallback only
  \-- FixtureFetcher, test only
```

### 11.2 Required protections

- DNS and IP validation before every redirect.
- Block localhost, private, link-local, metadata, and reserved network ranges.
- Response size and decompression limits.
- MIME sniffing and extension mismatch detection.
- Timeout, redirect, and retry limits.
- User-agent and contact policy.
- Per-domain rate limiting.
- No authentication or CAPTCHA circumvention.

### 11.3 Parser output

Parsers produce normalized document blocks:

```text
Document
  metadata
  language
  title
  published/modified date if available
  blocks[]
    block_id
    type
    text
    page/section/css/xpath reference
    char offsets
    hash
```

Evidence references stable block IDs and offsets, not only a copied sentence.

## 12. AI architecture

### 12.1 Provider interface

The application defines operations such as:

- `extract_company_facts`;
- `classify_source`;
- `translate_evidence`;
- `compare_candidates`;
- `generate_grounded_summary`.

Each operation has:

- versioned input schema;
- versioned output schema;
- prompt template version;
- budget and timeout;
- mock implementation;
- validation and fallback behavior.

### 12.2 Grounding controls

The system sends only the selected document blocks needed for the operation. The system prompt instructs the model to treat source instructions as data. Output facts must reference supplied block IDs. Unknown values are valid output.

### 12.3 Structured output validation

Model output is rejected when:

- JSON/schema validation fails;
- evidence block does not exist;
- evidence does not contain or support the claimed value;
- company entity mismatch is detected;
- field type or unit is invalid;
- output exceeds configured budget or cardinality;
- model attempts to return executable tool instructions as facts.

## 13. Confidence architecture

The default candidate score is explainable and field-specific:

```text
confidence =
  authority_weight
  * entity_match_weight
  * evidence_quality_weight
  * recency_weight
  * extraction_reliability_weight
  * agreement_adjustment
```

The persisted explanation includes each component. Exact weights belong to versioned policy configuration. A reviewer may override the selected candidate but cannot rewrite the historical score silently.

Confidence thresholds do not automatically publish high-impact fields.

## 14. Profile architecture

A draft profile references selected fact candidates. Publication creates:

- immutable profile version;
- immutable field values and evidence links;
- generated summary based only on those values;
- source appendix;
- publication actor and timestamp;
- schema and policy versions.

A refresh never edits a published version. It produces new candidates and a new draft.

## 15. Authorization architecture

- Identity provider token is verified at the API edge.
- Active user and workspace membership are reloaded or safely cached with revocation rules.
- Controllers pass an actor context to services.
- Services enforce capability and workspace ownership.
- Repositories receive workspace scope explicitly in every workspace-owned query.
- Object keys include opaque IDs, not guessable tenant paths alone.
- Export download uses authorization checks or short-lived signed URLs.

## 16. Security boundaries

- All provider credentials are backend-only secrets.
- Retrieved content is untrusted.
- AI output is untrusted until validated.
- Uploaded or downloaded documents are untrusted until checked.
- Source URLs are untrusted SSRF inputs.
- Markdown/HTML rendered in UI is sanitized.
- Audit logs avoid full source bodies, secrets, and unnecessary personal information.
- Production object storage is private by default.

## 17. Observability architecture

Every API request and worker step carries:

- request or correlation ID;
- workspace ID;
- company ID when applicable;
- research job and step ID;
- provider operation ID;
- safe outcome code;
- latency and retry count.

Metrics include:

- API latency and errors;
- active and queued jobs;
- step duration and failure by type;
- source fetch result and bytes;
- parser result;
- AI calls, tokens, estimated cost, latency, validation rejection;
- fact conflict rate;
- review backlog age;
- publication count and age;
- object storage and database health.

## 18. Failure behavior

| Failure | Required behavior |
| --- | --- |
| Search provider unavailable | Mark discovery step retryable; preserve existing sources |
| One source fetch fails | Continue other sources; record partial result |
| PDF unsupported | Mark source parse failure; keep source metadata |
| AI timeout | Retry within budget or leave candidates incomplete |
| Invalid AI output | Record validation failure; never create accepted fact |
| Worker crash | Lease expires and step can be reclaimed |
| Duplicate task delivery | Idempotency returns prior result |
| Database unavailable | API readiness fails; worker stops claiming new work |
| Object storage unavailable | Do not mark snapshot complete; retry safely |
| Reviewer conflict | Use optimistic version check and return `409` |
| Publication failure | Transaction rolls back; previous version remains active |

## 19. Scalability boundaries

The baseline is suitable for a small-to-medium internal workload. Before larger scale:

- measure job queue depth and worker utilization;
- separate heavy PDF/browser workloads if necessary;
- add managed task delivery and autoscaling;
- add database read optimization and partitioning based on evidence;
- introduce search infrastructure only when PostgreSQL search is insufficient;
- add provider-specific concurrency and quota coordination;
- consider Redis only for a measured cache or queue requirement, not by default.

## 20. Architecture synchronization checklist

- [ ] Runtime diagram matches deployed components.
- [ ] Module list matches source directories and ownership.
- [ ] Provider interfaces match implemented adapters.
- [ ] Job state and claim strategy match actual worker code.
- [ ] Authentication and authorization boundaries match middleware and services.
- [ ] Storage ownership matches database and object keys.
- [ ] Failure behavior is covered by tests or documented operational checks.
- [ ] New external dependencies are recorded with secrets, cost, privacy, and fallback behavior.
- [ ] Any departure from this architecture has an ADR in `09_DECISIONS_AND_RISKS.md`.

## Verified implementation addendum — TASK-CRAWL-001 (2026-08-08)

The worker implementation currently uses the following durable step sequence:

```text
entity_resolution
→ source_discovery
→ source_selection
→ source_fetch
→ document_parse
→ deterministic_extraction
→ ai_extraction (optional)
→ fact_processing
→ finalize
```

`ResearchPipelineExecutor` owns orchestration while `WebFetcher`, document parsers, deterministic fact extraction, AI validation, conflict detection, and review-task services retain their provider/domain boundaries. Each completed worker step is committed before the dispatcher creates the next step. Optional AI failures become warnings in the durable payload; acquisition artifacts are not rolled back.

## Verified implementation addendum — TASK-CRAWL-002 (2026-08-08)

Source discovery responsibilities are now split from pipeline orchestration:

```text
ResearchPipelineExecutor
  -> SourceDiscoveryService
       -> SearchProvider metadata
       -> CountrySourceRegistry / TrustedSourceProvider adapters
       -> scope links (official, manual, sitemap, internal)
       -> tenant-scoped Source history
       -> deterministic canonicalization and selection
```

`modules/sources/discovery.py` contains provider-neutral contracts and policy orchestration. `modules/sources/trusted_sources.py` contains country configuration and the default no-fabrication adapter. The core service does not import AI or call websites directly. A production adapter must prefer public structured/API access, enforce robots/terms/access controls, and return a typed outcome before any permitted fetch adapter is used. `Source.authority_for_field()` is the boundary used by deterministic and AI fact confidence calculations; no single domain score is treated as authoritative for every field.
